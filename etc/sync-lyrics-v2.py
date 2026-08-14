#!/usr/bin/env python3
"""
sync-lyrics.py — synced (LRC) lyrics for whatever is currently playing.

Pulls track metadata from MPRIS (via playerctl) and tries multiple lyric
backends in order, same fallback idea as caelestia-shell:

    Local (~/Music/lyrics/*.lrc)  ->  LRCLIB (lrclib.net)  ->  NetEase (163.com)

Gurmukhi (Punjabi script) lyrics are automatically transliterated into
casual Latin-script "Punglish" (e.g. ਮੈਨੂੰ ਤੇਰੇ ਨਾ' ਪਿਆਰ ਜੱਟਾ ਤਾਂ ->
Mainu tere naa' pyaar jatta taan) unless you pass --no-romanize.

Usage:
    ./sync-lyrics.py                    Live-sync lyrics to the current line in the terminal
    ./sync-lyrics.py --notify           Send each line as a desktop notification instead
    ./sync-lyrics.py --once             Print the full synced lyric sheet and exit
    ./sync-lyrics.py --no-romanize      Keep Gurmukhi/other non-Latin script as-is
    ./sync-lyrics.py --backends lrclib  Only use LRCLIB (skip local files + NetEase)
    ./sync-lyrics.py --local-dir ~/lyrics

Requires:
    - playerctl          (pacman -S playerctl / apt install playerctl)
    - python 'requests'  (pip install requests --break-system-packages)
    - notify-send        (only for --notify; works with swaync/dunst/mako)
"""

import argparse
import hashlib
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

# --- lyric backend config ---------------------------------------------------

LRCLIB_GET = "https://lrclib.net/api/get"
LRCLIB_SEARCH = "https://lrclib.net/api/search"
NETEASE_SEARCH = "https://music.163.com/api/search/get"
NETEASE_LYRIC = "https://music.163.com/api/song/lyric"
NETEASE_HEADERS = {
    "Referer": "https://music.163.com/",
    "User-Agent": "Mozilla/5.0 sync-lyrics (https://github.com/caelestia-dots/shell-inspired)",
}

CACHE_DIR = Path.home() / ".cache" / "sync-lyrics"
DEFAULT_LOCAL_DIR = Path.home() / "Music" / "lyrics"
POLL_INTERVAL = 0.5  # seconds
LRC_LINE_RE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")


# =============================================================================
# Gurmukhi -> casual Latin ("Punglish") transliteration
# =============================================================================

_CONSONANTS = {
    "ਸ": "s", "ਹ": "h",
    "ਕ": "k", "ਖ": "kh", "ਗ": "g", "ਘ": "gh", "ਙ": "ng",
    "ਚ": "ch", "ਛ": "chh", "ਜ": "j", "ਝ": "jh", "ਞ": "ny",
    "ਟ": "t", "ਠ": "th", "ਡ": "d", "ਢ": "dh", "ਣ": "n",
    "ਤ": "t", "ਥ": "th", "ਦ": "d", "ਧ": "dh", "ਨ": "n",
    "ਪ": "p", "ਫ": "ph", "ਬ": "b", "ਭ": "bh", "ਮ": "m",
    "ਯ": "y", "ਰ": "r", "ਲ": "l", "ਵ": "v", "ੜ": "r",
}
_NUKTA_VARIANTS = {"ਸ": "sh", "ਖ": "kh", "ਗ": "g", "ਜ": "z", "ਫ": "f", "ਲ": "l"}
_INDEP_VOWELS = {
    "ਅ": "a", "ਆ": "aa", "ਇ": "i", "ਈ": "ee", "ਉ": "u",
    "ਊ": "oo", "ਏ": "e", "ਐ": "ai", "ਓ": "o", "ਔ": "au",
}
_MATRAS = {
    "ਾ": "aa", "ਿ": "i", "ੀ": "ee", "ੁ": "u", "ੂ": "oo",
    "ੇ": "e", "ੈ": "ai", "ੋ": "o", "ੌ": "au",
}
_ADDAK, _TIPPI, _BINDI, _HALANT, _NUKTA = "ੱ", "ੰ", "ਂ", "੍", "਼"
_NASAL_MARKS = (_TIPPI, _BINDI)
_NASAL_BASES = {"n", "m", "ng", "ny"}


def _is_gurmukhi(text):
    return any("\u0A00" <= ch <= "\u0A7F" for ch in text)


def _gm_tokenize(word):
    chars = list(word)
    n = len(chars)
    syllables = []
    i = 0
    geminate_next = False

    while i < n:
        ch = chars[i]

        if ch == _ADDAK:
            geminate_next = True
            i += 1
            continue

        if ch in _CONSONANTS:
            base = _CONSONANTS[ch]
            if i + 1 < n and chars[i + 1] == _NUKTA and ch in _NUKTA_VARIANTS:
                base = _NUKTA_VARIANTS[ch]
                i += 1
            if geminate_next:
                base = base[0] + base
                geminate_next = False

            vowel, is_matra = "a", False
            j = i + 1
            if j < n and chars[j] in _MATRAS:
                vowel, is_matra = _MATRAS[chars[j]], True
                i = j
            elif j < n and chars[j] == _HALANT:
                vowel, is_matra = "", True
                i = j

            nasal = None
            k = i + 1
            if k < n and chars[k] in _NASAL_MARKS:
                nasal = chars[k]
                i = k

            syllables.append(dict(base=base, vowel=vowel, is_matra=is_matra,
                                   nasal=nasal, indep=False, literal=None))
            i += 1
            continue

        if ch in _INDEP_VOWELS:
            vowel = _INDEP_VOWELS[ch]
            nasal = None
            k = i + 1
            if k < n and chars[k] in _NASAL_MARKS:
                nasal = chars[k]
                i = k
            syllables.append(dict(base=None, vowel=vowel, is_matra=False,
                                   nasal=nasal, indep=True, literal=None))
            i += 1
            continue

        if ch == _NUKTA:
            i += 1
            continue

        syllables.append(dict(base=None, vowel=None, is_matra=False,
                               nasal=None, indep=False, literal=ch))
        i += 1

    return syllables


def _gm_apply_rules(syllables):
    # i + independent-vowel glide: "pi" + "aa" -> "pyaa"
    for idx in range(1, len(syllables)):
        cur, prev = syllables[idx], syllables[idx - 1]
        if (cur["indep"] and prev["literal"] is None and
                prev["is_matra"] and prev["vowel"] == "i"):
            prev["vowel"] = ""
            cur["vowel"] = "y" + cur["vowel"]

    # nasalization: shorten long high vowels, skip redundant 'n' after nasal consonants
    for s in syllables:
        if s["literal"] is not None or not s["nasal"]:
            continue
        if s["vowel"] == "oo":
            s["vowel"] = "u"
        elif s["vowel"] == "ee":
            s["vowel"] = "i"
        skip_n = s["base"] is not None and s["base"] in _NASAL_BASES
        s["_append_n"] = not skip_n

    # word-final matra-'aa' shortens to 'a' when not nasalized
    if syllables and syllables[-1]["literal"] is None:
        last = syllables[-1]
        if last["is_matra"] and last["vowel"] == "aa" and not last["nasal"]:
            last["vowel"] = "a"

    # word-final bare consonant drops its inherent schwa
    real = [s for s in syllables if s["literal"] is None]
    if len(real) > 1:
        last = real[-1]
        if (not last["indep"] and not last["is_matra"] and
                last["vowel"] == "a" and not last["nasal"]):
            last["vowel"] = ""

    return syllables


def _gm_render(syllables):
    out = []
    for s in syllables:
        if s["literal"] is not None:
            out.append(s["literal"])
            continue
        piece = (s["base"] or "") + s["vowel"]
        if s["nasal"] and s.get("_append_n", True):
            piece += "n"
        out.append(piece)
    return "".join(out)


def _gm_word(word):
    return _gm_render(_gm_apply_rules(_gm_tokenize(word)))


def transliterate_gurmukhi(text):
    words = text.split(" ")
    latin = [_gm_word(w) for w in words]
    result = " ".join(latin)
    return result[:1].upper() + result[1:] if result else result


def maybe_romanize(text, enabled):
    if enabled and _is_gurmukhi(text):
        return transliterate_gurmukhi(text)
    return text


# =============================================================================
# MPRIS / playerctl
# =============================================================================

def run(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def get_player():
    players = run(["playerctl", "-l"]).splitlines()
    return players[0] if players else None


def get_metadata(player):
    fmt = "{{artist}}\t{{title}}\t{{album}}\t{{mpris:length}}"
    out = run(["playerctl", "-p", player, "metadata", "--format", fmt])
    if not out:
        return None
    parts = out.split("\t")
    if len(parts) < 4:
        return None
    artist, title, album, length_us = parts
    try:
        duration = int(length_us) / 1_000_000
    except ValueError:
        duration = 0.0
    if not artist or not title:
        return None
    return {"artist": artist, "title": title, "album": album, "duration": duration}


def get_position(player):
    pos = run(["playerctl", "-p", player, "position"])
    try:
        return float(pos)
    except ValueError:
        return 0.0


def get_status(player):
    return run(["playerctl", "-p", player, "status"])


# =============================================================================
# Cache
# =============================================================================

def cache_key(meta):
    raw = f"{meta['artist']}|{meta['title']}|{meta['album']}"
    return hashlib.sha1(raw.encode()).hexdigest()


def load_cached(meta):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{cache_key(meta)}.lrc"
    return path.read_text() if path.exists() else None


def save_cached(meta, text):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{cache_key(meta)}.lrc").write_text(text)


# =============================================================================
# Lyric backends
# =============================================================================

def try_local(meta, local_dir):
    """Look for a matching .lrc under local_dir: exact filename match first,
    then a recursive search for one containing both artist and title."""
    local_dir = Path(local_dir).expanduser()
    if not local_dir.is_dir():
        return None

    artist, title = meta["artist"], meta["title"]
    for candidate in (f"{artist} - {title}.lrc", f"{title}.lrc"):
        p = local_dir / candidate
        if p.exists():
            return p.read_text(errors="ignore")

    artist_l, title_l = artist.lower(), title.lower()
    for p in local_dir.rglob("*.lrc"):
        name = p.stem.lower()
        if title_l in name and (artist_l in name or not artist_l):
            return p.read_text(errors="ignore")

    return None


def try_lrclib(meta):
    """Direct match first, then fall back to search."""
    params = {"track_name": meta["title"], "artist_name": meta["artist"]}
    if meta["album"]:
        params["album_name"] = meta["album"]
    if meta["duration"] > 0:
        params["duration"] = round(meta["duration"])

    try:
        r = requests.get(LRCLIB_GET, params=params, timeout=8)
        if r.status_code == 200:
            synced = r.json().get("syncedLyrics")
            if synced:
                return synced
    except requests.RequestException:
        pass

    try:
        r = requests.get(
            LRCLIB_SEARCH,
            params={"track_name": meta["title"], "artist_name": meta["artist"]},
            timeout=8,
        )
        if r.status_code == 200:
            for result in r.json():
                if result.get("syncedLyrics"):
                    return result["syncedLyrics"]
    except requests.RequestException:
        pass

    return None


def try_netease(meta):
    """Search NetEase Cloud Music for the track, then fetch its LRC lyric.
    Good fallback for catalog LRCLIB is thin on (e.g. Punjabi/Bollywood)."""
    query = f"{meta['title']} {meta['artist']}".strip()
    try:
        r = requests.get(
            NETEASE_SEARCH,
            params={"s": query, "type": 1, "limit": 5, "offset": 0},
            headers=NETEASE_HEADERS,
            timeout=8,
        )
        if r.status_code != 200:
            return None
        songs = r.json().get("result", {}).get("songs", [])
        if not songs:
            return None
        song_id = songs[0]["id"]
    except (requests.RequestException, ValueError, KeyError):
        return None

    try:
        r = requests.get(
            NETEASE_LYRIC,
            params={"id": song_id, "lv": -1, "kv": -1, "tv": -1},
            headers=NETEASE_HEADERS,
            timeout=8,
        )
        if r.status_code != 200:
            return None
        return r.json().get("lrc", {}).get("lyric") or None
    except (requests.RequestException, ValueError, KeyError):
        return None


BACKEND_FUNCS = {
    "local": lambda meta, args: try_local(meta, args.local_dir),
    "lrclib": lambda meta, args: try_lrclib(meta),
    "netease": lambda meta, args: try_netease(meta),
}


def get_lyrics_for_track(meta, args):
    cached = load_cached(meta)
    if cached is not None:
        return cached, "cache"

    for name in args.backend_order:
        func = BACKEND_FUNCS.get(name)
        if not func:
            continue
        lrc = func(meta, args)
        if lrc:
            save_cached(meta, lrc)
            return lrc, name

    return None, None


# =============================================================================
# LRC parsing + display
# =============================================================================

def parse_lrc(text, romanize):
    lines = []
    for raw_line in text.splitlines():
        m = LRC_LINE_RE.match(raw_line)
        if not m:
            continue
        minutes, seconds, content = m.groups()
        t = int(minutes) * 60 + float(seconds)
        content = maybe_romanize(content.strip(), romanize)
        lines.append((t, content))
    lines.sort(key=lambda x: x[0])
    return lines


def current_line_index(lines, position):
    idx = -1
    for i, (t, _) in enumerate(lines):
        if t <= position:
            idx = i
        else:
            break
    return idx


def notify(title, body):
    run(["notify-send", "-a", "sync-lyrics", "-r", "9271", title, body])


def watch(player, args):
    last_key = None
    lines = []
    printed_idx = -1

    while True:
        status = get_status(player)
        meta = get_metadata(player)

        if not meta:
            time.sleep(POLL_INTERVAL)
            continue

        key = cache_key(meta)
        if key != last_key:
            last_key = key
            printed_idx = -1
            print(f"\n♪ {meta['artist']} — {meta['title']}", file=sys.stderr)
            lrc_text, source = get_lyrics_for_track(meta, args)
            if not lrc_text:
                print("  (no synced lyrics found in any backend)", file=sys.stderr)
                lines = []
            else:
                print(f"  (source: {source})", file=sys.stderr)
                lines = parse_lrc(lrc_text, not args.no_romanize)

        if status != "Playing" or not lines:
            time.sleep(POLL_INTERVAL)
            continue

        position = get_position(player)
        idx = current_line_index(lines, position)

        if idx != printed_idx and idx >= 0:
            printed_idx = idx
            text = lines[idx][1] or "♪"
            if args.notify:
                notify(f"{meta['artist']} — {meta['title']}", text)
            else:
                print(f"\r\033[K{text}", end="", flush=True)

        time.sleep(POLL_INTERVAL)


def once(player, args):
    meta = get_metadata(player)
    if not meta:
        print("No track currently playing.", file=sys.stderr)
        sys.exit(1)
    print(f"{meta['artist']} — {meta['title']}\n")
    lrc_text, source = get_lyrics_for_track(meta, args)
    if not lrc_text:
        print("No synced lyrics found in any backend for this track.")
        sys.exit(1)
    print(f"(source: {source})\n")
    for t, text in parse_lrc(lrc_text, not args.no_romanize):
        mm, ss = divmod(int(t), 60)
        print(f"[{mm:02d}:{ss:02d}] {text}")


def main():
    parser = argparse.ArgumentParser(description="Show synced lyrics for the currently playing track.")
    parser.add_argument("--notify", action="store_true", help="send lines as desktop notifications instead of printing")
    parser.add_argument("--once", action="store_true", help="print the full synced lyric sheet and exit")
    parser.add_argument("--player", help="MPRIS player name (defaults to the first one playerctl finds)")
    parser.add_argument("--backends", default="local,lrclib,netease",
                         help="comma-separated backend order to try: local,lrclib,netease (default: all three)")
    parser.add_argument("--local-dir", default=str(DEFAULT_LOCAL_DIR),
                         help=f"directory to search for local .lrc files (default: {DEFAULT_LOCAL_DIR})")
    parser.add_argument("--no-romanize", action="store_true",
                         help="don't transliterate Gurmukhi lyrics to Latin script")
    args = parser.parse_args()
    args.backend_order = [b.strip() for b in args.backends.split(",") if b.strip()]

    player = args.player or get_player()
    if not player:
        print("No MPRIS-capable player found. Is anything playing?", file=sys.stderr)
        sys.exit(1)

    if args.once:
        once(player, args)
    else:
        try:
            watch(player, args)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
