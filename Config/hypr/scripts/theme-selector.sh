#!/bin/bash

ROFI_COLORS_DIR="$HOME/.config/rofi/colors"
WAYBAR_COLORS_DIR="$HOME/.config/waybar/Colors"
WAYBAR_STYLE="$HOME/.config/waybar/style.css"
HYPR_MODS="$HOME/.config/hypr/mods"
ROFI_SHARED=(
  "$HOME/.config/rofi/launchers/type-1/shared/colors.rasi"
  "$HOME/.config/rofi/applets/shared/colors.rasi"
  "$HOME/.config/rofi/powermenu/type-2/shared/colors.rasi"
)

icon=$'⏎'

# Theme definitions: rofi_key="Display|waybar_css|hypr_active|kitten_name"
declare -A THEMES
THEMES["nord"]="${icon} Nord|nord.css|5e81ac|Nord"
THEMES["tokyonight"]="${icon} Tokyo Night|tokyo-night.css|bb9af7|Tokyo\ Night\ Storm"
THEMES["catppuccin"]="${icon} Catppuccin|catppuccin.css|dda0dd|Catppuccin-Mocha"
THEMES["gruvbox"]="${icon} Gruvbox|gruvbox.css|83a598|Gruvbox\ Dark\ Soft"
THEMES["dracula"]="${icon} Dracula|dracula.css|bd93f9|Dracula"
THEMES["everforest"]="${icon} Everforest|everforest.css|7fbbb3|Everforest\ Dark\ Medium"
THEMES["onedark"]="${icon} One Dark|onedark.css|61afef|One Dark"
THEMES["solarized"]="${icon} Solarized|solarized.css|268bd2|Solarized Dark"

# Build menu from rofi colors that have a matching waybar file
names=()
for rasi in "$ROFI_COLORS_DIR"/*.rasi; do
  key=$(basename "$rasi" .rasi)
  if [[ -n "${THEMES[$key]}" ]]; then
    IFS='|' read -r display waybar_css _ <<<"${THEMES[$key]}"
    if [[ -f "$WAYBAR_COLORS_DIR/$waybar_css" ]]; then
      names+=("$display")
    fi
  fi
done

# Rofi menu
selected=$(printf "%s\n" "${names[@]}" | rofi -dmenu -p "Theme" -theme "$HOME/.config/rofi/launchers/type-1/style-5.rasi")
[[ -z "$selected" ]] && exit 1

# Find and apply
for key in "${!THEMES[@]}"; do
  IFS='|' read -r display waybar_css active kitten_name <<<"${THEMES[$key]}"
  [[ "$display" != "$selected" ]] && continue

  # Waybar
  sed -i "1s|@import \"Colors/[^\"]*\";|@import \"Colors/$waybar_css\";|" "$WAYBAR_STYLE"

  # Rofi
  rasi_file="$key.rasi"
  if [[ -f "$ROFI_COLORS_DIR/$rasi_file" ]]; then
    for f in "${ROFI_SHARED[@]}"; do
      sed -i "s|@import \"~/.config/rofi/colors/[^\"]*\"|@import \"~/.config/rofi/colors/$rasi_file\"|" "$f"
    done
  fi

  # Hyprland
  sed -i "s/active_border = \"rgb([^)]*)\"/active_border = \"rgb($active)\"/" "$HYPR_MODS/Look_n_Feel.lua"

  # Kitty
  kitten themes "$kitten_name" 2>/dev/null

  pkill waybar 2>/dev/null || true
  waybar &
  hyprctl reload
  notify-send -i /usr/share/icons/breeze-dark/status/64/dialog-positive.svg "Theme" "Switched to ${display#* }"
  break
done
