#!/bin/bash

set -euo pipefail

WALLPAPER_DIR="$HOME/.config/hypr/theme-wallpapers"
THUMB_DIR="$HOME/.cache/wallpaper-thumbs"
HYPRPAPER_CONF="$HOME/.config/hypr/hyprpaper.conf"
ROFI_THEME="$HOME/.config/rofi/launchers/type-1/wallpaper.rasi"

missing=()
for cmd in rofi hyprctl; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done
command -v magick >/dev/null 2>&1 || command -v convert >/dev/null 2>&1 || missing+=("imagemagick")
if ((${#missing[@]})); then
  notify-send -a "Wallpaper" "Missing dependencies: ${missing[*]}"
  exit 1
fi

if command -v magick >/dev/null 2>&1; then
  IMCMD="magick"
else
  IMCMD="convert"
fi

mapfile -d '' -t images < <(find "$WALLPAPER_DIR" -maxdepth 1 -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' \) -print0 | LC_ALL=C sort -z)

if ((${#images[@]} == 0)); then
  notify-send -a "Wallpaper" "No wallpapers found in $WALLPAPER_DIR"
  exit 1
fi

mkdir -p "$THUMB_DIR"

for img in "${images[@]}"; do
  thumb="$THUMB_DIR/$(basename "$img")"
  if [[ ! -f "$thumb" || "$img" -nt "$thumb" ]]; then
    "$IMCMD" "$img" -thumbnail "400x225^" -gravity center -extent 400x225 "$thumb" 2>/dev/null || true
  fi
done

selected=$(for img in "${images[@]}"; do
    printf '%s\0icon\x1f%s\n' "$(basename "$img")" "$THUMB_DIR/$(basename "$img")"
  done | rofi -dmenu -show-icons -no-custom -p "Wallpaper" -theme "$ROFI_THEME" || true)
[[ -z "$selected" ]] && exit 0

path="$WALLPAPER_DIR/$selected"
[[ -f "$path" ]] || exit 1

monitors=()
while read -r name; do
  [[ -n "$name" ]] && monitors+=("$name")
done < <(hyprctl monitors 2>/dev/null | awk '/^Monitor /{print $2}')
((${#monitors[@]})) || monitors+=("eDP-1")

for mon in "${monitors[@]}"; do
  hyprctl hyprpaper wallpaper "$mon,$path" 2>/dev/null || true
done

sed -i "s|path = .*|path = $path|" "$HYPRPAPER_CONF"

notify-send -i "$path" "Wallpaper" "${selected%.*}"
