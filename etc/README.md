# lyricsync

CLI lyrics synchronization tool. Fetches synchronized lyrics from
[LRCLIB](https://lrclib.net) and [LRCMIX](https://lrcmux.dev),
transliterates Devanagari/Gurmukhi to casual Latin (Hinglish/Punglish),
and displays them in sync with the currently playing song.

Zero Python dependencies — uses only the standard library.

## Installation

```bash
# Clone or download lyricsync.py
curl -O https://raw.githubusercontent.com/user/lyricsync/main/lyricsync.py
chmod +x lyricsync.py

# Optional: install system dependencies for player integration
# Debian/Ubuntu:
sudo apt install playerctl libnotify-bin

# Arch:
sudo pacman -S playerctl libnotify

# For MPD users:
sudo apt install mpc

# For cmus users:
sudo apt install cmus
```

### System requirements

- Python 3.10+
- One of: `playerctl`, `mpc`, or `cmus-remote` (for live sync modes)
- `notify-send` (for `--notify` mode, optional)

## Usage

### Default mode (live sync)

Displays the current lyric line in the terminal as the song plays:

```bash
./lyricsync.py
./lyricsync.py --artist "Arijit Singh" --title "Tum Hi Ho"
```

### Interactive TUI (`--tui`)

Shows 5 lines (2 previous, 1 current highlighted, 2 upcoming):

```bash
./lyricsync.py --tui
./lyricsync.py --tui --artist "Pritam" --title "Channa Mereya"
```

### JSON output (`--json`)

Machine-readable output with timestamps, metadata, and transliteration mode:

```bash
./lyricsync.py --json --artist "AR Rahman" --title "Jai Ho"
./lyricsync.py --json --once --artist "Shankar" --title "Kal Ho Naa Ho"
```

### Print once (`--once`)

Prints the full lyrics with timestamps and exits:

```bash
./lyricsync.py --once --artist "Lata Mangeshkar" --title "Lag Jaa Gale"
./lyricsync.py --once --artist "Arijit Singh" --title "Agar Tum Saath Ho"
```

### Notification mode (`--notify`)

Shows the current lyric line as a desktop notification:

```bash
./lyricsync.py --notify
./lyricsync.py --notify --artist "Sonu Nigam" --title "Abhi Mujh Mein Kahin"
```

### Player selection (`--player`)

Force a specific player backend:

```bash
./lyricsync.py --player mpris          # playerctl (Spotify, VLC, etc.)
./lyricsync.py --player mpd            # Music Player Daemon
./lyricsync.py --player cmus           # cmus
```

### Provider selection (`--provider`)

Force a single lyrics provider:

```bash
./lyricsync.py --provider lrclib --artist "Artist" --title "Song"
./lyricsync.py --provider lrcmux --artist "Artist" --title "Song"
```

### Transliteration (`--transliterate`)

Force transliteration even for Latin-script text:

```bash
./lyricsync.py --transliterate devanagari --artist "Arijit Singh" --title "Kabira"
./lyricsync.py --transliterate gurmukhi --artist "Diljit" --title "G.O.A.T."
```

### Combined examples

```bash
# TUI with specific player
./lyricsync.py --tui --player mpris

# JSON with forced provider and transliteration
./lyricsync.py --json --provider lrclib --transliterate devanagari \
  --artist "Arijit Singh" --title "Tum Hi Ho"

# Once mode with album info
./lyricsync.py --once --artist "AR Rahman" --title "Roja" --album "Roja"

# Notify with specific player
./lyricsync.py --notify --player cmus
```

## CLI options

| Flag | Description |
|------|-------------|
| `--tui` | Interactive terminal UI |
| `--json` | Machine-readable JSON output |
| `--once` | Print lyrics once and exit |
| `--notify` | Desktop notification per line |
| `--player NAME` | Player backend (`mpris`, `mpd`, `cmus`) |
| `--provider NAME` | Lyrics source (`lrclib`, `lrcmux`) |
| `--transliterate MODE` | Force mode (`devanagari`, `gurmukhi`) |
| `--artist NAME` | Artist (for manual lookup) |
| `--title NAME` | Song title (for manual lookup) |
| `--album NAME` | Album (improves match accuracy) |

`--tui`, `--json`, and `--once` are mutually exclusive.

## Error handling

| Error | Meaning |
|-------|---------|
| `No supported player detected` | Install `playerctl`, `mpc`, or `cmus-remote` |
| `No song metadata available` | Pass `--artist` and `--title`, or start playback |
| `No lyrics found from any provider` | Song not in LRCLIB or LRCMIX databases |
| `Note: only unsynchronized lyrics available` | Plain lyrics found, no timestamps |
| `Could not read playback metadata` | Player has no active track |

## Running tests

```bash
python -m unittest tests.test_lyricsync -v
```

## Architecture

Single file, modular sections:

```
Data types        — LyricLine, SyncedLyrics, PlaybackInfo
LRC parser        — parse_lrc(), parse_plain_lyrics()
Transliteration   — Devanagari→Hinglish, Gurmukhi→Punglish
Providers         — LRCLIBProvider, LRCMIXProvider (abstract LyricsProvider)
Players           — MPRISPlayer, MPDPlayer, CMUSPlayer (abstract Player)
Sync engine       — find_current_line()
Output modes      — output_plain(), output_tui(), output_json(), output_once()
Notifications     — notify(), output_notify()
CLI               — build_parser(), main()
```

New providers, players, and output modes can be added by subclassing
`LyricsProvider` or `Player` and implementing the abstract methods.
