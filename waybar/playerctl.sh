#!/bin/bash

max=22
delay=0.1 #it was 0.15
sep="  •  "

get_icon() {
    case "$(playerctl status 2>/dev/null)" in
        Playing) echo "" ;;
        Paused)  echo "" ;;
        *)       echo "" ;;
    esac
}

last_text=""
pos=0

while true; do
    text=$(playerctl metadata --format '{{title}} -{{artist}}' 2>/dev/null)
    [ -z "$text" ] && text="No music"

    icon=$(get_icon)

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
