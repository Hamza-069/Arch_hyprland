#!/usr/bin/env bash

set -o pipefail

sweather.py fittja --json --compact | jq -c '
  def fmt1:
    if . == null then "—"
    else ((. * 10 | round) / 10 | tostring)
    end;

  def fmt0:
    if . == null then "—"
    else (. | round | tostring)
    end;

  . as $w |

  ($w.stats.temperature.stdev  | fmt1) as $temp_spread |
  ($w.stats.feels_like.stdev   | fmt1) as $feels_spread |
  ($w.stats.humidity.stdev     | fmt1) as $humidity_spread |
  ($w.stats.pressure.stdev     | fmt1) as $pressure_spread |
  ($w.stats.wind_speed.stdev   | fmt1) as $wind_spread |
  ($w.stats.wind_gust.stdev    | fmt1) as $gust_spread |
  ($w.stats.cloud_cover.stdev  | fmt1) as $cloud_spread |
  ($w.stats.precipitation.stdev| fmt1) as $rain_spread |

  {
    text: "\($w.average.emoji // "🌡️")\($w.average.temperature | fmt0)°",

    tooltip: (
      "<span font_desc=\"JetBrainsMono Nerd Font 8\" foreground=\"#cdd6f4\">" +
      "<b><span foreground=\"#89b4fa\">\($w.location.name)</span></b>\r" +
      "<span foreground=\"#a6adc8\">\($w.average.condition // "—")</span>\r\r" +

      "Temp      <b>\($w.average.temperature | fmt1)°C</b>  <span foreground=\"#6c7086\">±\($temp_spread)°</span>\r" +
      "Feels     <b>\($w.average.feels_like   | fmt1)°C</b>  <span foreground=\"#6c7086\">±\($feels_spread)°</span>\r" +
      "Humidity  <b>\($w.average.humidity     | fmt0)%</b>  <span foreground=\"#6c7086\">±\($humidity_spread)%</span>\r" +
      "Pressure  <b>\($w.average.pressure     | fmt0) hPa</b>  <span foreground=\"#6c7086\">±\($pressure_spread)</span>\r" +
      "Wind      <b>\($w.average.wind_speed   | fmt1) m/s</b>  <span foreground=\"#6c7086\">±\($wind_spread)</span>\r" +
      "Gust      <b>\($w.average.wind_gust    | fmt1) m/s</b>  <span foreground=\"#6c7086\">±\($gust_spread)</span>\r" +
      "Clouds    <b>\($w.average.cloud_cover  | fmt0)%</b>  <span foreground=\"#6c7086\">±\($cloud_spread)%</span>\r" +
      "Rain      <b>\($w.average.precipitation| fmt1) mm</b>  <span foreground=\"#6c7086\">±\($rain_spread)</span>\r\r" +

      "<span foreground=\"#a6e3a1\">Sources  \($w.sources_ok)/\($w.sources_total)</span>" +
      "</span>"
    ),

    class: (($w.average.condition // "unknown") | ascii_downcase | gsub(" "; "-"))
  }
'
