#!/bin/bash

format_time() {
  printf '%d:%02d' $(($1 / 60)) $(($1 % 60))
}

COVER="/tmp/spotify_cover.jpg"
ART_CACHE="/tmp/.spotify_art_url"

if ! pgrep -x spotify &>/dev/null; then
  rm -f "$COVER" "$ART_CACHE"
  exit 0
fi

song_name=$(playerctl metadata -p spotify --format "<span foreground='#1ed760'>󰓇</span>   {{title}} ")
song_artist=$(playerctl metadata -p spotify --format '•  {{artist}} ')
art_url=$(playerctl metadata -p spotify --format '{{ mpris:artUrl }}')
position=$(playerctl position -p spotify 2>/dev/null | cut -d. -f1)
duration=$(playerctl metadata -p spotify --format '{{ duration(mpris:length) }}' 2>/dev/null)

# Download album cover if the URL changed or the cached image is missing
if [ -n "$art_url" ]; then
  cached=$(cat "$ART_CACHE" 2>/dev/null)

  if [ "$cached" != "$art_url" ] || [ ! -f "$COVER" ]; then
    curl -sL "$art_url" -o "$COVER" 2>/dev/null
    echo "$art_url" >"$ART_CACHE"
  fi
fi

dur_sec=$(echo "$duration" | awk -F: '{print $1*60+$2}')
pos_sec=${position:-0}

width=20

if [ "$dur_sec" -gt 0 ] 2>/dev/null; then
  filled=$((pos_sec * width / dur_sec))
else
  filled=0
fi

empty=$((width - filled))

filled_bar=""
empty_bar=""

for ((i = 0; i < filled; i++)); do
  filled_bar+="━"
done

for ((i = 0; i < empty; i++)); do
  empty_bar+="─"
done

echo "$song_name $song_artist"

echo "<span foreground='#e0def4'>$(format_time "$pos_sec")  </span><span foreground='#1ed760'>$filled_bar</span><span foreground='#e0def4'>$empty_bar  $(format_time "$dur_sec")</span>"
