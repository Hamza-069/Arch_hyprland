#!/usr/bin/env bash
set -o pipefail

out=$(sweather.py fittja --json --compact 2>/dev/null) || {
  echo '{"text":"󰖪","tooltip":"Weather unavailable","class":"error"}'
  exit 0
}

jq -c '
  def fmt1: if . == null then "—" else ((. * 10 | round) / 10 | tostring) end;
  def fmt0: if . == null then "—" else (. | round | tostring) end;

  # Pango-safe text
  def esc: tostring | gsub("&";"&amp;") | gsub("<";"&lt;") | gsub(">";"&gt;");

  # right-pad with spaces so columns line up in the monospace font
  def padr(n): . as $s | (n - ($s | length)) as $k
    | $s + (if $k > 0 then " " * $k else "" end);

  def dim(s): "<span foreground=\"#6c7086\">\(s)</span>";
  def lbl(s): "<span foreground=\"#a6adc8\">\(s | padr(9))</span>";

  # ±spread, omitted entirely when the stat is missing (e.g. one source)
  def spread(v; suffix): if v == null then "" else dim("±\(v | fmt1)\(suffix)") end;

  # one aligned row: label, bold value+unit padded, dim spread
  def row(name; value; unit; sd; sfx):
    lbl(name) + "<b>" + ((value + unit) | padr(10)) + "</b>" + spread(sd; sfx);

  . as $w |
  ($w.average // {}) as $a |
  ($w.stats // {}) as $s |

  (if $w.sources_ok == $w.sources_total then "#a6e3a1"
   elif ($w.sources_ok // 0) == 0 then "#f38ba8"
   else "#f9e2af" end) as $src_color |

  {
    text: "\($a.emoji // "🌡️")\($a.temperature | fmt0)°",

    tooltip: (
      "<span font_desc=\"JetBrainsMono Nerd Font 8\" foreground=\"#cdd6f4\">" +
      "<b><span foreground=\"#89b4fa\">\($w.location.name | esc)</span></b>\n" +
      "<span foreground=\"#a6adc8\">\($a.condition // "—" | esc)</span>\n\n" +

      row("Temp";     ($a.temperature | fmt1); "°C";   $s.temperature.stdev;   "°") + "\n" +
      lbl("") + dim("\($a.temp_min | fmt1)° … \($a.temp_max | fmt1)°") + "\n" +
      row("Feels";    ($a.feels_like  | fmt1); "°C";   $s.feels_like.stdev;    "°") + "\n" +
      row("Humidity"; ($a.humidity    | fmt0); "%";    $s.humidity.stdev;      "%") + "\n" +
      row("Pressure"; ($a.pressure    | fmt0); " hPa"; $s.pressure.stdev;      "")  + "\n" +
      row("Wind";     ($a.wind_speed  | fmt1); " m/s"; $s.wind_speed.stdev;    "")  +
        " " + dim($a.wind_dir_compass // "") + "\n" +
      row("Gust";     ($a.wind_gust   | fmt1); " m/s"; $s.wind_gust.stdev;     "")  + "\n" +
      row("Clouds";   ($a.cloud_cover | fmt0); "%";    $s.cloud_cover.stdev;   "%") + "\n" +
      row("Rain";     ($a.precipitation | fmt1); " mm"; $s.precipitation.stdev; "") + "\n\n" +

      "<span foreground=\"\($src_color)\">Sources \($w.sources_ok)/\($w.sources_total)</span>" +
      "</span>"
    ),

    class: (($a.condition // "unknown") | ascii_downcase
            | gsub("[^a-z0-9]+"; "-") | gsub("^-|-$"; ""))
  }
' <<<"$out"
