#!/bin/bash

pkill waybar
waybar &
pkill hyprpaper
hyprpaper &

sleep 1
if pgrep waybar >/dev/null && pgrep hyprpaper >/dev/null; then
  notify-send -i /usr/share/icons/breeze-dark/status/64/dialog-positive.svg "SYSTEM" "Successfully reloaded waybar and hyprpaper"
else
  notify-send -i dialog-error "SYSTEM" "Error: one or both processes failed to start"
fi
