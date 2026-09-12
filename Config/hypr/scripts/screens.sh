#!/bin/bash
pgrep -f 'kitty .*screensaver.peaclock' >/dev/null && exit 0

for monitor in $(hyprctl monitors -j | jq -r '.[].name'); do
  hyprctl dispatch "hl.dsp.exec_cmd(\"kitty --start-as=fullscreen --class screensaver.peaclock -e peaclock\", { monitor = \"$monitor\" })" >/dev/null
done
