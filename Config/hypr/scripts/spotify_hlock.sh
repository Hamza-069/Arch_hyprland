#!/bin/bash

song_name=$(playerctl metadata -p spotify --format '󰓇  {{title}} ')
song_artist=$(playerctl metadata -p spotify --format '• {{artist}} ')

echo "$song_name 
$song_artist"
