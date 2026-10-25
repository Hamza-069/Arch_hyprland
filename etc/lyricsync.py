#!/usr/bin/env python3
"""lyricsync — CLI lyrics synchronization tool.

Fetches synchronized lyrics from LRCLIB and LRCMux (lrcmux.dev),
transliterates Gurmukhi/Devanagari to casual Latin, and displays
them in sync with the currently playing song.
"""

from __future__ import annotations

import argparse
import bisect
import collections
import curses
import difflib
import json
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence

# ──────────────────────────── data types ─────────────────────────────

@dataclass
class LyricLine:
    time_ms: int
    text: str

@dataclass
class SyncedLyrics:
    title: str
    artist: str
    album: str
    source: str
    lines: list[LyricLine] = field(default_factory=list)
    synced: bool = True

    @property
    def last_line_ms(self) -> int:
        # Timestamp of the last lyric line, NOT the track length.
        return self.lines[-1].time_ms if self.lines else 0

@dataclass
class PlaybackInfo:
    title: str = ""
    artist: str = ""
    album: str = ""
    duration_ms: int = 0
    position_ms: int = 0
    playing: bool = False
    player: str = ""

# ──────────────────────────── LRC parser ─────────────────────────────

_LRC_META_RE = re.compile(r"\[(\w+):(.*)\]")
_LRC_TIME_RE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
# mpc status prints elapsed/total on the second line as m:ss or h:mm:ss
# (e.g. "[playing] #3/12   1:23/3:45 (37%)"). Resolution is whole seconds.
_MPC_TIME_RE = re.compile(
    r"(\d+):(\d\d)(?::(\d\d))?/(\d+):(\d\d)(?::(\d\d))?"
)

def parse_lrc(raw: str) -> SyncedLyrics:
    """Parse LRC format into SyncedLyrics."""
    title = artist = album = ""
    lines: list[LyricLine] = []
    for raw_line in raw.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        meta = _LRC_META_RE.match(raw_line)
        if meta:
            key = meta.group(1).lower()
            if key in ("ti", "ar", "al"):
                val = meta.group(2).strip()
                if key == "ti":
                    title = val
                elif key == "ar":
                    artist = val
                elif key == "al":
                    album = val
                continue
        times = _LRC_TIME_RE.findall(raw_line)
        if not times:
            continue
        text = _LRC_TIME_RE.sub("", raw_line).strip()
        for mm, ss_part in times:
            ss = float(ss_part)
            ms = int(float(mm) * 60000 + ss * 1000)
            lines.append(LyricLine(time_ms=ms, text=text))
    lines.sort(key=lambda l: l.time_ms)
    return SyncedLyrics(title=title, artist=artist, album=album,
                        source="lrc", lines=lines, synced=bool(lines))


def parse_plain_lyrics(text: str, title: str = "", artist: str = "",
                       album: str = "", source: str = "") -> SyncedLyrics:
    """Wrap unsynced plain text into a SyncedLyrics with synced=False."""
    lines = [LyricLine(time_ms=0, text=l.strip())
             for l in text.splitlines() if l.strip()]
    return SyncedLyrics(title=title, artist=artist, album=album,
                        source=source, lines=lines, synced=False)


# ──────────────────────────── transliteration ────────────────────────
# Table-driven Indic → casual Latin. Each script occupies a 128-codepoint
# block, so classification is an array index (ord(ch) - base) rather than
# a chain of dict lookups. Schwa (inherent "a") is dropped at word end
# and before a later syllable that already has an explicit matra.

_OTHER, _CONS, _VOWEL, _MATRA, _NASAL, _SIGN, _HALANT, _ADDAK, _NUKTA = range(9)
_SCRIPT_SIZE = 128
_WORD_BREAK = frozenset(" \t\n\r.,!?;:'\"-—–…()[]{}।॥?/\\~`")
_FORMAT_CHARS = frozenset("\u200c\u200d")  # ZWNJ, ZWJ


@dataclass
class _Script:
    base: int
    lo: str
    hi: str
    kinds: list[int]
    vals: list[str]
    nukta_vals: list[str]
    yu_vowel: str
    labials: str
    gy: bool  # Devanagari ज्ञ → gy


def _key_index(base: int, ch: str) -> int:
    """Validate a single-code-point key inside the script block and return
    its array index. Raises ValueError for multi-code-point or out-of-block
    keys."""
    if len(ch) != 1:
        raise ValueError(f"key must be a single code point, got {ch!r}")
    idx = ord(ch) - base
    if not 0 <= idx < _SCRIPT_SIZE:
        raise ValueError(
            f"key {ch!r} (U+{ord(ch):04X}) is outside the "
            f"script block U+{base:04X}-U+{base + _SCRIPT_SIZE - 1:04X}")
    return idx


def _put(kinds: list[int], vals: list[str], base: int,
         ch: str, kind: int, val: str) -> None:
    idx = _key_index(base, ch)
    kinds[idx] = kind
    vals[idx] = val


def _make_script(
    base: int,
    consonants: dict[str, str],
    vowels: dict[str, str],
    matras: dict[str, str],
    nasals: dict[str, str],
    signs: dict[str, str],
    halant: str,
    nukta: str,
    addak: str = "",
    nukta_forms: dict[str, str] | None = None,
    yu_vowel: str = "",
    labials: str = "",
    gy: bool = False,
) -> _Script:
    kinds = [_OTHER] * _SCRIPT_SIZE
    vals = [""] * _SCRIPT_SIZE
    nukta_vals = [""] * _SCRIPT_SIZE
    for ch, val in consonants.items():
        _put(kinds, vals, base, ch, _CONS, val)
    for ch, val in vowels.items():
        _put(kinds, vals, base, ch, _VOWEL, val)
    for ch, val in matras.items():
        _put(kinds, vals, base, ch, _MATRA, val)
    for ch, val in nasals.items():
        _put(kinds, vals, base, ch, _NASAL, val)
    for ch, val in signs.items():
        _put(kinds, vals, base, ch, _SIGN, val)
    _put(kinds, vals, base, halant, _HALANT, "")
    if nukta:
        _put(kinds, vals, base, nukta, _NUKTA, "")
    if addak:
        _put(kinds, vals, base, addak, _ADDAK, "")
    if nukta_forms:
        for ch, val in nukta_forms.items():
            idx = _key_index(base, ch)
            nukta_vals[idx] = val
    return _Script(
        base=base, lo=chr(base), hi=chr(base + _SCRIPT_SIZE - 1),
        kinds=kinds, vals=vals, nukta_vals=nukta_vals,
        yu_vowel=yu_vowel, labials=labials, gy=gy,
    )


def _cons_has_matra(text: str, pos: int, n: int,
                    base: int, kinds: list[int]) -> bool:
    """True if the consonant at pos is followed by a matra (after nukta)."""
    pos += 1
    if pos >= n:
        return False
    idx = ord(text[pos]) - base
    if not (0 <= idx < _SCRIPT_SIZE):
        return False
    k = kinds[idx]
    if k == _NUKTA:
        pos += 1
        if pos >= n:
            return False
        idx = ord(text[pos]) - base
        if not (0 <= idx < _SCRIPT_SIZE):
            return False
        k = kinds[idx]
    return k == _MATRA


def _final_aa(text: str, pos: int, n: int) -> bool:
    """True if the aa matra at pos is word-final."""
    j = pos + 1
    while j < n and text[j] in _FORMAT_CHARS:
        j += 1
    return j >= n or text[j] in _WORD_BREAK or text[j].isspace()


def _geminate(val: str) -> str:
    if len(val) == 1:
        return val + val
    return val[0] + val  # kh → kkh, sh → ssh


def transliterate_indic(text: str, script: _Script) -> str:
    lo, hi = script.lo, script.hi
    n = len(text)
    # Fast reject: no characters in this script.
    i = 0
    while i < n and not (lo <= text[i] <= hi):
        i += 1
    if i >= n:
        return text
    # Run the main loop from index 0 so leading non-script characters,
    # format chars (ZWJ/ZWNJ) and dandas are handled by the main loop
    # rather than copied raw.
    i = 0

    kinds = script.kinds
    vals = script.vals
    nukta_vals = script.nukta_vals
    base = script.base
    yu_vowel = script.yu_vowel
    labials = script.labials
    gy = script.gy
    out: list[str] = []
    seen_vowel = False

    while i < n:
        ch = text[i]
        idx = ord(ch) - base
        if idx < 0 or idx >= _SCRIPT_SIZE:
            if ch in _FORMAT_CHARS:
                i += 1
                continue
            if ch in ("।", "॥"):
                # Danda / double-danda: word break, dropped in both scripts.
                seen_vowel = False
                i += 1
                continue
            if ch in _WORD_BREAK or ch.isspace():
                seen_vowel = False
            out.append(ch)
            i += 1
            continue

        kind = kinds[idx]
        val = vals[idx]
        geminate = False

        if kind == _ADDAK:
            i += 1
            if i >= n:
                continue
            ch = text[i]
            idx = ord(ch) - base
            if not (0 <= idx < _SCRIPT_SIZE) or kinds[idx] != _CONS:
                continue
            kind = _CONS
            val = vals[idx]
            geminate = True

        if kind == _CONS:
            # ज्ञ (j + virama + nya) → gy
            if gy and ch == "ज" and i + 2 < n and text[i + 1] == "्" \
                    and text[i + 2] == "ञ":
                val = "gy"
                i += 3
            else:
                i += 1
                if i < n:
                    nidx = ord(text[i]) - base
                    if 0 <= nidx < _SCRIPT_SIZE and kinds[nidx] == _NUKTA:
                        alt = nukta_vals[idx]
                        if alt:
                            val = alt
                        i += 1
            if geminate:
                val = _geminate(val)

            nxt_kind = _OTHER
            if i < n:
                nidx = ord(text[i]) - base
                if 0 <= nidx < _SCRIPT_SIZE:
                    nxt_kind = kinds[nidx]

            if nxt_kind == _HALANT:
                out.append(val)
                continue
            if nxt_kind == _MATRA:
                out.append(val)
                mval = vals[ord(text[i]) - base]
                if mval == "i" and yu_vowel and i + 1 < n \
                        and text[i + 1] == yu_vowel:
                    out.append("yu")
                    i += 2
                else:
                    # Word-final explicit aa shortens to "a" (का → ka);
                    # medial aa stays long (किताब → kitaab, हाँ → haan).
                    if mval == "aa" and _final_aa(text, i, n):
                        out.append("a")
                    else:
                        out.append(mval)
                    i += 1
                seen_vowel = True
                continue

            add_a = False
            if i >= n:
                add_a = not seen_vowel
            else:
                nxt = text[i]
                nidx = ord(nxt) - base
                if nidx < 0 or nidx >= _SCRIPT_SIZE:
                    # Mixed romanization (ਫ਼iran): Latin already supplies the vowel.
                    if nxt.isalpha() or nxt.isdigit():
                        add_a = False
                    else:
                        add_a = not seen_vowel
                elif nxt_kind == _NASAL or nxt_kind == _ADDAK:
                    add_a = True
                elif nxt_kind == _CONS:
                    add_a = (not seen_vowel) or (
                        not _cons_has_matra(text, i, n, base, kinds))
                elif nxt_kind in (_MATRA, _HALANT, _VOWEL):
                    add_a = False
                else:
                    add_a = not seen_vowel
            out.append(val)
            if add_a:
                out.append("a")
                seen_vowel = True
            continue

        if kind == _VOWEL:
            out.append(val)
            seen_vowel = True
            i += 1
            continue

        if kind == _MATRA:
            if val == "i" and yu_vowel and i + 1 < n \
                    and text[i + 1] == yu_vowel:
                out.append("yu")
                i += 2
            else:
                if val == "aa" and _final_aa(text, i, n):
                    out.append("a")
                else:
                    out.append(val)
                i += 1
            seen_vowel = True
            continue

        if kind == _NASAL:
            emit = "n"
            if i + 1 < n and text[i + 1] in labials:
                emit = "m"
            out.append(emit)
            i += 1
            continue

        if kind == _HALANT:
            # A halant only skips itself: the following consonant goes
            # through the normal consonant branch (nukta, ज्ञ, matra, and
            # the schwa rules) instead of being consumed bare.
            i += 1
            continue

        if kind == _SIGN:
            if val:
                out.append(val)
            i += 1
            continue

        if kind == _NUKTA:
            i += 1
            continue

        if kind == _OTHER and ch in ("।", "॥"):
            # Danda / double-danda: word break (resets the schwa state)
            # and dropped from the output, in both scripts.
            seen_vowel = False
            i += 1
            continue

        out.append(ch)
        i += 1

    # Script characters were present (otherwise we returned early above),
    # so collapse runs of whitespace left by dropped dandas and strip.
    return re.sub(r"\s+", " ", "".join(out)).strip()


_DV_MAPS = _make_script(
    base=0x0900,
    consonants={
        "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
        "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
        "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
        "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
        "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
        "य": "y", "र": "r", "ल": "l", "ळ": "l", "व": "v",
        "श": "sh", "ष": "sh", "स": "s", "ह": "h",
        "\u0958": "q",  # DEVANAGARI LETTER QA
        "\u0959": "kh",  # DEVANAGARI LETTER KHHA
        "\u095a": "gh",  # DEVANAGARI LETTER GHHA
        "\u095b": "z",  # DEVANAGARI LETTER ZA
        "\u095c": "d",  # DEVANAGARI LETTER DDDHA
        "\u095d": "dh",  # DEVANAGARI LETTER RHA
        "\u095e": "f",  # DEVANAGARI LETTER FA
        "\u095f": "y",  # DEVANAGARI LETTER YYA
    },
    vowels={
        "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
        "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऋ": "ri", "ॐ": "om",
        "ऍ": "e", "ऑ": "o",
    },
    matras={
        "ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo",
        "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ृ": "ri",
        "ॅ": "e", "ॉ": "o", "ॊ": "o", "ॆ": "e",
    },
    nasals={"ं": "n", "ँ": "n"},
    signs={"ः": "h", "ऽ": "'"},
    halant="्",
    nukta="़",
    nukta_forms={
        "क": "q", "ख": "kh", "ग": "gh", "ज": "z",
        "ड": "d", "ढ": "dh", "फ": "f", "य": "y",
    },
    yu_vowel="उ",
    labials="पबमभफ",
    gy=True,
)

_GG_MAPS = _make_script(
    base=0x0A00,
    consonants={
        "ਕ": "k", "ਖ": "kh", "ਗ": "g", "ਘ": "gh", "ਙ": "ng",
        "ਚ": "ch", "ਛ": "chh", "ਜ": "j", "ਝ": "jh", "ਞ": "ny",
        "ਟ": "t", "ਠ": "th", "ਡ": "d", "ਢ": "dh", "ਣ": "n",
        "ਤ": "t", "ਥ": "th", "ਦ": "d", "ਧ": "dh", "ਨ": "n",
        "ਪ": "p", "ਫ": "ph", "ਬ": "b", "ਭ": "bh", "ਮ": "m",
        "ਯ": "y", "ਰ": "r", "ਲ": "l", "ਵ": "v",
        "ਸ": "s", "ਹ": "h", "ੜ": "r",
        "\u0a36": "sh",  # GURMUKHI LETTER SHA
        "\u0a33": "l",   # GURMUKHI LETTER LLA
        "\u0a59": "kh",  # GURMUKHI LETTER KHHA
        "\u0a5a": "gh",  # GURMUKHI LETTER GHHA
        "\u0a5b": "z",   # GURMUKHI LETTER ZA
        "\u0a5e": "f",   # GURMUKHI LETTER FA
    },
    vowels={
        "ਅ": "a", "ਆ": "aa", "ਇ": "i", "ਈ": "ee", "ਉ": "u", "ਊ": "oo",
        "ਏ": "e", "ਐ": "ai", "ਓ": "o", "ਔ": "au", "ੴ": "ek onkar",
        "ੳ": "u", "ੲ": "i",
    },
    matras={
        "ਾ": "aa", "ਿ": "i", "ੀ": "ee", "ੁ": "u", "ੂ": "oo",
        "ੇ": "e", "ੈ": "ai", "ੋ": "o", "ੌ": "au",
    },
    nasals={"ਂ": "n", "ੰ": "n"},
    signs={"ਃ": "h"},
    halant="੍",
    nukta="਼",
    addak="ੱ",
    nukta_forms={
        "ਸ": "sh", "ਖ": "kh", "ਗ": "gh", "ਜ": "z", "ਫ": "f", "ਲ": "l",
    },
    yu_vowel="ਉ",
    labials="ਪਬਮਭਫ",
)


def transliterate_devanagari(text: str) -> str:
    """Casual Hindi (Latin) transliteration of Devanagari text."""
    return transliterate_indic(text, _DV_MAPS)


def transliterate_gurmukhi(text: str) -> str:
    """Casual Punjabi (Latin) transliteration of Gurmukhi text."""
    return transliterate_indic(text, _GG_MAPS)


# --- detection & dispatch ---

def detect_script(text: str) -> str:
    if not text or text.isascii():
        return "latin"
    dv = gg = 0
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F:
            dv += 1
        elif 0x0A00 <= o <= 0x0A7F:
            gg += 1
    if dv == 0 and gg == 0:
        return "latin"
    if gg > dv:
        return "gurmukhi"
    return "devanagari"


def transliterate(text: str, force_mode: str | None = None) -> tuple[str, str]:
    """Returns (transliterated_text, mode_name)."""
    if force_mode == "hindi":
        return transliterate_devanagari(text), "hindi"
    if force_mode == "pungabi":
        # Hidden alias for "punjabi", kept for compatibility.
        force_mode = "punjabi"
    if force_mode == "punjabi":
        return transliterate_gurmukhi(text), "punjabi"
    if not text or text.isascii():
        return text, "none"
    script = detect_script(text)
    if script == "devanagari":
        return transliterate_devanagari(text), "hindi"
    if script == "gurmukhi":
        return transliterate_gurmukhi(text), "punjabi"
    return text, "none"


def transliterate_lyrics(lyrics: SyncedLyrics,
                         force_mode: str | None = None) -> tuple[SyncedLyrics, str]:
    """Transliterate all lines, return (lyrics, mode)."""
    modes: set[str] = set()
    for line in lyrics.lines:
        translit, mode = transliterate(line.text, force_mode)
        line.text = translit
        if mode != "none":
            modes.add(mode)
    mode_str = modes.pop() if len(modes) == 1 else (
        "/".join(sorted(modes)) if modes else "none"
    )
    return lyrics, mode_str


# ──────────────────────────── providers ──────────────────────────────

_USER_AGENT = "lyricsync/1.0 (https://github.com/lyricsync)"


def _http_get_json(url: str, timeout: int = 10, retries: int = 2) -> dict | list | None:
    """GET JSON, retrying only on timeouts/connection errors, HTTP 429 and 5xx.

    Other 4xx responses (e.g. LRCLIB's 404 "not found") and undecodable
    bodies are returned as failures without retrying.
    """
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    for attempt in range(1 + retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or 500 <= exc.code < 600:
                if attempt < retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
            return None
        except (urllib.error.URLError, OSError):
            # Timeout/connection error: retry.
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            return None
        except (UnicodeDecodeError, json.JSONDecodeError):
            # Undecodable body: failure without retrying.
            return None
    return None


class LyricsProvider(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, artist: str, title: str, album: str = "",
              duration_s: float = 0) -> SyncedLyrics | None:
        ...


def _has_lyrics(value: object) -> bool:
    """True for a non-empty, non-whitespace lyric body."""
    return isinstance(value, str) and value.strip() != ""


def _norm_text(value: object) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _title_core(title: str) -> str:
    """Core title used for matching.

    Lowercase; drop anything after ``" - "``; drop ``(...)`` and ``[...]``
    groups; strip punctuation; collapse spaces.
    """
    t = title.lower()
    t = t.split(" - ", 1)[0]
    t = re.sub(r"\([^)]*\)", "", t)
    t = re.sub(r"\[[^]]*\]", "", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _duration_seconds(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


_tui_active = False
_warnings_buffer: list[str] = []


def _warn(msg: str) -> None:
    """Print a provider warning, buffered while curses is active."""
    if _tui_active:
        _warnings_buffer.append(msg)
    else:
        print(msg, file=sys.stderr)


class LRCLIBProvider(LyricsProvider):
    name = "lrclib"
    BASE = "https://lrclib.net/api"

    def _parse_result(self, data: dict, title: str, artist: str,
                      album: str) -> SyncedLyrics | None:
        if not data or not isinstance(data, dict):
            return None
        # None, "" and whitespace-only all mean "absent".
        synced = data.get("syncedLyrics")
        if _has_lyrics(synced):
            lyrics = parse_lrc(synced)
            lyrics.title = data.get("trackName") or title
            lyrics.artist = data.get("artistName") or artist
            lyrics.album = data.get("albumName") or album
            lyrics.source = "lrclib"
            return lyrics
        plain = data.get("plainLyrics")
        if _has_lyrics(plain):
            return parse_plain_lyrics(
                plain,
                title=data.get("trackName") or title,
                artist=data.get("artistName") or artist,
                album=data.get("albumName") or album,
                source="lrclib",
            )
        return None

    def _result_score(self, item: dict, title_norm: str, artist_norm: str,
                      target_dur: int | None) -> tuple[int, ...] | None:
        # Null-safe field access.
        item_title = _norm_text(item.get("trackName") or item.get("name"))
        item_artist = _norm_text(item.get("artistName"))
        if not item_title:
            return None  # never let an empty title match

        # --- Title matching on "core" titles ---
        title_core = _title_core(title_norm)
        item_title_core = _title_core(item_title)
        title_score = None
        if title_core == item_title_core:
            title_score = 2  # exact core match
        elif title_core and item_title_core:
            short, long = sorted((title_core, item_title_core), key=len)
            if short in long and len(short) / len(long) >= 0.6:
                title_score = 1  # contained core
            elif difflib.SequenceMatcher(None, title_core,
                                         item_title_core).ratio() >= 0.85:
                title_score = 1  # romanization variant on cores
        if title_score is None:
            return None  # title rejected

        # --- Artist matching ---
        if artist_norm:
            artist_match = False
            if item_artist:
                artist_match = (artist_norm in item_artist
                                or item_artist in artist_norm)
            if not artist_match:
                artist_match = (difflib.SequenceMatcher(None, artist_norm,
                                                        item_artist).ratio()
                                >= 0.6)
            if not artist_match:
                return None  # artist rejected
            artist_score = 1
        else:
            # Empty player artist: accept any artist, but score it 0.
            artist_score = 0

        score = [title_score, artist_score]
        if target_dur is not None:
            item_dur = _duration_seconds(item.get("duration"))
            if (item_dur is not None
                    and abs(item_dur - target_dur) <= 3):
                score.append(1)
            else:
                score.append(0)
        # Prefer synced over plain only among acceptable candidates.
        score.append(1 if _has_lyrics(item.get("syncedLyrics")) else 0)
        return tuple(score)

    def _search(self, results: list, title: str, artist: str,
                duration_s: float) -> dict | None:
        title_norm = _norm_text(title)
        artist_norm = _norm_text(artist)
        if not title_norm:
            return None
        if not isinstance(results, list):
            return None
        target_dur = int(duration_s) if duration_s > 0 else None
        best_item: dict | None = None
        best_score: tuple[int, ...] | None = None
        for item in results:
            if not isinstance(item, dict):
                continue
            score = self._result_score(item, title_norm, artist_norm,
                                       target_dur)
            if score is None:
                continue  # unrelated track: never returned
            if best_score is None or score > best_score:
                best_score = score
                best_item = item
        return best_item

    def fetch(self, artist: str, title: str, album: str = "",
              duration_s: float = 0) -> SyncedLyrics | None:
        params: dict[str, str | int] = {
            "artist_name": artist, "track_name": title,
        }
        if album:
            params["album_name"] = album
        if duration_s > 0:
            params["duration"] = int(duration_s)
        url = f"{self.BASE}/get?{urllib.parse.urlencode(params)}"
        data = _http_get_json(url)
        get_result = self._parse_result(data, title, artist, album)
        if get_result and get_result.synced:
            return get_result
        search_q = f"{artist} {title}"
        search_url = f"{self.BASE}/search?q={urllib.parse.quote(search_q)}"
        results = _http_get_json(search_url)
        best = self._search(results, title, artist, duration_s)
        search_result = self._parse_result(best, title, artist, album) \
            if best else None
        if search_result and search_result.synced:
            return search_result
        if get_result:
            return get_result
        return search_result


class LRCMuxProvider(LyricsProvider):
    name = "lrcmux"
    BASE = "https://api.lrcmux.dev"

    def _fetch_once(self, artist: str, title: str, album: str = "",
                    duration_s: float = 0) -> SyncedLyrics | None:
        params: dict[str, str | float] = {
            "artist": artist, "title": title,
            "format": "lrc", "level": "line", "sources": "!netease",
        }
        if album:
            params["album"] = album
        if duration_s > 0:
            params["duration"] = int(duration_s)
        url = f"{self.BASE}/get?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                lrc_text = resp.read().decode()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            return None
        if not lrc_text or not lrc_text.strip():
            return None
        lyrics = parse_lrc(lrc_text)
        if not lyrics.lines:
            return None
        lyrics.title = title
        lyrics.artist = artist
        lyrics.album = album
        lyrics.source = "lrcmux"
        return lyrics

    def fetch(self, artist: str, title: str, album: str = "",
              duration_s: float = 0) -> SyncedLyrics | None:
        result = self._fetch_once(artist, title, album, duration_s)
        if result is not None:
            return result
        if album:
            return self._fetch_once(artist, title, "", duration_s)
        return None


ALL_PROVIDERS: list[LyricsProvider] = [LRCLIBProvider(), LRCMuxProvider()]


def fetch_lyrics(artist: str, title: str, album: str = "",
                 duration_s: float = 0,
                 providers: list[LyricsProvider] | None = None,
                 timeout: float = 15.0) -> SyncedLyrics | None:
    """Fetch from providers concurrently; prefer synced over plain.

    Return as soon as the outcome can't change: a synced result from
    provider index i is returned once every provider with index < i has
    finished or failed; plain results are returned only after every
    provider has finished. An overall timeout (~15 s) caps the wait;
    worker threads are daemon so the process can always exit.
    """
    provs = providers if providers is not None else ALL_PROVIDERS
    results: list[SyncedLyrics | None] = [None] * len(provs)
    finished = [False] * len(provs)
    lock = threading.Lock()
    cond = threading.Condition(lock)
    deadline = time.monotonic() + timeout

    def run(i: int, p: LyricsProvider) -> None:
        try:
            res = p.fetch(artist, title, album, duration_s)
        except Exception as exc:
            _warn(f"[{p.name}] fetch error: {exc}")
            res = None
        with lock:
            results[i] = res
            finished[i] = True
            cond.notify_all()

    threads = [threading.Thread(target=run, args=(i, p), daemon=True)
               for i, p in enumerate(provs)]
    for t in threads:
        t.start()

    with lock:
        while True:
            # A synced result from provider i can be returned once every
            # earlier provider has finished (it can no longer win).
            for i, result in enumerate(results):
                if (result is not None and result.synced
                        and all(finished[:i])):
                    return result
            # Plain results only after every provider has finished.
            if all(finished):
                for result in results:
                    if result is not None and not result.synced:
                        return result
                return None
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                # Deadline: return the best available result (first synced by
                # provider order, else first plain). None only if nothing
                # produced a result.
                for result in results:
                    if result is not None and result.synced:
                        return result
                for result in results:
                    if result is not None and not result.synced:
                        return result
                return None
            cond.wait(min(remaining, 0.2))


# ──────────────────────────── players ────────────────────────────────

class Player(ABC):
    name: str = "base"

    @abstractmethod
    def detect(self) -> bool: ...

    @abstractmethod
    def get_playback(self) -> PlaybackInfo | None: ...

    def seek(self, position_ms: int) -> bool:
        return False


def _playerctl_list() -> list[str]:
    """List MPRIS player names via `playerctl -l` (empty if unavailable)."""
    try:
        r = subprocess.run(["playerctl", "-l"], capture_output=True,
                           text=True, timeout=5)
        if r.returncode == 0:
            return [line for line in r.stdout.splitlines() if line.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return []


class MPRISPlayer(Player):
    """Linux MPRIS/D-Bus players via playerctl."""
    name = "mpris"

    def __init__(self, player_name: str | None = None):
        self.player_name = player_name

    def detect(self) -> bool:
        return bool(_playerctl_list())

    def _run(self, *args: str) -> str | None:
        cmd = ["playerctl"]
        if self.player_name:
            cmd += ["-p", self.player_name]
        cmd += list(args)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return r.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def get_playback(self) -> PlaybackInfo | None:
        status = self._run("status")
        if status is None:
            return None
        raw_meta = self._run("metadata")
        if not raw_meta:
            return None
        props: dict[str, str] = {}
        for line in raw_meta.splitlines():
            parts = line.split(None, 2)
            if len(parts) >= 3:
                key = parts[1]
                val = parts[2]
                props[key] = val
        title = props.get("xesam:title", "")
        if not title:
            return None
        artist = props.get("xesam:artist", "")
        album = props.get("xesam:album", "")
        dur_ms = int(float(props.get("mpris:length", "0")) / 1000)
        pos_raw = self._run("position")
        pos_ms = int(float(pos_raw or "0") * 1000)
        playing = status.lower() == "playing"
        return PlaybackInfo(
            title=title, artist=artist, album=album,
            duration_ms=dur_ms, position_ms=pos_ms, playing=playing,
            player=self.player_name or "mpris",
        )

    def seek(self, position_ms: int) -> bool:
        pos_s = position_ms / 1000
        result = self._run("position", str(pos_s))
        return result is not None


def _parse_mpc_current(current_text: str) -> tuple[str, str, str, str] | None:
    """Parse mpc current --format output into (title, artist, album, file).

    The format is tab-separated; only the trailing newline is stripped so a
    leading tab (empty title) is preserved and fields are not shifted.
    Returns None when there is no current track.
    """
    if not current_text or not current_text.strip():
        return None
    parts = current_text.rstrip("\r\n").split("\t")
    title = parts[0] if len(parts) > 0 else ""
    artist = parts[1] if len(parts) > 1 else ""
    album = parts[2] if len(parts) > 2 else ""
    file_name = parts[3] if len(parts) > 3 else ""
    if not title:
        # Untagged tracks fall back to the file's base name without
        # extension, not the relative path.
        base = file_name.rsplit("/", 1)[-1] if file_name else ""
        title = base.rsplit(".", 1)[0] if base else ""
    return title, artist, album, file_name


def _parse_mpc_status(status_text: str) -> tuple[bool, int, int] | None:
    """Parse mpc status into (playing, elapsed_ms, dur_ms).

    Returns None when the player is stopped (neither playing nor paused).
    Elapsed and total times are parsed independently; each may be m:ss or
    h:mm:ss (whole-second resolution).
    """
    status_low = status_text.lower()
    if "[playing]" not in status_low and "[paused]" not in status_low:
        return None
    playing = "[playing]" in status_low
    elapsed_ms = dur_ms = 0
    lines = status_text.splitlines()
    if len(lines) >= 2:
        m = _MPC_TIME_RE.search(lines[1])
        if m:
            g = m.groups()
            if g[2] is not None:  # h:mm:ss
                pos_s = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2])
            else:  # m:ss
                pos_s = int(g[0]) * 60 + int(g[1])
            if g[5] is not None:  # h:mm:ss
                dur_s = int(g[3]) * 3600 + int(g[4]) * 60 + int(g[5])
            else:  # m:ss
                dur_s = int(g[3]) * 60 + int(g[4])
            elapsed_ms = pos_s * 1000
            dur_ms = dur_s * 1000
    return playing, elapsed_ms, dur_ms


class MPDPlayer(Player):
    """Music Player Daemon via mpc."""
    name = "mpd"

    def detect(self) -> bool:
        try:
            r = subprocess.run(["mpc", "status"], capture_output=True,
                               text=True, timeout=5)
            return r.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _mpc(self, *args: str) -> str | None:
        try:
            r = subprocess.run(["mpc"] + list(args), capture_output=True,
                               text=True, timeout=5)
            if r.returncode == 0:
                return r.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def get_playback(self) -> PlaybackInfo | None:
        status = self._mpc("status") or ""
        current = self._mpc("current", "--format",
                            "%title%\t%artist%\t%album%\t%file%")
        parsed_status = _parse_mpc_status(status)
        if parsed_status is None:
            return None
        playing, elapsed_ms, dur_ms = parsed_status
        parsed_current = _parse_mpc_current(current)
        if parsed_current is None:
            return None
        title, artist, album, _file_name = parsed_current
        return PlaybackInfo(
            title=title, artist=artist, album=album,
            duration_ms=dur_ms, position_ms=elapsed_ms,
            playing=playing, player="mpd",
        )

    def seek(self, position_ms: int) -> bool:
        # mpc `seek` takes seconds; send integer seconds.
        return self._mpc("seek", str(position_ms // 1000)) is not None


class CMUSPlayer(Player):
    """cmus via cmus-remote."""
    name = "cmus"

    def detect(self) -> bool:
        try:
            r = subprocess.run(["cmus-remote", "-Q"], capture_output=True,
                               text=True, timeout=5)
            return r.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _query(self) -> str | None:
        try:
            r = subprocess.run(["cmus-remote", "-Q"], capture_output=True,
                               text=True, timeout=5)
            if r.returncode == 0:
                return r.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def get_playback(self) -> PlaybackInfo | None:
        raw = self._query()
        if not raw:
            return None
        info: dict[str, str] = {}
        playing = False
        for line in raw.splitlines():
            if line.startswith("status playing"):
                playing = True
            elif line.startswith("duration "):
                # Bare seconds line (whole-second resolution).
                info["duration"] = line[len("duration "):]
            elif line.startswith("position "):
                # Bare seconds line (whole-second resolution).
                info["position"] = line[len("position "):]
            elif line.startswith("tag title "):
                info["title"] = line[len("tag title "):]
            elif line.startswith("tag artist "):
                info["artist"] = line[len("tag artist "):]
            elif line.startswith("tag album "):
                info["album"] = line[len("tag album "):]
        if not info.get("title"):
            return None
        return PlaybackInfo(
            title=info.get("title", ""),
            artist=info.get("artist", ""),
            album=info.get("album", ""),
            duration_ms=int(float(info.get("duration", "0")) * 1000),
            position_ms=int(float(info.get("position", "0")) * 1000),
            playing=playing, player="cmus",
        )

    def seek(self, position_ms: int) -> bool:
        # cmus-remote `seek` takes absolute seconds by default
        # (seek [+-]<n>[mh]); send integer seconds with no suffix.
        pos_s = position_ms // 1000
        try:
            result = subprocess.run(["cmus-remote", "-C",
                                     f"seek {pos_s}"],
                                    capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False


ALL_PLAYERS: list[Player] = [MPRISPlayer(), MPDPlayer(), CMUSPlayer()]


def detect_player(name: str | None = None) -> Player | None:
    if name:
        # Explicit backend name: return the player whenever its binary is
        # installed; a reachable session is not required (a session that
        # isn't running simply reports nothing to play). Error only when
        # the binary is missing.
        if name == "mpris":
            return MPRISPlayer() if shutil.which("playerctl") else None
        if name == "mpd":
            return MPDPlayer() if shutil.which("mpc") else None
        if name == "cmus":
            return CMUSPlayer() if shutil.which("cmus-remote") else None
        # Not a backend name: treat it as an MPRIS player instance if
        # playerctl lists a matching player (prefix match, since instances
        # look like chromium.instance1234).
        if shutil.which("playerctl"):
            for listed in _playerctl_list():
                if listed == name or listed.startswith(name):
                    return MPRISPlayer(player_name=listed)
        return None
    # Prefer a backend that is actually reachable; fall back to the first
    # installed binary only if none are reachable.
    for p in ALL_PLAYERS:
        if p.detect():
            return p
    for binary, cls in (("playerctl", MPRISPlayer), ("mpc", MPDPlayer),
                        ("cmus-remote", CMUSPlayer)):
        if shutil.which(binary):
            return cls()
    return None


# ──────────────────────────── sync engine ────────────────────────────

def find_current_line(lines: list[LyricLine], position_ms: int) -> int:
    """Return the index of the line currently playing."""
    if not lines:
        return -1
    timestamps = [l.time_ms for l in lines]
    idx = bisect.bisect_right(timestamps, position_ms) - 1
    return idx if idx >= 0 else -1


def wrap_lyric_line(text: str, width: int) -> list[str]:
    """Wrap a lyric line to fit within the given width."""
    text = text.strip()
    if not text:
        return ["♪"]
    width = max(1, width)  # clamp so very narrow terminals can't raise
    if len(text) <= width:
        return [text]
    return textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=True)


def _scroll_start(target_visual_row: int, total_rows: int, height: int) -> int:
    """Return the first visual row to show so target_visual_row is centered.

    Clamps to the valid range [0, max(0, total_rows - height)]. A height of
    zero or fewer returns 0.
    """
    if height <= 0 or total_rows <= 0:
        return 0
    start = target_visual_row - height // 2
    if start < 0:
        return 0
    max_start = max(0, total_rows - height)
    if start > max_start:
        return max_start
    return start


def _song_key(info: PlaybackInfo) -> tuple[str, str]:
    return (info.artist.lower().strip(), info.title.lower().strip())


def _check_song_change(
    player: Player,
    last_key: tuple[str, str],
) -> tuple[PlaybackInfo | None, bool, tuple[str, str]]:
    """Poll player. Returns (info, changed, updated_last_key)."""
    info = player.get_playback()
    if info is None or not info.playing:
        return info, False, last_key
    key = _song_key(info)
    changed = bool(key != last_key and (info.title or info.artist))
    new_last = key if changed else last_key
    return info, changed, new_last


_CACHE_MISS = object()


class _PlaybackPoller:
    """Shared state for live playback output modes.

    Lyric fetches on song change run in a background daemon thread so the
    polling loop never blocks; finished results are queued under the lock
    so no result is lost, and _collect applies only the one for the
    current song.
    """

    def __init__(self, player: Player, initial_lyrics: SyncedLyrics | None,
                 translit_mode: str | None,
                 providers: list[LyricsProvider] | None = None,
                 initial_info: PlaybackInfo | None = None):
        self.player = player
        self.translit_mode = translit_mode
        self.providers = providers or ALL_PROVIDERS
        self.lyrics = initial_lyrics
        self.is_fetching = False
        self._lock = threading.Lock()
        self._pending_key: tuple[str, str] | None = None
        self._results: collections.deque = collections.deque()
        # Cache only successful results: transient failures are retried
        # instead of poisoning the cache for the whole session.
        self._cache: dict[tuple[str, str], SyncedLyrics | None] = {}
        # Only seed last_key from the player's current track when we already
        # have lyrics for it; otherwise leave ("", "") so the first playing
        # poll starts a fetch (a startup failure gets retried).
        if initial_lyrics and initial_lyrics.lines:
            if initial_info:
                self.last_key = _song_key(initial_info)
                cache_key = _song_key(initial_info)
            else:
                self.last_key = _song_key(PlaybackInfo(
                    title=initial_lyrics.title,
                    artist=initial_lyrics.artist))
                cache_key = self.last_key
            # Key the initial cache entry by initial_info when given, else by
            # the lyrics' own title/artist.
            self._cache[cache_key] = initial_lyrics
        else:
            self.last_key = ("", "")

    def poll(self) -> tuple[PlaybackInfo | None, bool]:
        """Check for song changes; start a background fetch when changed.

        Returns (info, changed). Never blocks on network I/O.
        """
        info, changed, self.last_key = _check_song_change(
            self.player, self.last_key)
        if info is not None:
            current_key = _song_key(info)
            if changed:
                cached = self._cache.get(current_key, _CACHE_MISS)
                if cached is not _CACHE_MISS:
                    self.lyrics = cached
                    self._pending_key = None
                    self.is_fetching = False
                else:
                    self.lyrics = None
                    self.is_fetching = True
                    self._pending_key = current_key
                    threading.Thread(
                        target=self._fetch_worker,
                        args=(info.artist, info.title, info.album,
                              info.duration_ms / 1000, current_key),
                        name="lyricsync-fetch", daemon=True,
                    ).start()
            self._collect(current_key)
        return info, changed

    def _fetch_worker(self, artist: str, title: str, album: str,
                      dur_s: float, key: tuple[str, str]) -> None:
        try:
            lyrics = fetch_lyrics(artist, title, album, dur_s, self.providers)
            if lyrics is not None:
                lyrics, _ = transliterate_lyrics(lyrics, self.translit_mode)
        except Exception:
            lyrics = None
        with self._lock:
            self._results.append((key, lyrics))

    def _collect(self, current_key: tuple[str, str]) -> None:
        """Drain finished results; cache successes, apply only the current.

        Stale results (for a song that is no longer current) are never
        applied, so a late fetch can't resurrect an old song or leave
        is_fetching True forever.
        """
        with self._lock:
            pending = self._pending_key
            results = list(self._results)
            self._results.clear()
        applied = False
        for result_key, lyrics in results:
            if lyrics is not None:
                self._cache[result_key] = lyrics
            if result_key == current_key:
                self.lyrics = lyrics
                applied = True
        if applied:
            self.is_fetching = False
        elif pending is None:
            self.is_fetching = False

    def current_line(self, position_ms: int) -> LyricLine | None:
        if not self.lyrics or not self.lyrics.lines:
            return None
        if not self.lyrics.synced:
            # Unsynchronized lyrics must not be displayed as if synced.
            return None
        idx = find_current_line(self.lyrics.lines, position_ms)
        return self.lyrics.lines[idx] if idx >= 0 else None


# ──────────────────────────── output: plain ──────────────────────────

class _LineRenderer:
    """Render lyrics/status to a TTY (single line) or to out/err (non-TTY)."""

    def __init__(self, isatty: bool, out, err) -> None:
        self._isatty = isatty
        self._out = out
        self._err = err
        # One record of what is currently on the screen (TTY single line).
        self._screen: str | None = None
        # Non-TTY lyric tracking: last rendered line index; None resets.
        self._last_lyric_idx: int | None = None
        # Non-TTY status tracking: last rendered status text.
        self._last_status: str | None = None

    def lyric(self, text: str, line_idx: int | None, reset: bool = False) -> None:
        """Render a lyric line.

        TTY: redraw whenever text differs from what is on screen.
        Non-TTY: print to stdout once per change of line index (identical
        consecutive lyrics at different indices both print); reset on song
        change or backward seek.
        """
        if self._isatty:
            if text == self._screen:
                return
            self._screen = text
            self._out.write(f"\r\033[2K\033[1m{text}\033[0m")
            self._out.flush()
        else:
            if reset or line_idx != self._last_lyric_idx:
                self._out.write(text + "\n")
                self._out.flush()
                self._last_lyric_idx = line_idx

    def status(self, text: str) -> None:
        """Render a status message.

        TTY: redraw whenever text differs from what is on screen.
        Non-TTY: print to stderr only when the text changes; no ANSI.
        """
        if self._isatty:
            if text == self._screen:
                return
            self._screen = text
            self._out.write(f"\r\033[2K\033[1m{text}\033[0m")
            self._out.flush()
        else:
            if text != self._last_status:
                self._err.write(text + "\n")
                self._err.flush()
                self._last_status = text


def output_plain(lyrics: SyncedLyrics | None, player: Player,
                 translit_mode: str | None = None,
                 providers: list[LyricsProvider] | None = None,
                 initial_info: PlaybackInfo | None = None) -> None:
    if lyrics is not None:
        lyrics, _ = transliterate_lyrics(lyrics, translit_mode)
    poller = _PlaybackPoller(player, lyrics, translit_mode, providers,
                             initial_info=initial_info)
    renderer = _LineRenderer(sys.stdout.isatty(), sys.stdout, sys.stderr)
    # One unsynced stderr note per song (track key); reset on song change.
    unsynced_note_key: tuple[str, str] | None = None
    reset_lyric = False
    last_position_ms: int | None = None

    try:
        while True:
            info, changed = poller.poll()
            if changed:
                if info:
                    renderer.status(
                        f"Fetching lyrics for: {info.artist} — {info.title}")
                reset_lyric = True
                continue
            if info is None:
                renderer.status("No playback detected. Waiting...")
                time.sleep(2)
                continue
            if not info.playing:
                renderer.status(f"Paused: {info.artist} - {info.title}")
                time.sleep(1)
                continue
            if poller.lyrics is not None and not poller.lyrics.synced:
                key = (poller.lyrics.artist, poller.lyrics.title)
                if unsynced_note_key != key:
                    unsynced_note_key = key
                    print(_UNSYNCED_NOTE, file=sys.stderr)
                time.sleep(0.5)
                continue
            if poller.is_fetching:
                time.sleep(0.25)
                continue
            line = poller.current_line(info.position_ms)
            if line is None:
                time.sleep(0.5 if not poller.lyrics else 0.3)
                continue
            idx = find_current_line(poller.lyrics.lines, info.position_ms)
            backward = (last_position_ms is not None
                        and info.position_ms < last_position_ms)
            renderer.lyric(line.text.strip() or "♪", idx,
                           reset=reset_lyric or backward)
            reset_lyric = False
            last_position_ms = info.position_ms
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass


# ──────────────────────────── output: once ───────────────────────────

def output_once(lyrics: SyncedLyrics, translit_mode: str | None = None) -> None:
    lyrics, _ = transliterate_lyrics(lyrics, translit_mode)
    for line in lyrics.lines:
        text = line.text.strip() or "♪"
        if lyrics.synced:
            mm = line.time_ms // 60000
            ss = (line.time_ms % 60000) // 1000
            cs = (line.time_ms % 1000) // 10
            print(f"[{mm:02d}:{ss:02d}.{cs:02d}] {text}")
        else:
            print(text)


# ──────────────────────────── output: JSON ───────────────────────────

def output_json(lyrics: SyncedLyrics, translit_mode: str | None = None) -> None:
    lyrics, mode = transliterate_lyrics(lyrics, translit_mode)
    result = {
        "title": lyrics.title,
        "artist": lyrics.artist,
        "album": lyrics.album,
        "source": lyrics.source,
        "transliteration_mode": mode,
        "synced": lyrics.synced,
        "lines": [
            {
                "time_ms": l.time_ms,
                "time": f"{l.time_ms // 60000:02d}"
                        f":{(l.time_ms % 60000) // 1000:02d}"
                        f".{(l.time_ms % 1000) // 10:02d}",
                "text": l.text,
            }
            for l in lyrics.lines
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ──────────────────────────── output: TUI ────────────────────────────

def _init_color_pairs_256() -> None:
    pairs = {
        1: (curses.COLOR_WHITE, -1),
        2: (curses.COLOR_YELLOW, -1),
        3: (curses.COLOR_CYAN, -1),
        4: (curses.COLOR_GREEN, -1),
        5: (curses.COLOR_MAGENTA, -1),
        6: (252, -1),
        7: (247, -1),
        8: (242, -1),
        9: (238, -1),
        10: (235, -1),
        11: (233, -1),
        12: (curses.COLOR_CYAN, 235),
    }
    for pair, (fg, bg) in pairs.items():
        try:
            curses.init_pair(pair, fg, bg)
        except curses.error:
            pass


def _init_color_pairs_basic() -> None:
    # Fewer than 256 colors: use the 8 basic colors; A_BOLD/A_DIM keep the
    # playing/selected highlights readable.
    pairs = {
        1: (curses.COLOR_WHITE, -1),
        2: (curses.COLOR_YELLOW, -1),
        3: (curses.COLOR_CYAN, -1),
        4: (curses.COLOR_GREEN, -1),
        5: (curses.COLOR_MAGENTA, -1),
        6: (curses.COLOR_WHITE, -1),
        7: (curses.COLOR_WHITE, -1),
        8: (curses.COLOR_WHITE, -1),
        9: (curses.COLOR_WHITE, -1),
        10: (curses.COLOR_WHITE, -1),
        11: (curses.COLOR_WHITE, -1),
        12: (curses.COLOR_CYAN, -1),
    }
    for pair, (fg, bg) in pairs.items():
        try:
            curses.init_pair(pair, fg, bg)
        except curses.error:
            pass


def output_tui(lyrics: SyncedLyrics | None, player: Player,
               translit_mode: str | None = None,
               providers: list[LyricsProvider] | None = None,
               initial_info: PlaybackInfo | None = None) -> None:
    if lyrics is not None:
        lyrics, _ = transliterate_lyrics(lyrics, translit_mode)
    poller = _PlaybackPoller(player, lyrics, translit_mode, providers,
                             initial_info=initial_info)

    def draw(stdscr: "curses.window") -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        if curses.has_colors() and curses.COLORS >= 256:
            _init_color_pairs_256()
        elif curses.has_colors():
            _init_color_pairs_basic()

        sel_idx = -1  # -1 means "follow playback"
        view_offset = 0  # unsynced scrolling offset, in visual rows
        _GRADIENT = [7, 8, 9, 10, 11]
        prev_lyrics: SyncedLyrics | None = None
        last_input: float | None = None  # monotonic time of last key press

        def line_color(dist: int) -> int:
            idx = min(dist - 1, len(_GRADIENT) - 1)
            attr = curses.color_pair(_GRADIENT[max(0, idx)])
            if curses.COLORS < 256 and dist >= 2:
                attr |= curses.A_DIM  # fade distant lines on basic terminals
            return attr

        def _draw_header(stdscr: "curses.window", info: PlaybackInfo,
                         lyrics: SyncedLyrics | None, h: int, w: int) -> None:
            if info is None or h < 1 or w < 1:
                return
            # Prefer the player's real length; fall back to the last lyric
            # timestamp only when the player reports 0.
            dur = info.duration_ms if info.duration_ms > 0 else (
                lyrics.last_line_ms if lyrics and lyrics.last_line_ms > 0 else 0)
            mm_now = info.position_ms // 60000
            ss_now = (info.position_ms % 60000) // 1000
            mm_dur = dur // 60000
            ss_dur = (dur % 60000) // 1000
            header = (f" {info.artist} - {info.title}  "
                      f"[{mm_now:02d}:{ss_now:02d} / {mm_dur:02d}:{ss_dur:02d}] ")
            if len(header) > w - 1:
                header = header[: max(0, w - 4)] + "..."
            x = max(0, (w - len(header)) // 2)
            try:
                stdscr.addstr(0, x, header[: max(0, w - 1 - x)],
                              curses.color_pair(2))
            except curses.error:
                pass

        def _draw_footer(stdscr: "curses.window", lyrics: SyncedLyrics | None,
                         h: int, w: int, unsynced: bool = False) -> None:
            if lyrics is None or h < 1 or w < 1:
                return
            footer = f" source:{lyrics.source} "
            if unsynced:
                footer += " unsynced"
            x = max(0, w - len(footer) - 1)
            try:
                stdscr.addstr(h - 1, x, footer[: max(0, w - 1 - x)],
                              curses.color_pair(2))
            except curses.error:
                pass

        def draw_lyrics(stdscr: "curses.window", lyr: SyncedLyrics,
                        info: PlaybackInfo, sel: int, unsynced: bool) -> None:
            nonlocal view_offset
            h, w = stdscr.getmaxyx()
            lyrics_h = h - 2
            if lyrics_h <= 0 or w < 1:
                return
            playing_idx = find_current_line(lyr.lines, info.position_ms)

            # Build wrapped rows for every lyric line.
            prefix_w = 2  # "▸ " prefix on the first row of the selected line
            max_text_width = max(1, w - 1 - prefix_w - 3)
            visible_lines: list[tuple[int, list[str]]] = []
            for line_idx in range(len(lyr.lines)):
                text = lyr.lines[line_idx].text.strip() or "♪"
                wrapped = wrap_lyric_line(text, max_text_width)
                visible_lines.append((line_idx, wrapped))
            total_visual_rows = sum(len(wrapped) for _, wrapped in visible_lines)

            if unsynced:
                # Static view from the top; no playing highlight.
                view_offset = max(0, min(view_offset,
                                         max(0, total_visual_rows - lyrics_h)))
                start_visual_row = view_offset
            else:
                # Center on the selected line when a selection is active,
                # otherwise on the playing line. During the intro
                # (playing_idx == -1 and no selection) start at the top.
                target_line = sel if sel >= 0 else playing_idx
                if target_line < 0:
                    start_visual_row = 0
                else:
                    target_visual_row = 0
                    for line_idx, wrapped in visible_lines:
                        if line_idx == target_line:
                            break
                        target_visual_row += len(wrapped)
                    start_visual_row = _scroll_start(target_visual_row,
                                                     total_visual_rows,
                                                     lyrics_h)

            # Style every wrapped row of a line; keep the prefix on the
            # first row only.
            visual_row = 0
            for line_idx, wrapped in visible_lines:
                is_playing = (not unsynced and playing_idx == line_idx)
                is_selected = sel >= 0 and line_idx == sel
                dist = abs(line_idx - max(playing_idx, 0))
                for wrap_idx, wrap_text in enumerate(wrapped):
                    if visual_row < start_visual_row:
                        visual_row += 1
                        continue
                    if visual_row >= start_visual_row + lyrics_h:
                        break
                    y = visual_row - start_visual_row + 1  # +1 for header
                    is_first_wrap = wrap_idx == 0
                    display_prefix = ("▸ " if (is_selected and is_first_wrap)
                                      else "")
                    display = (display_prefix + wrap_text)[: max(0, w - 1)]
                    x = max(0, (w - len(display)) // 2)
                    if unsynced:
                        # One fixed readable attribute: no gradient, no
                        # playing highlight (all timestamps are 0).
                        attr = curses.color_pair(1)
                    elif is_selected and is_playing:
                        attr = (curses.A_BOLD | curses.A_UNDERLINE
                                | curses.color_pair(5))
                    elif is_selected:
                        attr = curses.A_BOLD | curses.color_pair(5)
                    elif is_playing:
                        attr = (curses.A_BOLD | curses.A_UNDERLINE
                                | curses.color_pair(12))
                    else:
                        attr = line_color(dist)
                    try:
                        stdscr.addstr(y, x, display, attr)
                    except curses.error:
                        pass
                    visual_row += 1

        while True:
            # Fall back to follow mode after about 5 s without input.
            if (sel_idx >= 0 and last_input is not None
                    and time.monotonic() - last_input > 5):
                sel_idx = -1
            info, changed = poller.poll()
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            _draw_header(stdscr, info, poller.lyrics, h, w)
            lyr = poller.lyrics
            unsynced = lyr is not None and not lyr.synced
            # Reset selection/scroll on track change or when the lyrics
            # object is replaced, so stale selection doesn't carry over.
            if changed or lyr is not prev_lyrics:
                sel_idx = -1
                view_offset = 0
            prev_lyrics = lyr
            _draw_footer(stdscr, lyr, h, w, unsynced=unsynced)

            if h < 2 or w < 1:
                if h >= 1 and w >= len("terminal too small") + 1:
                    try:
                        stdscr.addstr(0, 0, "terminal too small")
                    except curses.error:
                        pass
            elif info is None:
                msg = "No playback detected. Waiting..."
                try:
                    stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2),
                                  msg[: max(0, w - 1)])
                except curses.error:
                    pass
            elif not info.playing:
                msg = (f"Paused: {info.artist} - {info.title}"
                       if info.artist or info.title else "Paused...")
                try:
                    stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2),
                                  msg[: max(0, w - 1)])
                except curses.error:
                    pass
            elif lyr is None or not lyr.lines:
                msg = "Fetching lyrics..." if poller.is_fetching else "No lyrics"
                try:
                    stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2),
                                  msg[: max(0, w - 1)])
                except curses.error:
                    pass
            else:
                playing_idx = find_current_line(lyr.lines, info.position_ms)
                draw_lyrics(stdscr, lyr, info, sel_idx, unsynced)
                stdscr.refresh()
                stdscr.timeout(150)
                key = stdscr.getch()
                if key == ord('q'):
                    break
                elif key == curses.KEY_RESIZE:
                    pass
                elif key in (10, 13, curses.KEY_ENTER):
                    # Enter seeks only when a selection is active; unsynced
                    # lyrics and "follow playback" mode do nothing.
                    if not unsynced and sel_idx >= 0:
                        if sel_idx < len(lyr.lines):
                            player.seek(lyr.lines[sel_idx].time_ms)
                        sel_idx = -1
                elif key == curses.KEY_UP:
                    if unsynced:
                        view_offset = max(0, view_offset - 1)
                    else:
                        if sel_idx < 0:
                            sel_idx = playing_idx
                        sel_idx = max(0, min(len(lyr.lines) - 1, sel_idx - 1))
                elif key == curses.KEY_DOWN:
                    if unsynced:
                        view_offset += 1
                    else:
                        if sel_idx < 0:
                            sel_idx = playing_idx
                        sel_idx = max(0, min(len(lyr.lines) - 1, sel_idx + 1))
                if key != -1:
                    last_input = time.monotonic()
                    stdscr.timeout(0)
                    while stdscr.getch() != -1:
                        pass
                    stdscr.timeout(150)
                continue
            stdscr.refresh()
            # Poll every iteration so `q` works in every state.
            stdscr.timeout(500)
            key = stdscr.getch()
            if key == ord('q'):
                break
            if key != -1:
                last_input = time.monotonic()
            # KEY_RESIZE and -1 simply redraw on the next iteration.

    try:
        global _tui_active
        _tui_active = True
        curses.wrapper(draw)
    except KeyboardInterrupt:
        pass
    finally:
        _tui_active = False
        # Flush warnings buffered while curses was active.
        for msg in _warnings_buffer:
            print(msg, file=sys.stderr)
        _warnings_buffer.clear()


# ──────────────────────────── output: notify ─────────────────────────

_NOTIFY_CMD = shutil.which("notify-send")
# Whether --print-id / --replace-id are supported by the installed libnotify.
# Set to False on the first failure so later calls skip those flags.
_NOTIFY_MODERN = True
# Single wording for the unsynced note, used by main() (--once/--json) and
# by output_plain/output_notify (once per song).
_UNSYNCED_NOTE = "only unsynchronized lyrics available"


def _escape_notify_body(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def notify(line: str, _last_id: list[str] | None = None) -> None:
    """Send or replace a desktop notification."""
    global _NOTIFY_MODERN
    if not _NOTIFY_CMD:
        return
    if _last_id is None:
        _last_id = []
    body = _escape_notify_body(line)
    base = [_NOTIFY_CMD, "--hint=int:transient:1", "-a", "lyricsync",
            "--", "lyricsync", body]
    try:
        if _last_id:
            cmd = (_NOTIFY_CMD, "--replace-id=" + _last_id[0]) + tuple(base[1:])
            subprocess.run(list(cmd), timeout=2, capture_output=True,
                           check=True)
        elif _NOTIFY_MODERN:
            r = subprocess.run(
                [_NOTIFY_CMD, "--print-id"] + list(base[1:]),
                capture_output=True, text=True, timeout=2, check=True)
            if r.stdout.strip():
                _last_id.append(r.stdout.strip())
        else:
            subprocess.run(base, timeout=2, capture_output=True, check=True)
    except subprocess.CalledProcessError:
        # Old libnotify: --print-id/--replace-id not supported. Retry once
        # without them and stop using them afterwards.
        _NOTIFY_MODERN = False
        try:
            subprocess.run(base, timeout=2, capture_output=True, check=True)
        except (subprocess.TimeoutExpired, FileNotFoundError,
                subprocess.CalledProcessError):
            pass
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def output_notify(lyrics: SyncedLyrics | None, player: Player,
                  translit_mode: str | None = None,
                  providers: list[LyricsProvider] | None = None,
                  initial_info: PlaybackInfo | None = None) -> None:
    if lyrics is not None:
        lyrics, _ = transliterate_lyrics(lyrics, translit_mode)
    poller = _PlaybackPoller(player, lyrics, translit_mode, providers,
                             initial_info=initial_info)
    last_idx = -1
    last_id: list[str] = []
    unsynced_note_key: tuple[str, str] | None = None
    try:
        while True:
            info, changed = poller.poll()
            if changed:
                last_idx = -1
                continue
            if info is None or not info.playing:
                last_idx = -1
                time.sleep(1)
                continue
            if poller.lyrics is not None and not poller.lyrics.synced:
                key = (poller.lyrics.artist, poller.lyrics.title)
                if unsynced_note_key != key:
                    unsynced_note_key = key
                    print(_UNSYNCED_NOTE, file=sys.stderr)
                time.sleep(0.5)
                continue
            line = poller.current_line(info.position_ms)
            if poller.is_fetching:
                time.sleep(0.3)
                continue
            if line is None:
                time.sleep(0.5)
                continue
            idx = find_current_line(poller.lyrics.lines, info.position_ms)
            if idx != last_idx:
                notify(line.text.strip() or "♪", last_id)
                last_idx = idx
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass


# ──────────────────────────── CLI ────────────────────────────────────

def _transliterate_mode(value: str) -> str:
    """Normalize --transliterate values; keep the hidden "pungabi" alias
    working (case-insensitive) without advertising it in --help."""
    if value.lower() == "pungabi":
        return "punjabi"
    return value


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lyricsync",
        description="CLI lyrics synchronization tool — LRCLIB + LRCMux",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--tui", action="store_true",
                      help="Interactive terminal UI showing as many lyric "
                           "lines as fit")
    mode.add_argument("--notify", action="store_true",
                      help="Show lyrics as desktop notifications")
    mode.add_argument("--json", action="store_true", dest="json_output",
                      help="Output machine-readable JSON")
    mode.add_argument("--once", action="store_true",
                      help="Print full lyrics once and exit")
    p.add_argument("--player", type=str, default=None,
                   help="Player backend: mpris, mpd, cmus (or auto-detect)")
    p.add_argument("--transliterate", type=_transliterate_mode, default=None,
                   choices=["hindi", "punjabi"],
                   help="Force transliteration mode: hindi or punjabi")
    p.add_argument("--artist", type=str, default=None,
                   help="Artist name (for manual lookup)")
    p.add_argument("--title", type=str, default=None,
                   help="Song title (for manual lookup)")
    p.add_argument("--album", type=str, default=None,
                   help="Album name (for manual lookup)")
    p.add_argument("--provider", type=str, default=None,
                   choices=["lrclib", "lrcmux"],
                   help="Force a single lyrics provider")
    return p


def resolve_providers(name: str | None) -> list[LyricsProvider]:
    if name == "lrclib":
        return [LRCLIBProvider()]
    if name == "lrcmux":
        return [LRCMuxProvider()]
    return list(ALL_PROVIDERS)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.notify and not _NOTIFY_CMD:
        print("notify-send is not installed; cannot show notifications",
              file=sys.stderr)
        return 1

    player: Player | None = None
    startup_info: PlaybackInfo | None = None
    title = args.title or ""
    artist = args.artist or ""
    album = args.album or ""
    dur_s = 0.0

    live_mode = not args.once and not args.json_output
    if live_mode or args.notify:
        player = detect_player(args.player)
        if player is None:
            print("No supported player detected. Use --player or install "
                  "playerctl/mpc/cmus-remote.", file=sys.stderr)
            return 1
        print(f"Using player: {player.name}", file=sys.stderr)
    elif not title or not artist:
        player = detect_player(args.player)

    if player:
        # One startup read of the player's current track; its key seeds
        # the poller so a manual --artist/--title lookup stays in place
        # until the track actually changes.
        startup_info = player.get_playback()
        if startup_info and (not title or not artist):
            title = title or startup_info.title
            artist = artist or startup_info.artist
        # Only inherit duration/album from the playing track when the
        # resolved title/artist refer to the same song; a manual
        # --artist/--title lookup for a different song must not leak
        # the playing track's duration or album.
        same_song = (startup_info is not None
                     and _song_key(PlaybackInfo(title=title,
                                                artist=artist))
                     == _song_key(startup_info))
        if same_song:
            album = album or startup_info.album
            dur_s = startup_info.duration_ms / 1000
        else:
            album = album or ""
            dur_s = 0.0

    providers = resolve_providers(args.provider)
    have_metadata = bool(title or artist)

    if live_mode and not have_metadata:
        # No manual metadata and no readable playback: skip the initial
        # fetch, start the poller with lyrics=None and wait for playback.
        lyrics = None
    elif not have_metadata:
        print("No song metadata available. Use --artist and --title.",
              file=sys.stderr)
        return 1
    else:
        print(f"Fetching lyrics for: {artist} — {title}", file=sys.stderr)
        lyrics = fetch_lyrics(artist, title, album, dur_s, providers)
        if lyrics is None:
            print("No lyrics found from any provider.", file=sys.stderr)
        elif not lyrics.synced and (args.once or args.json_output):
            print(_UNSYNCED_NOTE, file=sys.stderr)

    if args.json_output or args.once:
        if lyrics is None:
            return 1
        if args.json_output:
            output_json(lyrics, args.transliterate)
        else:
            output_once(lyrics, args.transliterate)
    elif args.notify:
        output_notify(lyrics, player, args.transliterate, providers,
                      startup_info)
    elif args.tui:
        output_tui(lyrics, player, args.transliterate, providers,
                   startup_info)
    else:
        output_plain(lyrics, player, args.transliterate, providers,
                     startup_info)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
