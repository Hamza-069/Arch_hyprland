#!/usr/bin/env bash
set -euo pipefail

# ── Dependencies ────────────────────────────────────────────────────────────
missing=()
for cmd in grim slurp tesseract wl-copy; do
  command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
done

has_notif=false
command -v notify-send >/dev/null 2>&1 && has_notif=true

# timeout is optional but recommended
has_timeout=false
command -v timeout >/dev/null 2>&1 && has_timeout=true

if ((${#missing[@]})); then
  $has_notif && notify-send -a "Text Extractor" "Missing dependencies: ${missing[*]}"
  exit 1
fi

# ── Paths ───────────────────────────────────────────────────────────────────
TMPDIR=$(mktemp -d)
SAVE_DIR="/tmp/text_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SAVE_DIR"
trap 'rm -rf "$TMPDIR"' EXIT

# ── Capture ─────────────────────────────────────────────────────────────────
geometry=$(slurp -d) || exit 0
grim -g "$geometry" "$TMPDIR/capture.png" || exit 0
cp "$TMPDIR/capture.png" "$SAVE_DIR/capture.png"

# ── Image preprocessing (optional) ──────────────────────────────────────────
IMCMD=""
if command -v magick >/dev/null 2>&1; then
  IMCMD="magick"
elif command -v convert >/dev/null 2>&1; then
  IMCMD="convert"
fi

declare -a variants=("capture") # always try the original

if [[ -n "$IMCMD" ]]; then
  if "$IMCMD" "$TMPDIR/capture.png" \
    -colorspace Gray \
    -contrast-stretch 1%x0.5% \
    -resize x1600 \
    -sharpen 0x0.5 \
    "$TMPDIR/processed.png" 2>/dev/null; then
    variants+=("processed")
    cp "$TMPDIR/processed.png" "$SAVE_DIR/processed.png"
  fi
fi

# ── OCR + scoring ───────────────────────────────────────────────────────────
OCR_TIMEOUT=60 # seconds per tesseract run

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

    # Run tesseract with timeout (falls back to no timeout if `timeout` is missing)
    if $has_timeout; then
      timeout "$OCR_TIMEOUT" tesseract "$TMPDIR/${variant}.png" "$out_base" \
        -l eng \
        --oem 1 \
        --psm "$psm" \
        tsv txt \
        2>/dev/null || continue
    else
      tesseract "$TMPDIR/${variant}.png" "$out_base" \
        -l eng \
        --oem 1 \
        --psm "$psm" \
        tsv txt \
        2>/dev/null || continue
    fi

    # strip blank lines
    text=$(sed '/^[[:space:]]*$/d' "$out_base.txt" 2>/dev/null) || continue
    [[ -z "$text" ]] && continue

    cp "$out_base.txt" "$SAVE_DIR/ocr_${variant}_${psm}.txt"

    # average word confidence (column 11)
    conf=$(awk -F'\t' '
      NR == 1 { next }
      $11 == "-1" || $11 == "" { next }
      { sum += $11; n++ }
      END { if (n > 0) printf "%.1f", sum/n; else print "0" }
    ' "$out_base.tsv" 2>/dev/null) || conf="0"

    chars=${#text}
    words=$(printf "%s" "$text" | wc -w)

    # alphanumeric ratio (quality heuristic)
    alnum_count=$(printf "%s" "$text" | tr -cd '[:alnum:]' | wc -c)
    if ((chars > 0)); then
      quality=$(awk "BEGIN { printf \"%.2f\", ($alnum_count / $chars) * 100 }")
    else
      quality=0
    fi

    # length bonus (log scale, capped)
    length_score=$(awk "BEGIN {
      ls = log($words + 1) / log(10) * 33
      if (ls > 100) ls = 100
      printf \"%.2f\", ls
    }")

    avg_word_len=0
    if ((words > 0)); then
      avg_word_len=$(awk "BEGIN { printf \"%.2f\", $chars / $words }")
    fi

    # noise penalties
    noise_penalty=0
    ((words < 3)) && noise_penalty=$((noise_penalty + 20))
    awk "BEGIN { exit !($quality < 40) }" && noise_penalty=$((noise_penalty + 20))
    awk "BEGIN { exit !($avg_word_len < 1.5) }" && noise_penalty=$((noise_penalty + 10))

    score=$(awk "BEGIN {
      s = ($conf * 0.50) + ($quality * 0.25) + ($length_score * 0.15) - $noise_penalty
      if (s < 0) s = 0
      printf \"%.2f\", s
    }")

    # decide whether this result is better
    is_better=$(awk -v cs="$score" -v bw="$best_words" -v cw="$words" \
      -v bc="$best_conf" -v cc="$conf" -v bs="$best_score" 'BEGIN {
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

# ── Result ──────────────────────────────────────────────────────────────────
if [[ -z "$best_text" ]]; then
  $has_notif && notify-send -a "Text Extractor" "No text found"
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
