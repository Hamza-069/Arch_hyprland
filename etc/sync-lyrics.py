#!/usr/bin/env python3
"""
sync-lyrics.py — synced (LRC) lyrics for whatever is currently playing.

Pulls track metadata from MPRIS (via playerctl) and tries multiple lyric
backends in order:

    Local (~/Music/lyrics/*.lrc) -> LRCLIB -> LrcMux

Gurmukhi (Punjabi) lyrics are automatically transliterated into casual
Latin-script "Punglish", and Devanagari (Hindi) into casual "Hinglish",
unless --no-romanize is used.

Gurmukhi extended characters such as ਫ਼, ਜ਼, ਖ਼, ਗ਼, ਸ਼ and Gurmukhi digits
such as ੧, ੨, ੩ are converted as well.

Usage:
    ./sync-lyrics.py
    ./sync-lyrics.py --notify
    ./sync-lyrics.py --once
    ./sync-lyrics.py --json
    ./sync-lyrics.py --json --once
    ./sync-lyrics.py --no-romanize
    ./sync-lyrics.py --backends lrclib
    ./sync-lyrics.py --local-dir ~/lyrics

Requires:
    - playerctl
    - python requests
    - notify-send (only for --notify)
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import requests


# =============================================================================
# Configuration
# =============================================================================

LRCLIB_GET = "https://lrclib.net/api/get"
LRCLIB_SEARCH = "https://lrclib.net/api/search"

LRCMUX_GET = "https://api.lrcmux.dev/get"
LRCMUX_HEADERS = {
    "User-Agent": "sync-lyrics (https://github.com/caelestia-dots/shell-inspired)",
}

CACHE_DIR = Path.home() / ".cache" / "sync-lyrics"
DEFAULT_LOCAL_DIR = Path.home() / "Music" / "lyrics"

POLL_INTERVAL = 0.5

LRC_LINE_RE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")


# =============================================================================
# Gurmukhi -> casual Latin ("Punglish")
# =============================================================================

_CONSONANTS = {
    # Basic Gurmukhi
    "ਸ": "s",
    "ਹ": "h",

    "ਕ": "k",
    "ਖ": "kh",
    "ਗ": "g",
    "ਘ": "gh",
    "ਙ": "ng",

    "ਚ": "ch",
    "ਛ": "chh",
    "ਜ": "j",
    "ਝ": "jh",
    "ਞ": "ny",

    "ਟ": "t",
    "ਠ": "th",
    "ਡ": "d",
    "ਢ": "dh",
    "ਣ": "n",

    "ਤ": "t",
    "ਥ": "th",
    "ਦ": "d",
    "ਧ": "dh",
    "ਨ": "n",

    "ਪ": "p",
    "ਫ": "ph",
    "ਬ": "b",
    "ਭ": "bh",
    "ਮ": "m",

    "ਯ": "y",
    "ਰ": "r",
    "ਲ": "l",
    "ਵ": "v",
    "ੜ": "r",

    # Extended Gurmukhi letters / precomposed nukta letters
    "ਖ਼": "kh",
    "ਗ਼": "gh",
    "ਜ਼": "z",
    "ਫ਼": "f",
    "ਸ਼": "sh",
}

# Decomposed nukta variants.
#
# Examples:
#   ਜ਼  -> z
#   ਫ਼  -> f
#   ਗ਼  -> gh
#
# NFC normalization normally turns many of these into precomposed Unicode,
# but keeping this table makes the tokenizer robust.
_NUKTA_VARIANTS = {
    "ਸ": "sh",
    "ਖ": "kh",
    "ਗ": "gh",
    "ਜ": "z",
    "ਫ": "f",
    "ਲ": "l",
}

_INDEP_VOWELS = {
    "ਅ": "a",
    "ਆ": "aa",
    "ਇ": "i",
    "ਈ": "ee",
    "ਉ": "u",
    "ਊ": "oo",
    "ਏ": "e",
    "ਐ": "ai",
    "ਓ": "o",
    "ਔ": "au",
}

_MATRAS = {
    "ਾ": "aa",
    "ਿ": "i",
    "ੀ": "ee",
    "ੁ": "u",
    "ੂ": "oo",
    "ੇ": "e",
    "ੈ": "ai",
    "ੋ": "o",
    "ੌ": "au",
}

_GM_DIGITS = {
    "੦": "0",
    "੧": "1",
    "੨": "2",
    "੩": "3",
    "੪": "4",
    "੫": "5",
    "੬": "6",
    "੭": "7",
    "੮": "8",
    "੯": "9",
}

_ADDAK = "ੱ"
_TIPPI = "ੰ"
_BINDI = "ਂ"
_HALANT = "੍"
_NUKTA = "਼"

_NASAL_MARKS = (_TIPPI, _BINDI)

_NASAL_BASES = {
    "n",
    "m",
    "ng",
    "ny",
}


def _is_gurmukhi(text):
    return any("\u0A00" <= ch <= "\u0A7F" for ch in text)


def _gm_tokenize(word):
    """
    Convert one Gurmukhi word into syllable-like structures.
    """
    word = unicodedata.normalize("NFC", word)

    chars = list(word)
    n = len(chars)

    syllables = []
    i = 0
    geminate_next = False

    while i < n:
        ch = chars[i]

        # --------------------------------------------------------------
        # Addak
        # --------------------------------------------------------------
        if ch == _ADDAK:
            geminate_next = True
            i += 1
            continue

        # --------------------------------------------------------------
        # Gurmukhi digits
        # --------------------------------------------------------------
        if ch in _GM_DIGITS:
            syllables.append(
                {
                    "base": None,
                    "vowel": None,
                    "is_matra": False,
                    "nasal": None,
                    "indep": False,
                    "literal": _GM_DIGITS[ch],
                }
            )
            i += 1
            continue

        # --------------------------------------------------------------
        # Consonants
        # --------------------------------------------------------------
        if ch in _CONSONANTS:
            base = _CONSONANTS[ch]

            # Handle decomposed nukta if one remains after normalization.
            if (
                i + 1 < n
                and chars[i + 1] == _NUKTA
                and ch in _NUKTA_VARIANTS
            ):
                base = _NUKTA_VARIANTS[ch]
                i += 1

            if geminate_next:
                if base:
                    base = base[0] + base
                geminate_next = False

            vowel = "a"
            is_matra = False

            j = i + 1

            # Vowel matra
            if j < n and chars[j] in _MATRAS:
                vowel = _MATRAS[chars[j]]
                is_matra = True
                i = j

            # Halant
            elif j < n and chars[j] == _HALANT:
                vowel = ""
                is_matra = True
                i = j

            # Nasal mark
            nasal = None
            k = i + 1

            if k < n and chars[k] in _NASAL_MARKS:
                nasal = chars[k]
                i = k

            syllables.append(
                {
                    "base": base,
                    "vowel": vowel,
                    "is_matra": is_matra,
                    "nasal": nasal,
                    "indep": False,
                    "literal": None,
                }
            )

            i += 1
            continue

        # --------------------------------------------------------------
        # Independent vowels
        # --------------------------------------------------------------
        if ch in _INDEP_VOWELS:
            vowel = _INDEP_VOWELS[ch]
            nasal = None

            k = i + 1

            if k < n and chars[k] in _NASAL_MARKS:
                nasal = chars[k]
                i = k

            syllables.append(
                {
                    "base": None,
                    "vowel": vowel,
                    "is_matra": False,
                    "nasal": nasal,
                    "indep": True,
                    "literal": None,
                }
            )

            i += 1
            continue

        # --------------------------------------------------------------
        # Standalone nukta
        # --------------------------------------------------------------
        if ch == _NUKTA:
            i += 1
            continue

        # --------------------------------------------------------------
        # Preserve punctuation, Latin text, symbols, etc.
        # --------------------------------------------------------------
        syllables.append(
            {
                "base": None,
                "vowel": None,
                "is_matra": False,
                "nasal": None,
                "indep": False,
                "literal": ch,
            }
        )

        i += 1

    return syllables


def _gm_apply_rules(syllables):
    # ------------------------------------------------------------------
    # i + independent-vowel glide
    #
    # Roughly:
    #   pi + aa -> pyaa
    # ------------------------------------------------------------------
    for idx in range(1, len(syllables)):
        cur = syllables[idx]
        prev = syllables[idx - 1]

        if (
            cur["indep"]
            and prev["literal"] is None
            and prev["is_matra"]
            and prev["vowel"] == "i"
        ):
            prev["vowel"] = ""
            cur["vowel"] = "y" + cur["vowel"]

    # ------------------------------------------------------------------
    # Nasalization
    # ------------------------------------------------------------------
    for s in syllables:
        if s["literal"] is not None or not s["nasal"]:
            continue

        # Casual Romanization.
        if s["vowel"] == "oo":
            s["vowel"] = "u"
        elif s["vowel"] == "ee":
            s["vowel"] = "i"

        skip_n = (
            s["base"] is not None
            and s["base"] in _NASAL_BASES
        )

        s["_append_n"] = not skip_n

    # ------------------------------------------------------------------
    # Final aa -> a for casual Romanization
    # ------------------------------------------------------------------
    real = [s for s in syllables if s["literal"] is None]

    if real:
        last = real[-1]

        if (
            last["is_matra"]
            and last["vowel"] == "aa"
            and not last["nasal"]
        ):
            last["vowel"] = "a"

    # ------------------------------------------------------------------
    # Final bare consonant drops inherent schwa.
    # ------------------------------------------------------------------
    if len(real) > 1:
        last = real[-1]

        if (
            not last["indep"]
            and not last["is_matra"]
            and last["vowel"] == "a"
            and not last["nasal"]
        ):
            last["vowel"] = ""

    return syllables


def _render(syllables):
    out = []

    for s in syllables:
        if s["literal"] is not None:
            out.append(s["literal"])
            continue

        piece = (s["base"] or "") + (s["vowel"] or "")

        if s["nasal"] and s.get("_append_n", True):
            piece += "n"

        out.append(piece)

    return "".join(out)


def _gm_word(word):
    word = unicodedata.normalize("NFC", word)

    if not word:
        return ""

    return _render(
        _gm_apply_rules(
            _gm_tokenize(word)
        )
    )


def transliterate_gurmukhi(text):
    """
    Gurmukhi -> casual Latin-script Punjabi.
    """
    text = unicodedata.normalize("NFC", text)

    words = text.split(" ")
    latin = [_gm_word(word) for word in words]

    result = " ".join(latin)

    if result:
        return result[:1].upper() + result[1:]

    return result


# =============================================================================
# Devanagari -> casual Latin ("Hinglish")
# =============================================================================

_DV_NUKTA = "़"
_DV_HALANT = "्"
_DV_ANUSVARA = "ं"
_DV_CHANDRABINDU = "ँ"
_DV_NASAL_MARKS = (
    _DV_ANUSVARA,
    _DV_CHANDRABINDU,
)
_DV_VISARGA = "ः"
_DV_AVAGRAHA = "ऽ"

_DV_CONSONANTS = {
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "ng",

    "च": "ch",
    "छ": "chh",
    "ज": "j",
    "झ": "jh",
    "ञ": "ny",

    "ट": "t",
    "ठ": "th",
    "ड": "d",
    "ढ": "dh",
    "ण": "n",

    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",

    "प": "p",
    "फ": "ph",
    "ब": "b",
    "भ": "bh",
    "म": "m",

    "य": "y",
    "र": "r",
    "ल": "l",
    "ळ": "l",
    "व": "v",

    "श": "sh",
    "ष": "sh",
    "स": "s",
    "ह": "h",
}

_DV_NUKTA_VARIANTS = {
    "क": "q",
    "ख": "kh",
    "ग": "g",
    "ज": "z",
    "ड": "r",
    "ढ": "rh",
    "फ": "f",
    "य": "y",
}

_DV_INDEP_VOWELS = {
    "अ": "a",
    "आ": "aa",
    "इ": "i",
    "ई": "i",
    "उ": "u",
    "ऊ": "u",
    "ऋ": "ri",
    "ॠ": "rri",
    "ऌ": "lri",
    "ॡ": "lree",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
    "ऍ": "a",
    "ऑ": "o",
    "ॲ": "a",
    "ॅ": "a",
    "ॉ": "o",
}

_DV_MATRAS = {
    "ा": "aa",
    "ि": "i",
    "ी": "i",
    "ु": "u",
    "ू": "u",
    "ृ": "ri",
    "ॄ": "rree",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
    "ॅ": "a",
    "ॆ": "e",
    "ॉ": "o",
    "ॊ": "o",
}

_DV_IRREGULAR = {
    "गई": "gai",
    "गए": "gaye",
}


def _is_devanagari(text):
    return any("\u0900" <= ch <= "\u097F" for ch in text)


def _dv_tokenize(word):
    word = unicodedata.normalize("NFC", word)

    chars = list(word)
    n = len(chars)

    syllables = []
    i = 0

    while i < n:
        ch = chars[i]

        # Halant
        if ch == _DV_HALANT:
            i += 1
            continue

        # --------------------------------------------------------------
        # Consonant
        # --------------------------------------------------------------
        if ch in _DV_CONSONANTS:
            base = _DV_CONSONANTS[ch]

            if (
                i + 1 < n
                and chars[i + 1] == _DV_NUKTA
                and ch in _DV_NUKTA_VARIANTS
            ):
                base = _DV_NUKTA_VARIANTS[ch]
                i += 1

            vowel = "a"
            is_matra = False
            nasal = None

            j = i + 1

            if j < n and chars[j] in _DV_MATRAS:
                vowel = _DV_MATRAS[chars[j]]
                is_matra = True
                i = j

            elif j < n and chars[j] == _DV_HALANT:
                vowel = ""
                is_matra = True
                i = j

            k = i + 1

            # Nasal + matra
            if (
                k + 1 < n
                and chars[k] in _DV_NASAL_MARKS
                and chars[k + 1] in _DV_MATRAS
            ):
                nasal = chars[k]
                vowel = _DV_MATRAS[chars[k + 1]]
                is_matra = True
                i = k + 1

            # Nasal alone
            elif k < n and chars[k] in _DV_NASAL_MARKS:
                nasal = chars[k]
                i = k

            syllables.append(
                {
                    "base": base,
                    "vowel": vowel,
                    "is_matra": is_matra,
                    "nasal": nasal,
                    "indep": False,
                    "literal": None,
                }
            )

            i += 1
            continue

        # --------------------------------------------------------------
        # Independent vowel
        # --------------------------------------------------------------
        if ch in _DV_INDEP_VOWELS:
            vowel = _DV_INDEP_VOWELS[ch]
            nasal = None

            k = i + 1

            if k < n and chars[k] in _DV_NASAL_MARKS:
                nasal = chars[k]
                i = k

            syllables.append(
                {
                    "base": None,
                    "vowel": vowel,
                    "is_matra": False,
                    "nasal": nasal,
                    "indep": True,
                    "literal": None,
                }
            )

            i += 1
            continue

        # Visarga
        if ch == _DV_VISARGA:
            syllables.append(
                {
                    "base": None,
                    "vowel": None,
                    "is_matra": False,
                    "nasal": None,
                    "indep": False,
                    "literal": "h",
                }
            )
            i += 1
            continue

        # Avagraha
        if ch == _DV_AVAGRAHA:
            syllables.append(
                {
                    "base": None,
                    "vowel": None,
                    "is_matra": False,
                    "nasal": None,
                    "indep": False,
                    "literal": "'",
                }
            )
            i += 1
            continue

        # Standalone nasal
        if ch in _DV_NASAL_MARKS:
            syllables.append(
                {
                    "base": None,
                    "vowel": None,
                    "is_matra": False,
                    "nasal": None,
                    "indep": False,
                    "literal": "n",
                }
            )
            i += 1
            continue

        # Preserve punctuation / Latin text / unknown characters.
        syllables.append(
            {
                "base": None,
                "vowel": None,
                "is_matra": False,
                "nasal": None,
                "indep": False,
                "literal": ch,
            }
        )

        i += 1

    return syllables


def _dv_apply_rules(syllables):
    # ------------------------------------------------------------------
    # Nasalization
    # ------------------------------------------------------------------
    for idx, s in enumerate(syllables):
        if s["literal"] is not None or not s["nasal"]:
            continue

        nxt = (
            syllables[idx + 1]
            if idx + 1 < len(syllables)
            else None
        )

        if (
            nxt is not None
            and nxt["literal"] is None
            and nxt["base"] in _NASAL_BASES
        ):
            s["_append_n"] = False
        else:
            s["_append_n"] = True

    # ------------------------------------------------------------------
    # i + aa glide
    # ------------------------------------------------------------------
    for idx in range(1, len(syllables)):
        cur = syllables[idx]
        prev = syllables[idx - 1]

        if (
            cur["indep"]
            and cur["vowel"] == "aa"
            and prev["literal"] is None
            and prev["is_matra"]
            and prev["vowel"] == "i"
        ):
            cur["vowel"] = "ya"

    # ------------------------------------------------------------------
    # Final aa -> a
    # ------------------------------------------------------------------
    real = [s for s in syllables if s["literal"] is None]

    if real:
        last = real[-1]

        if (
            last["vowel"] == "aa"
            and not last["nasal"]
            and (
                last["is_matra"]
                or last["indep"]
            )
        ):
            last["vowel"] = "a"

    # ------------------------------------------------------------------
    # Final bare consonant drops schwa
    # ------------------------------------------------------------------
    if len(real) > 1:
        last = real[-1]

        if (
            not last["indep"]
            and not last["is_matra"]
            and last["vowel"] == "a"
            and not last["nasal"]
        ):
            last["vowel"] = ""

    return syllables


def _dv_word(word):
    word = unicodedata.normalize("NFC", word)

    if word in _DV_IRREGULAR:
        return _DV_IRREGULAR[word]

    return _render(
        _dv_apply_rules(
            _dv_tokenize(word)
        )
    )


def transliterate_devanagari(text):
    text = unicodedata.normalize("NFC", text)

    words = text.split(" ")
    latin = [_dv_word(word) for word in words]

    result = " ".join(latin)

    if result:
        return result[:1].upper() + result[1:]

    return result


def maybe_romanize(text, enabled):
    if not enabled:
        return text

    if _is_gurmukhi(text):
        return transliterate_gurmukhi(text)

    if _is_devanagari(text):
        return transliterate_devanagari(text)

    return text


# =============================================================================
# MPRIS / playerctl
# =============================================================================

def run(cmd):
    try:
        return subprocess.check_output(
            cmd,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        return ""


def get_player():
    players = run(["playerctl", "-l"]).splitlines()
    return players[0] if players else None


def get_metadata(player):
    fmt = "{{artist}}\t{{title}}\t{{album}}\t{{mpris:length}}"

    out = run(
        [
            "playerctl",
            "-p",
            player,
            "metadata",
            "--format",
            fmt,
        ]
    )

    if not out:
        return None

    parts = out.split("\t")

    if len(parts) < 4:
        return None

    artist, title, album, length_us = parts

    try:
        duration = int(length_us) / 1_000_000
    except (ValueError, TypeError):
        duration = 0.0

    if not artist or not title:
        return None

    return {
        "artist": artist,
        "title": title,
        "album": album,
        "duration": duration,
    }


def get_position(player):
    pos = run(
        [
            "playerctl",
            "-p",
            player,
            "position",
        ]
    )

    try:
        return float(pos)
    except ValueError:
        return 0.0


def get_status(player):
    return run(
        [
            "playerctl",
            "-p",
            player,
            "status",
        ]
    )


# =============================================================================
# Cache
# =============================================================================

def cache_key(meta):
    raw = (
        f"{meta['artist']}|"
        f"{meta['title']}|"
        f"{meta['album']}"
    )

    return hashlib.sha1(
        raw.encode("utf-8")
    ).hexdigest()


def load_cached(meta):
    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = CACHE_DIR / f"{cache_key(meta)}.lrc"

    if not path.exists():
        return None

    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return None


def save_cached(meta, text):
    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = CACHE_DIR / f"{cache_key(meta)}.lrc"

    try:
        path.write_text(
            text,
            encoding="utf-8",
        )
    except OSError:
        pass


# =============================================================================
# Lyric backends
# =============================================================================

def try_local(meta, local_dir):
    """
    Look for:
        Artist - Title.lrc
        Title.lrc

    Then recursively search for a filename containing both artist and title.
    """
    local_dir = Path(local_dir).expanduser()

    if not local_dir.is_dir():
        return None

    artist = meta["artist"]
    title = meta["title"]

    for candidate in (
        f"{artist} - {title}.lrc",
        f"{title}.lrc",
    ):
        path = local_dir / candidate

        if path.exists():
            try:
                return path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            except OSError:
                pass

    artist_l = artist.lower()
    title_l = title.lower()

    try:
        candidates = local_dir.rglob("*.lrc")
    except OSError:
        return None

    for path in candidates:
        try:
            name = path.stem.lower()

            if title_l in name and (
                artist_l in name
                or not artist_l
            ):
                return path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
        except OSError:
            continue

    return None


def try_lrclib(meta):
    """
    Try the direct LRCLIB endpoint first.
    Then fall back to search.
    """
    params = {
        "track_name": meta["title"],
        "artist_name": meta["artist"],
    }

    if meta["album"]:
        params["album_name"] = meta["album"]

    if meta["duration"] > 0:
        params["duration"] = round(
            meta["duration"]
        )

    # Direct lookup
    try:
        response = requests.get(
            LRCLIB_GET,
            params=params,
            timeout=8,
        )

        if response.status_code == 200:
            data = response.json()

            synced = data.get(
                "syncedLyrics"
            )

            if synced:
                return synced

    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ):
        pass

    # Search fallback
    try:
        response = requests.get(
            LRCLIB_SEARCH,
            params={
                "track_name": meta["title"],
                "artist_name": meta["artist"],
            },
            timeout=8,
        )

        if response.status_code == 200:
            results = response.json()

            if isinstance(results, list):
                for result in results:
                    synced = result.get(
                        "syncedLyrics"
                    )

                    if synced:
                        return synced

    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ):
        pass

    return None


def try_lrcmux(meta):
    params = {
        "artist": meta["artist"],
        "title": meta["title"],
        "format": "lrc",
        "level": "line",
        "sources": "!netease",
    }

    if meta["album"]:
        params["album"] = meta["album"]

    if meta["duration"] > 0:
        params["duration"] = round(
            meta["duration"]
        )

    try:
        response = requests.get(
            LRCMUX_GET,
            params=params,
            headers=LRCMUX_HEADERS,
            timeout=8,
        )

        if (
            response.status_code == 200
            and response.text.strip()
        ):
            return response.text

    except requests.RequestException:
        pass

    return None


BACKEND_FUNCS = {
    "local": lambda meta, args: try_local(
        meta,
        args.local_dir,
    ),

    "lrclib": lambda meta, args: try_lrclib(
        meta
    ),

    "lrcmux": lambda meta, args: try_lrcmux(
        meta
    ),
}


def get_lyrics_for_track(meta, args):
    """
    Return:
        (lyrics_text, source)

    Cached lyrics are the ORIGINAL/raw LRC returned by the backend.
    Romanization happens later during parse_lrc().
    """
    cached = load_cached(meta)

    if cached is not None:
        return cached, "cache"

    for backend_name in args.backend_order:
        func = BACKEND_FUNCS.get(
            backend_name
        )

        if func is None:
            continue

        try:
            lrc = func(
                meta,
                args,
            )
        except Exception:
            lrc = None

        if lrc:
            save_cached(
                meta,
                lrc,
            )

            return lrc, backend_name

    return None, None


# =============================================================================
# LRC parsing
# =============================================================================

def parse_lrc(text, romanize):
    """
    Parse timestamped LRC lines.
    """
    lines = []

    if not text:
        return lines

    for raw_line in text.splitlines():
        match = LRC_LINE_RE.match(
            raw_line
        )

        if not match:
            continue

        minutes, seconds, content = match.groups()

        try:
            timestamp = (
                int(minutes) * 60
                + float(seconds)
            )
        except ValueError:
            continue

        content = content.strip()

        content = maybe_romanize(
            content,
            romanize,
        )

        lines.append(
            (
                timestamp,
                content,
            )
        )

    lines.sort(
        key=lambda item: item[0]
    )

    return lines


def current_line_index(lines, position):
    index = -1

    for i, (timestamp, _) in enumerate(lines):
        if timestamp <= position:
            index = i
        else:
            break

    return index


def format_time(seconds):
    minutes, seconds = divmod(
        int(seconds),
        60,
    )

    return f"{minutes:02d}:{seconds:02d}"


# =============================================================================
# Notifications
# =============================================================================

def notify(title, body):
    run(
        [
            "notify-send",
            "-a",
            "sync-lyrics",
            "-u",
            "critical",
            "-r",
            "9271",
            "-t",
            "0",
            title,
            body,
        ]
    )


# =============================================================================
# Watch mode
# =============================================================================

def watch(player, args):
    last_key = None
    lines = []
    printed_idx = -1

    while True:
        status = get_status(player)
        meta = get_metadata(player)

        if not meta:
            time.sleep(
                POLL_INTERVAL
            )
            continue

        key = cache_key(meta)

        # --------------------------------------------------------------
        # New track
        # --------------------------------------------------------------
        if key != last_key:
            last_key = key
            printed_idx = -1

            if not args.json:
                print(
                    f"\n♪ {meta['artist']} — {meta['title']}",
                    file=sys.stderr,
                )

            lrc_text, source = (
                get_lyrics_for_track(
                    meta,
                    args,
                )
            )

            if not lrc_text:
                lines = []

                if not args.json:
                    print(
                        "  (no synced lyrics found in any backend)",
                        file=sys.stderr,
                    )

            else:
                lines = parse_lrc(
                    lrc_text,
                    not args.no_romanize,
                )

                if not args.json:
                    print(
                        f"  (source: {source})",
                        file=sys.stderr,
                    )

                else:
                    print(
                        json.dumps(
                            {
                                "event": "track_start",
                                "metadata": meta,
                                "source": source,
                                "total_lines": len(lines),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )

        # --------------------------------------------------------------
        # Not playing / no lyrics
        # --------------------------------------------------------------
        if (
            status != "Playing"
            or not lines
        ):
            time.sleep(
                POLL_INTERVAL
            )
            continue

        position = get_position(
            player
        )

        index = current_line_index(
            lines,
            position,
        )

        if (
            index != printed_idx
            and index >= 0
        ):
            printed_idx = index

            text = (
                lines[index][1]
                or "♪"
            )

            if args.json:
                print(
                    json.dumps(
                        {
                            "event": "lyric",
                            "time": lines[index][0],
                            "formatted_time": format_time(
                                lines[index][0]
                            ),
                            "text": text,
                            "index": index,
                            "artist": meta["artist"],
                            "title": meta["title"],
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

            elif args.notify:
                notify(
                    (
                        f"{meta['artist']} — "
                        f"{meta['title']}"
                    ),
                    text,
                )

            else:
                print(
                    f"\r\033[K{text}",
                    end="",
                    flush=True,
                )

        time.sleep(
            POLL_INTERVAL
        )


# =============================================================================
# --once mode
# =============================================================================

def once(player, args):
    meta = get_metadata(player)

    if not meta:
        if args.json:
            print(
                json.dumps(
                    {
                        "error": (
                            "No track currently playing"
                        )
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(
                "No track currently playing.",
                file=sys.stderr,
            )

        sys.exit(1)

    lrc_text, source = (
        get_lyrics_for_track(
            meta,
            args,
        )
    )

    if not lrc_text:
        if args.json:
            print(
                json.dumps(
                    {
                        "error": (
                            "No synced lyrics found"
                        ),
                        "metadata": meta,
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(
                "No synced lyrics found in any "
                "backend for this track."
            )

        sys.exit(1)

    lines = parse_lrc(
        lrc_text,
        not args.no_romanize,
    )

    if args.json:
        output = {
            "metadata": meta,
            "source": source,
            "lyrics": [
                {
                    "time": timestamp,
                    "formatted_time": format_time(
                        timestamp
                    ),
                    "text": text,
                }
                for timestamp, text in lines
            ],
        }

        print(
            json.dumps(
                output,
                indent=2,
                ensure_ascii=False,
            )
        )

    else:
        print(
            f"{meta['artist']} — {meta['title']}\n"
        )

        print(
            f"(source: {source})\n"
        )

        for timestamp, text in lines:
            print(
                f"[{format_time(timestamp)}] {text}"
            )


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Show synced lyrics for the currently "
            "playing track."
        )
    )

    parser.add_argument(
        "--notify",
        action="store_true",
        help=(
            "send lines as desktop notifications "
            "instead of printing"
        ),
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help=(
            "print the full synced lyric sheet "
            "and exit"
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "output as JSON "
            "(JSONL in watch mode, "
            "one object in --once)"
        ),
    )

    parser.add_argument(
        "--player",
        help=(
            "MPRIS player name "
            "(defaults to the first one playerctl finds)"
        ),
    )

    parser.add_argument(
        "--backends",
        default="local,lrclib,lrcmux",
        help=(
            "comma-separated backend order: "
            "local,lrclib,lrcmux"
        ),
    )

    parser.add_argument(
        "--local-dir",
        default=str(
            DEFAULT_LOCAL_DIR
        ),
        help=(
            "directory containing local .lrc files "
            f"(default: {DEFAULT_LOCAL_DIR})"
        ),
    )

    parser.add_argument(
        "--no-romanize",
        action="store_true",
        help=(
            "keep Gurmukhi/Devanagari lyrics "
            "in their original script"
        ),
    )

    args = parser.parse_args()

    args.backend_order = [
        backend.strip()
        for backend in args.backends.split(",")
        if backend.strip()
    ]

    player = (
        args.player
        or get_player()
    )

    if not player:
        if args.json:
            print(
                json.dumps(
                    {
                        "error": (
                            "No MPRIS-capable player found"
                        )
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(
                "No MPRIS-capable player found. "
                "Is anything playing?",
                file=sys.stderr,
            )

        sys.exit(1)

    if args.once:
        once(
            player,
            args,
        )
    else:
        try:
            watch(
                player,
                args,
            )
        except KeyboardInterrupt:
            if args.json:
                try:
                    print(
                        json.dumps(
                            {
                                "event": "stopped"
                            },
                            ensure_ascii=False,
                        )
                    )
                except BrokenPipeError:
                    pass


if __name__ == "__main__":
    main()
