#!/usr/bin/env bash

set -euo pipefail

# Ensure required commands exist
for cmd in grim slurp tesseract wl-copy notify-send; do
  command -v "$cmd" >/dev/null 2>&1 || {
    notify-send "Text Extractor" "Missing dependency: $cmd"
    exit 1
  }
done

# Extract text
text=$(
  grim -g "$(slurp)" - |
    tesseract stdin stdout \
      -l eng+swe \
      --oem 1 \
      --psm 6 \
      -c preserve_interword_spaces=1 |
    sed '/^[[:space:]]*$/d'
)

# User cancelled the selection
if [[ -z "$text" ]]; then
  notify-send -a "Text Extractor" "No text found"
  exit 0
fi

# Copy to clipboard
printf "%s" "$text" | wl-copy

# Count characters for the notification
chars=$(printf "%s" "$text" | wc -m)

notify-send \
  -a "Text Extractor" \
  "Text copied to clipboard" \
  "$chars characters copied" -i /usr/share/icons/breeze-dark/status/64/dialog-positive.svg
