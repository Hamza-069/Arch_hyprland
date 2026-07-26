#!/usr/bin/env bash

set -euo pipefail

missing=()
for cmd in grim slurp tesseract wl-copy; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done

has_notif=true
command -v notify-send >/dev/null 2>&1 || has_notif=false

if ((${#missing[@]})); then
  if $has_notif; then
    notify-send -a "Text Extractor" "Missing dependencies: ${missing[*]}"
  fi
  exit 1
fi

TMPDIR=$(mktemp -d)
SAVE_DIR="/tmp/text$(date +'%-m_%d-%I:%M')"
mkdir -p "$SAVE_DIR"
trap 'rm -rf "$TMPDIR"' EXIT

geometry=$(slurp) || exit 0
grim -g "$geometry" "$TMPDIR/capture.png" || exit 0
cp "$TMPDIR/capture.png" "$SAVE_DIR/capture.png"

IMCMD=""
if command -v magick >/dev/null 2>&1; then
  IMCMD="magick"
elif command -v convert >/dev/null 2>&1; then
  IMCMD="convert"
fi

declare -a variants=()

if [[ -n "$IMCMD" ]]; then
  "$IMCMD" "$TMPDIR/capture.png" \
    -colorspace Gray \
    -contrast-stretch 1%x0.5% \
    -resize x1600 \
    -sharpen 0x0.5 \
    "$TMPDIR/processed.png"

  variants+=("processed")
  cp "$TMPDIR/processed.png" "$SAVE_DIR/processed.png"
fi

best_text=""
best_score=-1
best_conf=0
best_variant=""
best_psm=0
best_chars=0
best_words=0

for variant in "${variants[@]}"; do
  for psm in 6 11; do
    out_base="$TMPDIR/ocr_${variant}_${psm}"

    tesseract "$TMPDIR/${variant}.png" "$out_base" \
      -l eng \
      --oem 1 \
      --psm "$psm" \
      tsv txt \
      2>/dev/null || continue

    text=$(sed '/^[[:space:]]*$/d' "$out_base.txt" 2>/dev/null) || continue
    [[ -z "$text" ]] && continue

    cp "$out_base.txt" "$SAVE_DIR/ocr_${variant}_${psm}.txt"

    conf=$(awk -F'\t' '
      NR == 1 { next }
      $11 == "-1" || $11 == "" { next }
      { sum += $11; n++ }
      END { if (n > 0) printf "%.1f", sum/n; else print "0" }
    ' "$out_base.tsv" 2>/dev/null) || conf="0"

    chars=${#text}
    words=$(printf "%s" "$text" | wc -w)
    lines=$(printf "%s" "$text" | wc -l)

    alnum_count=$(printf "%s" "$text" | tr -cd '[:alnum:]' | wc -c)
    if ((chars > 0)); then
      quality=$(awk "BEGIN { printf \"%.2f\", ($alnum_count / $chars) * 100 }")
    else
      quality=0
    fi

    length_score=$(awk "BEGIN {
      ls = log($words + 1) / log(10) * 33
      if (ls > 100) ls = 100
      printf \"%.2f\", ls
    }")

    avg_word_len=0
    if ((words > 0)); then
      avg_word_len=$(awk "BEGIN { printf \"%.2f\", $chars / $words }")
    fi

    noise_penalty=0
    if ((words < 3)); then
      noise_penalty=20
    fi
    low_quality=$(awk "BEGIN { print ($quality < 40) }")
    if [[ "$low_quality" == "1" ]]; then
      noise_penalty=$((noise_penalty + 20))
    fi
    short_words=$(awk "BEGIN { print ($avg_word_len < 1.5) }")
    if [[ "$short_words" == "1" ]]; then
      noise_penalty=$((noise_penalty + 10))
    fi

    score=$(awk "BEGIN {
      s = ($conf * 0.50) + ($quality * 0.25) + ($length_score * 0.15) - $noise_penalty
      if (s < 0) s = 0
      printf \"%.2f\", s
    }")

    is_better=$(awk -v cs="$score" -v bw="$best_words" -v cw="$words" -v bc="$best_conf" -v cc="$conf" -v bs="$best_score" 'BEGIN {
      if (bs < 0) { print 1; exit }
      if (cw > bw * 1.5 && cc >= bc * 0.5) { print 1; exit }
      if (bw > cw * 1.5 && bc >= cc * 0.5) { print 0; exit }
      print (cs > bs)
    }')
    if [[ "$is_better" == "1" ]]; then
      best_score="$score"
      best_text="$text"
      best_conf="$conf"
      best_variant="$variant"
      best_psm="$psm"
      best_chars="$chars"
      best_words="$words"
    fi
  done
done

if [[ -z "$best_text" ]]; then
  if $has_notif; then
    notify-send -a "Text Extractor" "No text found"
  fi
  exit 0
fi

printf "%s" "$best_text" | wl-copy

conf_int=${best_conf%.*}
if $has_notif; then
  icon_args=()
  if [[ -f /usr/share/icons/breeze-dark/status/64/dialog-positive.svg ]]; then
    icon_args=(-i /usr/share/icons/breeze-dark/status/64/dialog-positive.svg)
  fi
  notify-send \
    -a "Text Extractor" \
    "${icon_args[@]+"${icon_args[@]}"}" \
    "Text copied to clipboard" \
    "${best_chars} characters · ${best_words} words · ${conf_int}% confidence
Source: ${best_variant} · PSM ${best_psm}"
fi
