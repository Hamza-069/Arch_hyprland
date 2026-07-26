#!/bin/bash

format_time() {
  printf '%d:%02d' $(($1 / 60)) $(($1 % 60))
}

COVER="/tmp/spotify_cover.jpg"

song_name=$(playerctl metadata -p spotify --format "<span foreground='#1ed760'>󰓇</span>   {{title}} ")
song_artist=$(playerctl metadata -p spotify --format '•  {{artist}} ')
art_url=$(playerctl metadata -p spotify --format '{{ mpris:artUrl }}')
position=$(playerctl position -p spotify 2>/dev/null | cut -d. -f1)
duration=$(playerctl metadata -p spotify --format '{{ duration(mpris:length) }}' 2>/dev/null)

if [ -n "$art_url" ]; then
  cached=$(cat /tmp/.spotify_art_url 2>/dev/null)
  if [ "$cached" != "$art_url" ]; then
    curl -sL "$art_url" -o "$COVER" 2>/dev/null
    echo "$art_url" >/tmp/.spotify_art_url
  fi
fi

dur_sec=$(echo "$duration" | awk -F: '{print $1*60+$2}')
pos_sec=${position:-0}
width=20
[ "$dur_sec" -gt 0 ] 2>/dev/null && filled=$((pos_sec * width / dur_sec)) || filled=0
empty=$((width - filled))

filled_bar=""
empty_bar=""
for ((i = 0; i < filled; i++)); do filled_bar+="━"; done
for ((i = 0; i < empty; i++)); do empty_bar+="─"; done

echo "$song_name $song_artist"
echo "<span foreground='#e0def4'>$(format_time "$pos_sec")  </span><span foreground='#1ed760'>$filled_bar</span><span foreground='#e0def4'>$empty_bar  $(format_time "$dur_sec")</span>"
