#!/usr/bin/env python3
"""lyricsync — CLI lyrics synchronization tool.

Fetches synchronized lyrics from LRCLIB and LRCMɨX (lrcmux.dev),
transliterates Gurmukhi/Devanagari to casual Latin, and displays
them in sync with the currently playing song.
"""

from __future__ import annotations

import argparse
import bisect
import curses
import json
import os
import re
import shutil
import subprocess
import sys
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
    def duration_ms(self) -> int:
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

@dataclass
class IndicMaps:
    consonants: dict[str, str]
    vowels: dict[str, str]
    matras: dict[str, str]
    signs: dict[str, str]
    halant: str
    consonant_chars: set[str] = field(default_factory=set)
    multi_consonants: dict[str, str] = field(default_factory=dict)
    vowel_signs: tuple[str, ...] = ()
    script_range: tuple[str, str] = ("", "")
    multi_consonants: dict[str, str] = field(default_factory=dict)
    vowel_signs: tuple[str, ...] = ()
    script_range: tuple[str, str] = ("", "")


def _next_is_vowel(text: str, pos: int, maps: IndicMaps) -> bool:
    if pos >= len(text):
        return False
    ch = text[pos]
    return (ch in maps.matras or ch in maps.vowels
            or ch == maps.halant or ch in maps.vowel_signs)


def transliterate_indic(text: str, maps: IndicMaps) -> str:
    lo, hi = maps.script_range
    if not any(lo <= c <= hi for c in text):
        return text
    result: list[str] = []
    i = 0
    while i < len(text):
        two = text[i:i + 2]
        if two in maps.multi_consonants:
            result.append(maps.multi_consonants[two])
            nxt = i + 2
            if not (nxt < len(text) and text[nxt] == maps.halant) \
                    and not _next_is_vowel(text, nxt, maps):
                result.append("a")
            i += 2
            continue
        ch = text[i]
        if ch == maps.halant:
            if i + 1 < len(text) and text[i + 1] in maps.consonant_chars:
                result.append(maps.consonants[text[i + 1]])
                i += 2
                continue
            i += 1
            continue
        if ch in maps.consonant_chars:
            result.append(maps.consonants[ch])
            nxt = i + 1
            if not (nxt < len(text) and text[nxt] == maps.halant) \
                    and not _next_is_vowel(text, nxt, maps):
                result.append("a")
            i += 1
            continue
        if ch in maps.matras:
            result.append(maps.matras[ch]); i += 1; continue
        if ch in maps.vowels:
            result.append(maps.vowels[ch]); i += 1; continue
        if ch in maps.signs:
            result.append(maps.signs[ch]); i += 1; continue
        result.append(ch); i += 1
    return "".join(result)


_DV_MAPS = IndicMaps(
    consonants={
        "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
        "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
        "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
        "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
        "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
        "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
        "ष": "sh", "स": "s", "ह": "h",
    },
    vowels={
        "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
        "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऋ": "ri", "ॐ": "om",
    },
    matras={
        "ा": "a", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo",
        "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ृ": "ri",
    },
    signs={
        "ं": "n", "ँ": "n", "ः": "h", "ॅ": "e", "ॉ": "o", "ॊ": "o",
        "॥": "", "।": "",
    },
    halant="्",
    vowel_signs=("ं", "ँ"),
    script_range=("\u0900", "\u097F"),
)
_DV_MAPS.consonant_chars = set(_DV_MAPS.consonants.keys())

_GG_MAPS = IndicMaps(
    consonants={
        "ਕ": "k", "ਖ": "kh", "ਗ": "g", "ਘ": "gh", "ਙ": "ng",
        "ਚ": "ch", "ਛ": "chh", "ਜ": "j", "ਝ": "jh", "ਞ": "ny",
        "ਟ": "t", "ਠ": "th", "ਡ": "d", "ਢ": "dh", "ਣ": "n",
        "ਤ": "t", "ਥ": "th", "ਦ": "d", "ਧ": "dh", "ਨ": "n",
        "ਪ": "p", "ਫ": "ph", "ਬ": "b", "ਭ": "bh", "ਮ": "m",
        "ਯ": "y", "ਰ": "r", "ਲ": "l", "ਵ": "v",
        "ਸ": "s", "ਹ": "h", "ੜ": "r",
    },
    vowels={
        "ਅ": "a", "ਆ": "aa", "ਇ": "i", "ਈ": "ee", "ਉ": "u", "ਊ": "oo",
        "ਏ": "e", "ਐ": "ai", "ਓ": "o", "ਔ": "au", "ੴ": "ek onkar",
    },
    matras={
        "ਾ": "a", "ਿ": "i", "ੀ": "ee", "ੁ": "u", "ੂ": "oo",
        "ੇ": "e", "ੈ": "ai", "ੋ": "o", "ੌ": "au",
    },
    signs={"ਂ": "n", "ਃ": "h", "ੰ": "m", "ੱ": "", "॥": "", "।": ""},
    halant="੍",
    consonant_chars=set("ਕਖਗਘਙਚਛਜਝਞਟਠਡਢਣਤਥਦਧਨਪਫਬਭਮਯਰਲਵਸਹੜ"),
    multi_consonants={
        "ਸ਼": "sh", "ਖ਼": "kh", "ਗ਼": "gh", "ਜ਼": "z", "ਫ਼": "f",
        "ਲ਼": "l",
    },
    vowel_signs=("ਂ", "ੰ"),
    script_range=("\u0A00", "\u0A7F"),
)


def transliterate_devanagari(text: str) -> str:
    """Casual Hinglish transliteration of Devanagari text."""
    return transliterate_indic(text, _DV_MAPS)


def transliterate_gurmukhi(text: str) -> str:
    """Casual Punglish transliteration of Gurmukhi text."""
    return transliterate_indic(text, _GG_MAPS)


# --- detection & dispatch ---

def detect_script(text: str) -> str:
    dv = gg = 0
    for ch in text:
        if "\u0900" <= ch <= "\u097F":
            dv += 1
        elif "\u0A00" <= ch <= "\u0A7F":
            gg += 1
    if dv == 0 and gg == 0:
        return "latin"
    if gg > dv:
        return "gurmukhi"
    return "devanagari"


def transliterate(text: str, force_mode: str | None = None) -> tuple[str, str]:
    """Returns (transliterated_text, mode_name)."""
    if force_mode == "devanagari":
        return transliterate_devanagari(text), "hinglish"
    if force_mode == "gurmukhi":
        return transliterate_gurmukhi(text), "punglish"
    script = detect_script(text)
    if script == "devanagari":
        return transliterate_devanagari(text), "hinglish"
    if script == "gurmukhi":
        return transliterate_gurmukhi(text), "punglish"
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
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    last_err: Exception | None = None
    for attempt in range(1 + retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                json.JSONDecodeError) as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    return None


class LyricsProvider(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, artist: str, title: str, album: str = "",
              duration_s: float = 0) -> SyncedLyrics | None:
        ...


class LRCLIBProvider(LyricsProvider):
    name = "lrclib"
    BASE = "https://lrclib.net/api"

    def _parse_result(self, data: dict, title: str, artist: str,
                      album: str) -> SyncedLyrics | None:
        if not data or not isinstance(data, dict):
            return None
        synced = data.get("syncedLyrics")
        if synced:
            lyrics = parse_lrc(synced)
            lyrics.title = data.get("trackName", title)
            lyrics.artist = data.get("artistName", artist)
            lyrics.album = data.get("albumName", album)
            lyrics.source = "lrclib"
            return lyrics
        plain = data.get("plainLyrics")
        if plain:
            return parse_plain_lyrics(
                plain,
                title=data.get("trackName", title),
                artist=data.get("artistName", artist),
                album=data.get("albumName", album),
                source="lrclib",
            )
        return None

    def fetch(self, artist: str, title: str, album: str = "",
              duration_s: float = 0) -> SyncedLyrics | None:
        params: dict[str, str | float] = {
            "artist_name": artist, "track_name": title,
        }
        url = f"{self.BASE}/get?{urllib.parse.urlencode(params)}"
        data = _http_get_json(url)
        get_result = self._parse_result(data, title, artist, album)
        if get_result and get_result.synced:
            return get_result
        search_q = f"{artist} {title}"
        search_url = f"{self.BASE}/search?q={urllib.parse.quote(search_q)}"
        results = _http_get_json(search_url)
        search_result = None
        if results and isinstance(results, list):
            title_lower = title.lower()
            artist_lower = artist.lower()
            synced_exact = None
            synced_partial = None
            plain_exact = None
            plain_partial = None
            for item in results:
                if not isinstance(item, dict):
                    continue
                item_title = (item.get("trackName") or item.get("name", "")).lower()
                item_artist = item.get("artistName", "").lower()
                is_synced = item.get("syncedLyrics") is not None
                title_match = item_title == title_lower
                artist_match = artist_lower in item_artist or item_artist in artist_lower
                if not title_match:
                    title_match = title_lower in item_title or item_title in title_lower
                if not title_match:
                    continue
                if is_synced and artist_match and synced_exact is None:
                    synced_exact = item
                elif is_synced and synced_partial is None:
                    synced_partial = item
                elif not is_synced and artist_match and plain_exact is None:
                    plain_exact = item
                elif not is_synced and plain_partial is None:
                    plain_partial = item
            best = (synced_exact or synced_partial
                    or plain_exact or plain_partial)
            if best is None and results:
                for item in results:
                    if isinstance(item, dict) and item.get("syncedLyrics"):
                        best = item
                        break
                if best is None:
                    best = results[0]
            search_result = self._parse_result(best, title, artist, album) \
                if best else None
        if search_result and search_result.synced:
            return search_result
        if get_result:
            return get_result
        return search_result


class LRCMIXProvider(LyricsProvider):
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


ALL_PROVIDERS: list[LyricsProvider] = [LRCLIBProvider(), LRCMIXProvider()]


def fetch_lyrics(artist: str, title: str, album: str = "",
                 duration_s: float = 0,
                 providers: list[LyricsProvider] | None = None,
                 ) -> SyncedLyrics | None:
    """Try providers in order; prefer synced, fall back to plain."""
    provs = providers or ALL_PROVIDERS
    best: SyncedLyrics | None = None
    for p in provs:
        try:
            result = p.fetch(artist, title, album, duration_s)
        except Exception as exc:
            print(f"[{p.name}] fetch error: {exc}", file=sys.stderr)
            continue
        if result is None:
            continue
        if result.synced:
            return result
        if best is None:
            best = result
    return best


# ──────────────────────────── players ────────────────────────────────

class Player(ABC):
    name: str = "base"

    @abstractmethod
    def detect(self) -> bool: ...

    @abstractmethod
    def get_playback(self) -> PlaybackInfo | None: ...

    @abstractmethod
    def list_songs(self) -> list[dict] | None: ...

    def seek(self, position_ms: int) -> bool:
        return False


class MPRISPlayer(Player):
    """Linux MPRIS/D-Bus players via playerctl."""
    name = "mpris"

    def __init__(self, player_name: str | None = None):
        self.player_name = player_name

    def detect(self) -> bool:
        return shutil.which("playerctl") is not None

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

    def list_songs(self) -> list[dict] | None:
        raw = self._run("metadata")
        if not raw:
            return None
        by_player: dict[str, dict] = {}
        for line in raw.splitlines():
            parts = line.split(None, 2)
            if len(parts) < 3:
                continue
            pname, key, val = parts[0], parts[1], parts[2]
            if pname not in by_player:
                by_player[pname] = {}
            by_player[pname][key] = val
        songs = []
        for pdata in by_player.values():
            t = pdata.get("xesam:title", "")
            if t:
                songs.append({"title": t,
                              "artist": pdata.get("xesam:artist", ""),
                              "album": pdata.get("xesam:album", "")})
        return songs or None

    def seek(self, position_ms: int) -> bool:
        pos_s = position_ms / 1000
        result = self._run("position", str(pos_s))
        return result is not None


class MPDPlayer(Player):
    """Music Player Daemon via mpc."""
    name = "mpd"

    def detect(self) -> bool:
        return shutil.which("mpc") is not None

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
        status_low = status.lower()
        current = self._mpc("current")
        if not current or ("[playing]" not in status_low
                           and "[paused]" not in status_low):
            return None
        lines = current.strip().splitlines()
        title = artist = album = ""
        if lines:
            parts = lines[0].split(" - ", 1)
            title = parts[0].strip()
            artist = parts[1].strip() if len(parts) > 1 else ""
        playing = "[playing]" in status_low
        elapsed_ms = dur_ms = 0
        for line in status.splitlines():
            if line.lower().strip().startswith("time:"):
                t = line.split(":", 1)[1].strip()
                if "/" in t:
                    pos_s, dur_s = t.split("/", 1)
                    elapsed_ms = int(float(pos_s) * 1000)
                    dur_ms = int(float(dur_s) * 1000)
        meta = self._mpc("current", "--format", "%artist%\n%album%")
        if meta:
            mlines = meta.strip().splitlines()
            if mlines:
                artist = artist or mlines[0].strip()
            if len(mlines) > 1:
                album = mlines[1].strip()
        return PlaybackInfo(
            title=title, artist=artist, album=album,
            duration_ms=dur_ms, position_ms=elapsed_ms,
            playing=playing, player="mpd",
        )

    def list_songs(self) -> list[dict] | None:
        return None

    def seek(self, position_ms: int) -> bool:
        pos_s = position_ms / 1000
        result = self._mpc("seek", str(pos_s))
        return result is not None


class CMUSPlayer(Player):
    """cmus via cmus-remote."""
    name = "cmus"

    def detect(self) -> bool:
        return shutil.which("cmus-remote") is not None

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
            for key in ("title", "artist", "album", "duration", "position"):
                if line.startswith(f"tag {key} "):
                    info[key] = line[len(f"tag {key} "):]
                elif line.startswith(f"set {key} "):
                    info[key] = line[len(f"set {key} "):]
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

    def list_songs(self) -> list[dict] | None:
        return None

    def seek(self, position_ms: int) -> bool:
        pos_s = position_ms / 1000
        result = subprocess.run(["cmus-remote", "-C",
                                 f"seek {pos_s}s"],
                                capture_output=True, timeout=5)
        return result.returncode == 0


ALL_PLAYERS: list[Player] = [MPRISPlayer(), MPDPlayer(), CMUSPlayer()]


def detect_player(name: str | None = None) -> Player | None:
    if name:
        for p in ALL_PLAYERS:
            if p.name == name:
                return p if p.detect() else None
        for p in ALL_PLAYERS:
            if name.lower() in p.name.lower():
                return p if p.detect() else None
        return None
    for p in ALL_PLAYERS:
        if p.detect():
            return p
    return None


def interactive_player_select() -> Player | None:
    available = [p for p in ALL_PLAYERS if p.detect()]
    if not available:
        return None
    if len(available) == 1:
        return available[0]
    print("Available players:", file=sys.stderr)
    for i, p in enumerate(available, 1):
        print(f"  {i}. {p.name}", file=sys.stderr)
    try:
        choice = input("Select player [1]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    idx = int(choice) - 1 if choice else 0
    if 0 <= idx < len(available):
        return available[idx]
    return None


# ──────────────────────────── sync engine ────────────────────────────

def find_current_line(lines: list[LyricLine], position_ms: int) -> int:
    """Return the index of the line currently playing."""
    if not lines:
        return -1
    timestamps = [l.time_ms for l in lines]
    idx = bisect.bisect_right(timestamps, position_ms) - 1
    return idx if idx >= 0 else -1


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
    changed = key != last_key and (info.title or info.artist)
    new_last = key if changed else last_key
    return info, changed, new_last


def _fetch_for_player(
    player: Player,
    providers: list[LyricsProvider],
    translit_mode: str | None,
) -> SyncedLyrics | None:
    """Fetch lyrics for whatever the player is currently playing."""
    info = player.get_playback()
    if info is None:
        return None
    dur_s = info.duration_ms / 1000
    lyrics = fetch_lyrics(info.artist, info.title, info.album,
                          dur_s, providers)
    if lyrics is not None:
        lyrics, _ = transliterate_lyrics(lyrics, translit_mode)
    return lyrics


class _PlaybackPoller:
    """Shared state for live playback output modes."""

    def __init__(self, player: Player, initial_lyrics: SyncedLyrics | None,
                 translit_mode: str | None,
                 providers: list[LyricsProvider] | None = None):
        self.player = player
        self.translit_mode = translit_mode
        self.providers = providers or ALL_PROVIDERS
        self.lyrics = initial_lyrics
        self.last_key: tuple[str, str] = ("", "")
        if initial_lyrics and initial_lyrics.lines:
            self.last_key = _song_key(PlaybackInfo(
                title=initial_lyrics.title, artist=initial_lyrics.artist))

    def poll(self) -> tuple[PlaybackInfo | None, bool]:
        """Check for song changes, fetch if needed. Returns (info, changed)."""
        info, changed, self.last_key = _check_song_change(
            self.player, self.last_key)
        if changed and info:
            self.lyrics = _fetch_for_player(
                self.player, self.providers, self.translit_mode)
        return info, changed

    def current_line(self, position_ms: int) -> LyricLine | None:
        if not self.lyrics or not self.lyrics.lines:
            return None
        idx = find_current_line(self.lyrics.lines, position_ms)
        return self.lyrics.lines[idx] if idx >= 0 else None


# ──────────────────────────── output: plain ──────────────────────────

def output_plain(lyrics: SyncedLyrics | None, player: Player,
                 translit_mode: str | None = None,
                 providers: list[LyricsProvider] | None = None) -> None:
    if lyrics is not None:
        lyrics, _ = transliterate_lyrics(lyrics, translit_mode)
    poller = _PlaybackPoller(player, lyrics, translit_mode, providers)
    was_playing = False
    try:
        while True:
            info, changed = poller.poll()
            if changed:
                if info:
                    print(f"\nFetching lyrics for: {info.artist} — {info.title}",
                          file=sys.stderr)
                continue
            if info is None:
                print("No playback detected. Waiting...", file=sys.stderr)
                time.sleep(2)
                continue
            if not info.playing:
                was_playing = True
                print(f"Paused: {info.artist} - {info.title}", file=sys.stderr)
                time.sleep(1)
                continue
            was_playing = True
            line = poller.current_line(info.position_ms)
            if line is None:
                time.sleep(0.5 if not poller.lyrics else 0.3)
                continue
            text = line.text.strip() or "♪"
            sys.stdout.write(f"\r\033[2K\033[1m{text}\033[0m")
            sys.stdout.flush()
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass


# ──────────────────────────── output: once ───────────────────────────

def output_once(lyrics: SyncedLyrics, translit_mode: str | None = None) -> None:
    lyrics, _ = transliterate_lyrics(lyrics, translit_mode)
    for line in lyrics.lines:
        mm = line.time_ms // 60000
        ss = (line.time_ms % 60000) // 1000
        cs = (line.time_ms % 1000) // 10
        text = line.text.strip() or "♪"
        print(f"[{mm:02d}:{ss:02d}.{cs:02d}] {text}")


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

def output_tui(lyrics: SyncedLyrics | None, player: Player,
               translit_mode: str | None = None,
               providers: list[LyricsProvider] | None = None) -> None:
    if lyrics is not None:
        lyrics, _ = transliterate_lyrics(lyrics, translit_mode)
    poller = _PlaybackPoller(player, lyrics, translit_mode, providers)

    def draw(stdscr: "curses.window") -> None:
        curses.curs_set(0)
        curses.use_default_colors()
        if curses.can_change_color():
            try:
                curses.init_pair(1, curses.COLOR_WHITE, -1)
                curses.init_pair(2, curses.COLOR_YELLOW, -1)
                curses.init_pair(3, curses.COLOR_CYAN, -1)
                curses.init_pair(4, curses.COLOR_GREEN, -1)
                curses.init_pair(5, curses.COLOR_MAGENTA, -1)
                curses.init_pair(6,  252, -1)
                curses.init_pair(7,  247, -1)
                curses.init_pair(8,  242, -1)
                curses.init_pair(9,  238, -1)
                curses.init_pair(10, 235, -1)
                curses.init_pair(11, 233, -1)
            except curses.error:
                pass

        sel_idx = -1
        _GRADIENT = [6, 7, 8, 9, 10, 11]

        def line_color(dist: int) -> int:
            idx = min(dist - 1, len(_GRADIENT) - 1)
            return curses.color_pair(_GRADIENT[max(0, idx)])

        def _draw_header(stdscr: "curses.window", info: PlaybackInfo,
                         lyrics: SyncedLyrics | None, h: int, w: int) -> None:
            if info is None:
                return
            dur = (lyrics.duration_ms if lyrics and lyrics.duration_ms > 0
                   else info.duration_ms)
            mm_now = info.position_ms // 60000
            ss_now = (info.position_ms % 60000) // 1000
            mm_dur = dur // 60000
            ss_dur = (dur % 60000) // 1000
            header = (f" {info.artist} - {info.title}  "
                      f"[{mm_now:02d}:{ss_now:02d} / {mm_dur:02d}:{ss_dur:02d}] ")
            if len(header) > w - 1:
                header = header[: w - 4] + "..."
            try:
                stdscr.addstr(0, max(0, (w - len(header)) // 2),
                              header, curses.color_pair(2))
            except curses.error:
                pass

        def _draw_footer(stdscr: "curses.window", lyrics: SyncedLyrics | None,
                         h: int, w: int) -> None:
            if lyrics is None:
                return
            footer = f" source:{lyrics.source} "
            try:
                stdscr.addstr(h - 1, max(0, w - len(footer) - 1),
                              footer, curses.color_pair(2))
            except curses.error:
                pass

        def draw_lyrics(stdscr: "curses.window", lyr: SyncedLyrics,
                        info: PlaybackInfo, sel: int) -> None:
            nonlocal sel_idx
            h, w = stdscr.getmaxyx()
            lyrics_h = h - 2
            playing_idx = find_current_line(lyr.lines, info.position_ms)
            if sel < 0:
                sel_idx = playing_idx
                sel = sel_idx
            center = lyrics_h // 2

            for row in range(lyrics_h):
                line_idx = playing_idx + (row - center)
                y = row + 1
                if 0 <= line_idx < len(lyr.lines):
                    text = lyr.lines[line_idx].text.strip() or "♪"
                    is_playing = (line_idx == playing_idx)
                    is_selected = (line_idx == sel)
                    dist = abs(line_idx - playing_idx)
                    prefix_w = 2 if is_selected else 0
                    max_text = w - 1 - prefix_w - 3
                    if len(text) > max_text:
                        display = text[:max_text] + "..."
                    else:
                        display = text
                    if is_selected:
                        display = "▸ " + display
                    try:
                        if is_selected and is_playing:
                            attr = (curses.A_BOLD | curses.A_UNDERLINE
                                    | curses.color_pair(5))
                        elif is_selected:
                            attr = curses.A_BOLD | curses.color_pair(5)
                        elif is_playing:
                            attr = curses.A_BOLD | curses.A_UNDERLINE
                        else:
                            attr = line_color(dist)
                        stdscr.addstr(
                            y, max(0, (w - len(display)) // 2),
                            display, attr)
                    except curses.error:
                        pass

        while True:
            info, changed = poller.poll()
            if changed:
                sel_idx = -1
                stdscr.erase()
                h, w = stdscr.getmaxyx()
                _draw_header(stdscr, info, poller.lyrics, h, w)
                _draw_footer(stdscr, poller.lyrics, h, w)
                msg = f"Fetching lyrics for: {info.artist} — {info.title}"
                try:
                    stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2), msg)
                except curses.error:
                    pass
                stdscr.refresh()
                continue
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            _draw_header(stdscr, info, poller.lyrics, h, w)
            _draw_footer(stdscr, poller.lyrics, h, w)
            if info is None or not info.playing:
                msg = "Waiting for playback..."
                if info and not info.playing:
                    msg = f"Paused: {info.artist} - {info.title}"
                try:
                    stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2), msg)
                except curses.error:
                    pass
                stdscr.refresh()
                time.sleep(0.5)
                continue
            lyr = poller.lyrics
            if lyr is None or not lyr.lines:
                msg = "No lyrics"
                try:
                    stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2), msg)
                except curses.error:
                    pass
                stdscr.refresh()
                time.sleep(0.5)
                continue
            draw_lyrics(stdscr, lyr, info, sel_idx)
            stdscr.refresh()
            h, w = stdscr.getmaxyx()
            lyrics_h = h - 2
            playing_idx = find_current_line(lyr.lines, info.position_ms)
            stdscr.timeout(150)
            key = stdscr.getch()
            if key == ord('q'):
                break
            elif key == curses.KEY_UP:
                vis_lo = max(0, playing_idx - (lyrics_h // 2))
                vis_hi = min(len(lyr.lines) - 1,
                             playing_idx + (lyrics_h // 2))
                sel_idx = max(vis_lo, sel_idx - 1)
            elif key == curses.KEY_DOWN:
                vis_lo = max(0, playing_idx - (lyrics_h // 2))
                vis_hi = min(len(lyr.lines) - 1,
                             playing_idx + (lyrics_h // 2))
                sel_idx = min(vis_hi, sel_idx + 1)
            elif key in (10, 13, curses.KEY_ENTER):
                if 0 <= sel_idx < len(lyr.lines):
                    player.seek(lyr.lines[sel_idx].time_ms)
                    sel_idx = -1
            elif key == curses.KEY_RESIZE:
                pass

    try:
        curses.wrapper(draw)
    except KeyboardInterrupt:
        pass


# ──────────────────────────── output: notify ─────────────────────────

_NOTIFY_CMD = shutil.which("notify-send")


def notify(line: str, _last_id: list[str] | None = None) -> None:
    """Send or replace a desktop notification."""
    if not _NOTIFY_CMD:
        return
    if _last_id is None:
        _last_id = []
    try:
        if _last_id:
            subprocess.run(
                [_NOTIFY_CMD, "--replace-id=" + _last_id[0],
                 "--hint=int:transient:1",
                 "-a", "lyricsync", "lyricsync", line],
                timeout=2, capture_output=True,
            )
        else:
            r = subprocess.run(
                [_NOTIFY_CMD, "--print-id",
                 "--hint=int:transient:1",
                 "-a", "lyricsync", "lyricsync", line],
                capture_output=True, text=True, timeout=2,
            )
            if r.stdout.strip():
                _last_id.append(r.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def output_notify(lyrics: SyncedLyrics | None, player: Player,
                  translit_mode: str | None = None,
                  providers: list[LyricsProvider] | None = None) -> None:
    if lyrics is not None:
        lyrics, _ = transliterate_lyrics(lyrics, translit_mode)
    poller = _PlaybackPoller(player, lyrics, translit_mode, providers)
    last_idx = -1
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
            line = poller.current_line(info.position_ms)
            if line is None:
                time.sleep(0.5)
                continue
            idx = find_current_line(poller.lyrics.lines, info.position_ms)
            if idx != last_idx:
                notify(line.text)
                last_idx = idx
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass


# ──────────────────────────── CLI ────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lyricsync",
        description="CLI lyrics synchronization tool — LRCLIB + LRCMɨX",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--tui", action="store_true",
                      help="Interactive terminal UI with 5 lyric lines")
    mode.add_argument("--json", action="store_true", dest="json_output",
                      help="Output machine-readable JSON")
    mode.add_argument("--once", action="store_true",
                      help="Print full lyrics once and exit")
    p.add_argument("--player", type=str, default=None,
                   help="Player backend: mpris, mpd, cmus (or auto-detect)")
    p.add_argument("--notify", action="store_true",
                   help="Show lyrics as desktop notifications")
    p.add_argument("--transliterate", type=str, default=None,
                   choices=["devanagari", "gurmukhi"],
                   help="Force transliteration mode")
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
        return [LRCMIXProvider()]
    return list(ALL_PROVIDERS)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    player: Player | None = None
    title = args.title or ""
    artist = args.artist or ""
    album = args.album or ""
    dur_s = 0.0

    if not args.once and not args.json_output:
        player = detect_player(args.player)
        if player is None:
            print("No supported player detected. Use --player or install "
                  "playerctl/mpc/cmus-remote.", file=sys.stderr)
            return 1
        print(f"Using player: {player.name}", file=sys.stderr)
    elif not title or not artist:
        player = detect_player(args.player)

    if player and (not title or not artist):
        info = player.get_playback()
        if info:
            title = title or info.title
            artist = artist or info.artist
            album = album or info.album
            dur_s = info.duration_ms / 1000
        else:
            print("Could not read playback metadata. "
                  "Provide --artist and --title.", file=sys.stderr)
            return 1

    if not title and not artist:
        print("No song metadata available. Use --artist and --title.",
              file=sys.stderr)
        return 1

    print(f"Fetching lyrics for: {artist} — {title}", file=sys.stderr)
    providers = resolve_providers(args.provider)
    lyrics = fetch_lyrics(artist, title, album, dur_s, providers)
    if lyrics is None:
        print("No lyrics found from any provider.", file=sys.stderr)
    elif not lyrics.synced and not args.tui:
        print("Note: only unsynchronized lyrics available.", file=sys.stderr)

    if args.json_output or args.once:
        if lyrics is None:
            print("No lyrics found from any provider.", file=sys.stderr)
            return 1
        if args.json_output:
            output_json(lyrics, args.transliterate)
        else:
            output_once(lyrics, args.transliterate)
    elif args.notify:
        if player is None:
            print("Notification mode requires a running player.",
                  file=sys.stderr)
            return 1
        output_notify(lyrics, player, args.transliterate, providers)
    elif args.tui:
        if player is None:
            print("TUI mode requires a running player.", file=sys.stderr)
            return 1
        output_tui(lyrics, player, args.transliterate, providers)
    else:
        if player is None:
            print("Live mode requires a running player.", file=sys.stderr)
            return 1
        output_plain(lyrics, player, args.transliterate, providers)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
