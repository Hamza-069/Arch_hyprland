#!/usr/bin/env bash

set -euo pipefail

for cmd in grim slurp tesseract wl-copy notify-send; do
  command -v "$cmd" >/dev/null 2>&1 || {
    notify-send "Text Extractor" "Missing dependency: $cmd"
    exit 1
  }
done

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

grim -g "$(slurp)" "$TMPDIR/capture.png" || exit 0

if command -v convert >/dev/null 2>&1; then
  convert "$TMPDIR/capture.png" \
    -colorspace Gray \
    -contrast-stretch 2%x1% \
    -resize x1200 \
    -sharpen 0x1 \
    "$TMPDIR/processed.png"
else
  cp "$TMPDIR/capture.png" "$TMPDIR/processed.png"
fi

best_text=""
best_len=0

for psm in 3 6; do
  tesseract "$TMPDIR/processed.png" "$TMPDIR/out_${psm}" \
    -l eng \
    --oem 1 \
    --psm "$psm" \
    2>/dev/null || continue

  text=$(sed '/^[[:space:]]*$/d' "$TMPDIR/out_${psm}.txt") || continue

  len=${#text}
  if (( len > best_len )); then
    best_len=$len
    best_text="$text"
  fi
done

if [[ -z "$best_text" ]]; then
  notify-send -a "Text Extractor" "No text found"
  exit 0
fi

printf "%s" "$best_text" | wl-copy

chars=$(printf "%s" "$best_text" | wc -m)

notify-send \
  -a "Text Extractor" \
  "Text copied to clipboard" \
  "${chars} characters copied" \
  -i /usr/share/icons/breeze-dark/status/64/dialog-positive.svg
