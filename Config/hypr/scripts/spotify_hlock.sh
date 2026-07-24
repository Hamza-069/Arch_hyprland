#!/bin/bash

format_time() {
  printf '%d:%02d' $(($1 / 60)) $(($1 % 60))
}

song_name=$(playerctl metadata -p spotify --format "<span foreground='#1ed760'>󰓇</span>   {{title}} ")
song_artist=$(playerctl metadata -p spotify --format '•  {{artist}} ')
position=$(playerctl position -p spotify 2>/dev/null | cut -d. -f1)
duration=$(playerctl metadata -p spotify --format '{{ duration(mpris:length) }}' 2>/dev/null)
progress="$(format_time "$position")/$duration"

echo "$song_name $song_artist $progress"
