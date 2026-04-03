#!/bin/bash

max=22
delay=0.09
sep="  •  "

# 🔥 Find the real active player
get_active_player() {
    for p in $(playerctl -l 2>/dev/null); do
        status=$(playerctl -p "$p" status 2>/dev/null)
        if [[ "$status" == "Playing" ]]; then
            echo "$p"
            return
        fi
    done

    # fallback: first available player
    playerctl -l 2>/dev/null | head -n1
}

get_icon() {
    case "$1" in
        Playing) echo "" ;;
        Paused)  echo "" ;;
        *)       echo "" ;;
    esac
}

last_text=""
pos=0

while true; do
    player=$(get_active_player)

    status=$(playerctl -p "$player" status 2>/dev/null)
    text=$(playerctl -p "$player" metadata --format '{{title}} -{{artist}}' 2>/dev/null)

    # 🔥 Fix: Spotify bug (Stopped but actually playing)
    if [[ "$status" == "Stopped" ]]; then
        if playerctl -p "$player" metadata title &>/dev/null; then
            status="Playing"
        fi
    fi

    # fallback if nothing at all
    if [[ -z "$text" ]]; then
        echo " No Media Playing"
        sleep 0.5
        continue
    fi

    icon=$(get_icon "$status")

    if [[ "$text" != "$last_text" ]]; then
        pos=0
        last_text="$text"
    fi

    if [ ${#text} -le $max ]; then
        echo "$icon $text"
        sleep 0.3
        continue
    fi

    scroll="$text$sep$text$sep"
    len=${#scroll}

    # 🔥 TRUE WRAP AROUND LOGIC
    output=""
    for ((i=0; i<max; i++)); do
        idx=$(( (pos + i) % len ))
        output+="${scroll:$idx:1}"
    done

    echo "$icon $output"

    pos=$(( (pos + 1) % len ))

    sleep $delay
done
