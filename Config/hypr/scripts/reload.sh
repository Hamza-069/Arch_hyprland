#!/bin/bash

pkill waybar
waybar &
pkill hyprpaper
hyprpaper &

sleep 2.5
notify-send "SYSTEM" "Successfully reloaded waybar and hyprpaper"

