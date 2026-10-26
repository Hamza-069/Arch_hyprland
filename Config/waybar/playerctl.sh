#!/bin/bash
export LC_ALL=${LC_ALL:-en_US.UTF-8}

max=22
delay=0.07
sep="  •  "
US=$'\x1f' # field separator (non-whitespace so empty fields survive)

# open a fd once so we can "sleep" without forking
exec {sleepfd}<> <(:)
nap() { read -rt "$1" -u "$sleepfd" || :; }

icon_play=$'\uf04c'
icon_pause=$'\uf04b'
icon_stop=$'\uf04d'

icon="" text="" last_text="" last_out="" pos=0 last_poll=-1

poll() {
  local lines line name st title artist
  local sp="" pl="" first=""

  lines=$(playerctl -a metadata \
    --format "{{playerName}}${US}{{status}}${US}{{title}}${US}{{artist}}" 2>/dev/null)

  text="" icon=""
  [[ -z "$lines" ]] && return

  while IFS="$US" read -r name st title artist; do
    [[ -z "$first" ]] && first="$name${US}$st${US}$title${US}$artist"
    if [[ "$name" == spotify ]]; then
      sp="$name${US}$st${US}$title${US}$artist"
    elif [[ -z "$pl" && "$st" == Playing ]]; then
      pl="$name${US}$st${US}$title${US}$artist"
    fi
  done <<<"$lines"

  # 1. Spotify  2. anything playing  3. first available
  line=${sp:-${pl:-$first}}
  IFS="$US" read -r name st title artist <<<"$line"

  # Stopped but has metadata -> treat as Playing
  [[ "$st" == Stopped && -n "$title" ]] && st=Playing

  [[ -z "$title" ]] && return
  text="$title - $artist"

  case "$st" in
  Playing) icon=$icon_play ;;
  Paused) icon=$icon_pause ;;
  *) icon=$icon_stop ;;
  esac
}

emit() {
  [[ "$1" == "$last_out" ]] && return
  last_out=$1
  echo "$1"
}

while true; do
  if ((SECONDS != last_poll)); then
    last_poll=$SECONDS
    poll
  fi

  if [[ -z "$text" ]]; then
    emit "$icon_stop No Media Playing"
    nap 0.5
    continue
  fi

  if [[ "$text" != "$last_text" ]]; then
    pos=0
    last_text=$text
  fi

  if ((${#text} <= max)); then
    emit "$icon $text"
    nap 0.25
    continue
  fi

  scroll="$text$sep"
  len=${#scroll}
  doubled="$scroll$scroll"
  emit "$icon ${doubled:pos:max}"
  pos=$(((pos + 1) % len))
  nap "$delay"
done
