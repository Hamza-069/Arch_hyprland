#!/usr/bin/env bash
set -euo pipefail

URL="https://devimages-cdn.apple.com/design/resources/download/SF-Pro.dmg"
FONT_DIR="$HOME/.local/share/fonts"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if ! command -v 7z >/dev/null 2>&1; then
  echo "Error: 7z is required. Install it with: sudo pacman -S p7zip" >&2
  exit 1
fi

echo "Creating font directory..."
mkdir -p "$FONT_DIR"

echo "Downloading SF Pro..."
curl -fL --progress-bar -o "$TMP_DIR/SF-Pro.dmg" "$URL"

cd "$TMP_DIR"

echo "Extracting DMG..."
7z x -y "SF-Pro.dmg" >/dev/null

echo "Locating macOS package..."
PKG_PATH="$(find . -type f -name '*.pkg' | head -n 1)"

if [[ -z "$PKG_PATH" ]]; then
  echo "Error: could not find a .pkg file inside the DMG." >&2
  exit 1
fi

echo "Found package: $PKG_PATH"
echo "Extracting macOS package..."
7z x -y "$PKG_PATH" >/dev/null

echo "Locating Payload..."
PAYLOAD_PATH="$(find . -type f -name 'Payload' | head -n 1)"

if [[ -z "$PAYLOAD_PATH" ]]; then
  echo "Error: could not find Payload inside the package." >&2
  exit 1
fi

echo "Extracting Payload..."
7z x -y "$PAYLOAD_PATH" >/dev/null

echo "Locating Payload~..."
PAYLOAD_TILDE_PATH="$(find . -type f -name 'Payload~' | head -n 1)"

if [[ -z "$PAYLOAD_TILDE_PATH" ]]; then
  echo "Error: could not find Payload~ after extracting Payload." >&2
  exit 1
fi

echo "Extracting Payload~..."
7z x -y "$PAYLOAD_TILDE_PATH" >/dev/null

echo "Installing fonts..."
find . -type f \( -iname '*.otf' -o -iname '*.ttf' \) -print0 |
  while IFS= read -r -d '' font; do
    echo "Installing: $(basename "$font")"
    install -Dm 0644 "$font" "$FONT_DIR/$(basename "$font")"
  done

echo "Refreshing font cache..."
fc-cache -f "$FONT_DIR"

echo "Installed fonts:"
fc-list | grep -i "SF Pro" || true

echo "Done."
