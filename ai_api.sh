#!/usr/bin/env bash
#
# text-extractor-setup — paste your API key once; it's saved for text-extractor.
#
# Usage: text-extractor-setup [--pause]
# Writes AI_API_KEY to ${XDG_CONFIG_HOME:-~/.config}/ai_api.env (chmod 600),
# keeping any other settings already in that file. Runs fine from a launcher or
# hotkey too: with no terminal attached, it reopens itself in one.

set -euo pipefail
umask 077

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
CONFIG_FILE="$CONFIG_DIR/ai_api.env"
PAUSE=false
[[ "${1:-}" == "--pause" ]] && PAUSE=true

# No terminal attached (launcher/hotkey)? Reopen inside one.
if [[ ! -t 0 && -n "${WAYLAND_DISPLAY:-}${DISPLAY:-}" ]]; then
  for term in foot kitty alacritty wezterm konsole gnome-terminal xterm; do
    command -v "$term" >/dev/null 2>&1 || continue
    case "$term" in
    foot | kitty) exec "$term" "$0" --pause ;;
    wezterm) exec wezterm start -- "$0" --pause ;;
    gnome-terminal) exec gnome-terminal -- "$0" --pause ;;
    *) exec "$term" -e "$0" --pause ;;
    esac
  done
fi

finish() {
  if $PAUSE; then read -rp "Press Enter to close…" _ || true; fi
}
trap finish EXIT

has_key() {
  [[ -f "$CONFIG_FILE" ]] && grep -Eq '^[[:space:]]*(export[[:space:]]+)?AI_API_KEY[[:space:]]*=[[:space:]]*["'\'']?[^"'\''[:space:]]' "$CONFIG_FILE"
}

echo "AI_api setup"
echo

if has_key; then
  read -rp "An API key is already saved. Replace it? [y/N] " answer
  [[ "$answer" =~ ^[Yy] ]] || {
    echo "Nothing changed."
    exit 0
  }
fi

echo "Paste your API key (input is hidden), then press Enter."
read -rsp "API key: " key
echo
key=$(printf '%s' "$key" | tr -d '[:space:]"'"'")
[[ -n "$key" ]] || {
  echo "No key entered; nothing saved." >&2
  exit 1
}

case "$key" in
AQ.* | AIza*) provider="Google Gemini" ;;
sk-ant-*) provider="Anthropic" ;;
*) provider="OpenAI-compatible" ;;
esac

# Rewrite the config atomically, keeping every other setting.
mkdir -p "$CONFIG_DIR"
tmp=$(mktemp "$CONFIG_DIR/.ai_api.XXXXXX")
trap 'rm -f "$tmp"; finish' EXIT
if [[ -f "$CONFIG_FILE" ]]; then
  grep -Ev '^[[:space:]]*(export[[:space:]]+)?AI_API_KEY[[:space:]]*=' "$CONFIG_FILE" >"$tmp" || true
else
  printf '# text-extractor config. Optional: AI_PROVIDER, AI_MODEL, AI_API_URL, OCR_LANG\n' >"$tmp"
fi
printf 'AI_API_KEY="%s"\n' "$key" >>"$tmp"
chmod 600 "$tmp"
mv "$tmp" "$CONFIG_FILE"

echo
echo "Saved ${provider} key (…${key: -4}) to $CONFIG_FILE"
echo "Provider is detected automatically. Run text-extractor to try it."
