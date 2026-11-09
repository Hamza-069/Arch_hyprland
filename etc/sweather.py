#!/usr/bin/env python3
"""
sweather - weather CLI that queries free, key-less sources in parallel,
compares them and shows the average, with a weather emoji.

Sweden / Nordic sources (used automatically when the place is in the Nordics):
  smhi       SMHI open data (Swedish met office)
  om_dmi     DMI HARMONIE, high-res Nordic model (via Open-Meteo)
  om_metno   MET Norway Nordic 1 km model (via Open-Meteo)

Worldwide sources (used everywhere):
  metno      MET Norway locationforecast
  openmeteo  Open-Meteo best-match
  om_icon    DWD ICON (via Open-Meteo)
  om_ecmwf   ECMWF IFS (via Open-Meteo)
  om_gfs     NOAA GFS (via Open-Meteo)
  om_gem     Environment Canada GEM (via Open-Meteo)
  om_meteofrance  Météo-France (via Open-Meteo)
  om_jma     JMA (via Open-Meteo)
  om_ukmo    UK Met Office (via Open-Meteo)
  om_geosphere   GeoSphere Austria (via Open-Meteo)
  wttr       wttr.in
  timer      7Timer! (civil product)
  visualcrossing  Visual Crossing Timeline (anonymous)

Usage:
  sweather.py                       # Stockholm, TUI
  sweather.py Malmö
  sweather.py "New York"
  sweather.py Paris --country FR
  sweather.py --lat 63.82 --lon 20.26
  sweather.py Kiruna --json [--compact]
  sweather.py Umeå --watch 60
  sweather.py --robust --method median
  sweather.py --sources smhi,metno,om_ecmwf,visualcrossing
  sweather.py --list-sources
"""
import argparse
import gzip
import json
import math
import os
import statistics
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib import error, parse, request

VERSION = "1.4.0"
UA = os.environ.get(
    "SWEATHER_UA", "sweather-cli/1.4 (personal use; set SWEATHER_UA to your contact)"
)

CITIES = {
    "stockholm": (59.3293, 18.0686), "goteborg": (57.7089, 11.9746),
    "malmo": (55.6050, 13.0038), "uppsala": (59.8586, 17.6389),
    "vasteras": (59.6099, 16.5448), "orebro": (59.2753, 15.2134),
    "linkoping": (58.4108, 15.6214), "helsingborg": (56.0465, 12.6945),
    "jonkoping": (57.7826, 14.1618), "norrkoping": (58.5877, 16.1924),
    "lund": (55.7047, 13.1910), "umea": (63.8258, 20.2630),
    "gavle": (60.6749, 17.1413), "sundsvall": (62.3908, 17.3069),
    "ostersund": (63.1792, 14.6357), "lulea": (65.5848, 22.1547),
    "kiruna": (67.8558, 20.2253), "visby": (57.6348, 18.2948),
    "karlstad": (59.3793, 13.5036), "kalmar": (56.6634, 16.3568),
}

NORDIC_BBOX = (54.0, 72.0, 3.0, 32.0)

METRICS = [
    ("temperature", "Temperature", "°C", 1, 1.5),
    ("feels_like", "Feels like", "°C", 1, 2.5),
    ("temp_max", "High", "°C", 1, 2.0),
    ("temp_min", "Low", "°C", 1, 2.0),
    ("humidity", "Humidity", "%", 0, 10),
    ("pressure", "Pressure", "hPa", 0, 3),
    ("wind_speed", "Wind", "m/s", 1, 2),
    ("wind_gust", "Gusts", "m/s", 1, 3),
    ("wind_dir", "Wind dir", "°", 0, 60),
    ("cloud_cover", "Cloud cover", "%", 0, 30),
    ("precipitation", "Precip", "mm/h", 1, 0.5),
]

# ----------------------------------------------------------------- helpers

def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or abs(v) >= 9999:
        return None
    return v


def fetch_json(url, timeout=10, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = request.Request(url, headers=h)
    with request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def closest(entries, key):
    now = datetime.now(timezone.utc)
    return min(entries, key=lambda e: abs((parse_time(e[key]) - now).total_seconds()))


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(deg):
    return COMPASS[int((deg % 360) / 22.5 + 0.5) % 16]


def in_nordic(lat, lon):
    a, b, c, d = NORDIC_BBOX
    return a <= lat <= b and c <= lon <= d


def calculate_feels_like(temp, wind_ms, humidity):
    """Calculate a more human-like 'feels like' temperature (°C)."""
    if temp is None:
        return None
    wind = wind_ms or 0.0
    rh = humidity if humidity is not None else 50.0

    if temp <= 10 and wind >= 1.3:
        wind_kmh = wind * 3.6
        wind_chill = (13.12 + 0.6215 * temp
                      - 11.37 * (wind_kmh ** 0.16)
                      + 0.3965 * temp * (wind_kmh ** 0.16))
        return round(wind_chill, 1)

    e = (rh / 100.0) * 6.105 * math.exp(17.27 * temp / (237.7 + temp))
    apparent = temp + 0.33 * e - 0.70 * wind - 4.00
    return round(apparent, 1)


# ----------------------------------------------------------------- sources

def src_smhi(lat, lon, timeout):
    base = "https://opendata-download-metfcst.smhi.se/api/category"
    try:
        url = f"{base}/snow1g/version/1/geotype/point/lon/{lon:.4f}/lat/{lat:.4f}/data.json"
        d = fetch_json(url, timeout)
        e = closest(d["timeSeries"], "time")["data"]
        return {
            "temperature": num(e.get("air_temperature")),
            "humidity": num(e.get("relative_humidity")),
            "pressure": num(e.get("air_pressure_at_mean_sea_level")),
            "wind_speed": num(e.get("wind_speed")),
            "wind_gust": num(e.get("wind_speed_of_gust")),
            "wind_dir": num(e.get("wind_from_direction")),
            "cloud_cover": num(e.get("cloud_area_fraction")),
            "precipitation": num(e.get("precipitation_amount_mean")),
        }
    except Exception:
        url = f"{base}/pmp3g/version/2/geotype/point/lon/{lon:.4f}/lat/{lat:.4f}/data.json"
        d = fetch_json(url, timeout)
        e = closest(d["timeSeries"], "validTime")
        p = {x["name"]: x["values"][0] for x in e["parameters"]}
        octas = num(p.get("tcc_mean"))
        return {
            "temperature": num(p.get("t")),
            "humidity": num(p.get("r")),
            "pressure": num(p.get("msl")),
            "wind_speed": num(p.get("ws")),
            "wind_gust": num(p.get("gust")),
            "wind_dir": num(p.get("wd")),
            "cloud_cover": None if octas is None else octas * 12.5,
            "precipitation": num(p.get("pmean")),
        }


def src_metno(lat, lon, timeout):
    url = (f"https://api.met.no/weatherapi/locationforecast/2.0/compact"
           f"?lat={lat:.4f}&lon={lon:.4f}")
    d = fetch_json(url, timeout)
    ts = closest(d["properties"]["timeseries"], "time")
    i = ts["data"]["instant"]["details"]
    n1 = ts["data"].get("next_1_hours", {}).get("details", {})
    return {
        "temperature": num(i.get("air_temperature")),
        "humidity": num(i.get("relative_humidity")),
        "pressure": num(i.get("air_pressure_at_sea_level")),
        "wind_speed": num(i.get("wind_speed")),
        "wind_gust": num(i.get("wind_speed_of_gust")),
        "wind_dir": num(i.get("wind_from_direction")),
        "cloud_cover": num(i.get("cloud_area_fraction")),
        "precipitation": num(n1.get("precipitation_amount")),
    }


def _open_meteo(lat, lon, timeout, model=None):
    cur = ("temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,"
           "weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,"
           "wind_gusts_10m")
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}"
           f"&current={cur}"
           f"&daily=temperature_2m_max,temperature_2m_min"
           f"&wind_speed_unit=ms&timezone=auto&forecast_days=1")
    if model:
        url += f"&models={model}"
    data = fetch_json(url, timeout)
    c = data["current"]
    daily = data.get("daily", {})
    return {
        "temperature": num(c.get("temperature_2m")),
        "feels_like": num(c.get("apparent_temperature")),
        "temp_max": num(daily.get("temperature_2m_max", [None])[0]),
        "temp_min": num(daily.get("temperature_2m_min", [None])[0]),
        "humidity": num(c.get("relative_humidity_2m")),
        "pressure": num(c.get("pressure_msl")),
        "wind_speed": num(c.get("wind_speed_10m")),
        "wind_gust": num(c.get("wind_gusts_10m")),
        "wind_dir": num(c.get("wind_direction_10m")),
        "cloud_cover": num(c.get("cloud_cover")),
        "precipitation": num(c.get("precipitation")),
        "weather_code": num(c.get("weather_code")),
    }


def _om(model):
    return lambda lat, lon, timeout: _open_meteo(lat, lon, timeout, model)


def src_wttr(lat, lon, timeout):
    d = fetch_json(f"https://wttr.in/{lat:.4f},{lon:.4f}?format=j1", timeout)
    c = d["current_condition"][0]
    kmh = num(c.get("windspeedKmph"))
    # wttr gives max/min in weather[0]
    day = (d.get("weather") or [{}])[0]
    return {
        "temperature": num(c.get("temp_C")),
        "feels_like": num(c.get("FeelsLikeC")),
        "temp_max": num(day.get("maxtempC")),
        "temp_min": num(day.get("mintempC")),
        "humidity": num(c.get("humidity")),
        "pressure": num(c.get("pressure")),
        "wind_speed": None if kmh is None else kmh / 3.6,
        "wind_dir": num(c.get("winddirDegree")),
        "cloud_cover": num(c.get("cloudcover")),
        "precipitation": num(c.get("precipMM")),
    }


def src_timer(lat, lon, timeout):
    url = (f"https://www.7timer.info/bin/civil.php?"
           f"lon={lon:.4f}&lat={lat:.4f}&unit=metric&output=json")
    d = fetch_json(url, timeout)
    series = d.get("dataseries") or []
    if not series:
        raise ValueError("empty 7Timer response")
    e = series[0]
    wind = e.get("wind10m") or {}
    speed = num(wind.get("speed"))
    speed_ms = None if speed is None else max(0.0, (speed - 1) * 2.5)
    cloud = num(e.get("cloudcover"))
    cloud_pct = None if cloud is None else min(100.0, max(0.0, (cloud - 1) * 12.5))
    return {
        "temperature": num(e.get("temp2m")),
        "humidity": num(e.get("rh")),
        "wind_speed": speed_ms,
        "wind_dir": num(wind.get("direction")),
        "cloud_cover": cloud_pct,
        "precipitation": num(e.get("prec_amount")) or num(e.get("precip")),
    }


def src_visualcrossing(lat, lon, timeout):
    url = (f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
           f"{lat:.4f},{lon:.4f}?unitGroup=metric&include=current,days&contentType=json")

    req = request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
    })

    with request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        d = json.loads(raw.decode("utf-8"))

    c = d.get("currentConditions") or {}
    day = (d.get("days") or [{}])[0]

    wind_kmh = num(c.get("windspeed"))
    gust_kmh = num(c.get("windgust"))

    return {
        "temperature": num(c.get("temp")),
        "feels_like": num(c.get("feelslike")),
        "temp_max": num(day.get("tempmax")),
        "temp_min": num(day.get("tempmin")),
        "humidity": num(c.get("humidity")),
        "pressure": num(c.get("pressure")),
        "wind_speed": None if wind_kmh is None else wind_kmh / 3.6,
        "wind_gust": None if gust_kmh is None else gust_kmh / 3.6,
        "wind_dir": num(c.get("winddir")),
        "cloud_cover": num(c.get("cloudcover")),
        "precipitation": num(c.get("precip")),
    }


SOURCES = {
    "smhi": (src_smhi, "SMHI", "SMHI", "nordic"),
    "om_dmi": (_om("dmi_seamless"), "DMI HARMONIE (via Open-Meteo)", "DMI", "nordic"),
    "om_metno": (_om("metno_seamless"), "MET Nordic (via Open-Meteo)", "MET-Nordic", "nordic"),
    "metno": (src_metno, "MET Norway", "MET.no", "world"),
    "openmeteo": (_om(None), "Open-Meteo best match", "Open-Meteo", "world"),
    "om_icon": (_om("icon_seamless"), "DWD ICON (via Open-Meteo)", "ICON", "world"),
    "om_ecmwf": (_om("ecmwf_ifs025"), "ECMWF IFS (via Open-Meteo)", "ECMWF", "world"),
    "om_gfs": (_om("gfs_seamless"), "NOAA GFS (via Open-Meteo)", "GFS", "world"),
    "om_gem": (_om("gem_seamless"), "Canada GEM (via Open-Meteo)", "GEM", "world"),
    "om_meteofrance": (_om("meteofrance_seamless"), "Météo-France (via Open-Meteo)", "Météo-Fr", "world"),
    "om_jma": (_om("jma_seamless"), "JMA (via Open-Meteo)", "JMA", "world"),
    "om_ukmo": (_om("ukmo_seamless"), "UK Met Office (via Open-Meteo)", "UKMO", "world"),
    "om_geosphere": (_om("geosphere_seamless"), "GeoSphere Austria (via Open-Meteo)", "GeoSphere", "world"),
    "wttr": (src_wttr, "wttr.in", "wttr.in", "world"),
    "timer": (src_timer, "7Timer! (civil)", "7Timer", "world"),
    "visualcrossing": (src_visualcrossing, "Visual Crossing", "VC", "world"),
}


def run_source(name, lat, lon, timeout):
    t0 = time.time()
    try:
        data = SOURCES[name][0](lat, lon, timeout)
        data = {k: v for k, v in data.items() if v is not None}
        if not any(k in data for k, *_ in METRICS):
            raise ValueError("no usable fields in response")
        return name, {"ok": True, "latency_ms": int((time.time() - t0) * 1000),
                      "data": data, "error": None}
    except (error.URLError, error.HTTPError, TimeoutError) as e:
        err = f"network: {getattr(e, 'reason', e)}"
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    return name, {"ok": False, "latency_ms": int((time.time() - t0) * 1000),
                  "data": {}, "error": err}


# ----------------------------------------------------------------- location

def geocode(name, timeout, country):
    url = ("https://geocoding-api.open-meteo.com/v1/search"
           f"?name={parse.quote(name)}&count=1&language=en")
    if country:
        url += f"&country_code={country.upper()}"
    r = fetch_json(url, timeout).get("results")
    return r[0] if r else None


def resolve_location(args):
    if args.lat is not None and args.lon is not None:
        return args.location or f"{args.lat:.3f},{args.lon:.3f}", args.lat, args.lon
    name = args.location or "Stockholm"
    key = norm(name)
    if key in CITIES and not args.country:
        lat, lon = CITIES[key]
        return name.title(), lat, lon
    try:
        if args.country:
            c = None if args.country.lower() in ("world", "any", "all") else args.country
            r = geocode(name, args.timeout, c)
        else:
            r = geocode(name, args.timeout, "SE") or geocode(name, args.timeout, None)
    except Exception as e:
        sys.exit(f"Could not geocode '{name}': {e}")
    if not r:
        sys.exit(f"No place found for '{name}'. Try --lat/--lon or --country.")
    label = r["name"] + (f", {r['admin1']}" if r.get("admin1") else "")
    if r.get("country_code") and r["country_code"] != "SE":
        label += f" ({r['country_code']})"
    return label, r["latitude"], r["longitude"]


# ----------------------------------------------------------------- sun + emoji

def sun_elevation(lat, lon, when):
    n = when.timetuple().tm_yday
    hour = when.hour + when.minute / 60 + when.second / 3600
    g = 2 * math.pi / 365 * (n - 1 + (hour - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    tst = hour * 60 + eqt + 4 * lon
    ha = math.radians(tst / 4 - 180)
    la = math.radians(lat)
    s = math.sin(la) * math.sin(decl) + math.cos(la) * math.cos(decl) * math.cos(ha)
    return math.degrees(math.asin(max(-1, min(1, s))))


def is_daytime(lat, lon, when=None):
    return sun_elevation(lat, lon, when or datetime.now(timezone.utc)) > -0.833


def classify(d, day=True):
    t, p = d.get("temperature"), d.get("precipitation")
    c, w = d.get("cloud_cover"), d.get("wind_speed")
    code = d.get("weather_code")
    code = None if code is None else int(code)

    if code is not None and 95 <= code <= 99:
        return "⛈️", "thunderstorm"
    if p is not None and p >= 0.1:
        if t is not None and t <= 1.0:
            return "🌨️", ("light snow" if p < 1 else "snow" if p < 2.5 else "heavy snow")
        if p < 2.5:
            if day and c is not None and c < 70:
                return "🌦️", "showers"
            return "🌧️", "light rain"
        if p < 7.6:
            return "🌧️", "rain"
        return "☔", "heavy rain"
    if code in (45, 48):
        return "🌫️", "fog"
    if w is not None and w >= 14:
        return "💨", "windy"
    if c is None:
        return "❔", "unknown"
    if day:
        for lim, e, txt in ((15, "☀️", "sunny"), (35, "🌤️", "mostly sunny"),
                            (60, "⛅", "partly cloudy"), (85, "🌥️", "mostly cloudy")):
            if c < lim:
                return e, txt
        return "☁️", "overcast"
    for lim, e, txt in ((20, "🌙", "clear night"), (45, "🌙", "mostly clear"),
                        (60, "☁️", "partly cloudy"), (85, "☁️", "mostly cloudy")):
        if c < lim:
            return e, txt
    return "☁️", "overcast"


# ----------------------------------------------------------------- statistics

def circ_stats(vals):
    s = sum(math.sin(math.radians(v)) for v in vals)
    c = sum(math.cos(math.radians(v)) for v in vals)
    r = min(math.hypot(s, c) / len(vals), 1.0)
    mean = math.degrees(math.atan2(s, c)) % 360
    sd = 0.0 if r >= 1 else (180.0 if r <= 1e-9 else math.degrees(math.sqrt(-2 * math.log(r))))
    return mean, sd


def ang_diff(a, b):
    return abs((a - b + 180) % 360 - 180)


def compute_stats(per_source, method="mean", robust=False):
    out = {}
    for key, _label, _unit, dec, floor in METRICS:
        pairs = [(s, d[key]) for s, d in per_source.items() if key in d]
        if not pairs:
            continue
        vals = [v for _, v in pairs]
        n = len(vals)
        outliers = []

        if key == "wind_dir":
            ref, _ = circ_stats(vals)
            if n >= 4:
                outliers = [s for s, v in pairs if ang_diff(v, ref) > floor]
            used = [v for s, v in pairs if not (robust and s in outliers)] or vals
            value, sd = circ_stats(used)
            entry = {"value": value, "mean": value, "median": value,
                     "min": None, "max": None, "stdev": sd}
        else:
            med = statistics.median(vals)
            if n >= 4:
                mad = statistics.median(abs(v - med) for v in vals) * 1.4826
                lim = max(3 * mad, floor)
                outliers = [s for s, v in pairs if abs(v - med) > lim]
            used = [v for s, v in pairs if not (robust and s in outliers)] or vals
            mean = statistics.fmean(used)
            median = statistics.median(used)
            entry = {
                "value": median if method == "median" else mean,
                "mean": mean, "median": median,
                "min": min(vals), "max": max(vals),
                "stdev": statistics.pstdev(used) if len(used) > 1 else 0.0,
            }
        entry.update({"n": n, "n_used": len(used), "outliers": outliers})
        entry = {k: (round(v, dec + 2) if isinstance(v, float) else v)
                 for k, v in entry.items()}
        out[key] = entry
    return out


def build_result(label, lat, lon, results, skipped, method, robust):
    day = is_daytime(lat, lon)
    per = {n: r["data"] for n, r in results.items() if r["ok"]}
    stats = compute_stats(per, method, robust)

    avg = {}
    for key, _l, _u, dec, _f in METRICS:
        if key in stats:
            avg[key] = round(stats[key]["value"], dec)

    # Keep the sources' averaged feels_like
    sources_feels = avg.get("feels_like")

    # Calculate human-oriented feels_like
    if "temperature" in avg:
        calculated_feels = calculate_feels_like(
            avg.get("temperature"),
            avg.get("wind_speed"),
            avg.get("humidity")
        )
        avg["feels_like"] = calculated_feels

    avg["feels_like_sources"] = sources_feels

    if "wind_dir" in avg:
        avg["wind_dir_compass"] = compass(avg["wind_dir"])

    codes = [int(d["weather_code"]) for d in per.values() if "weather_code" in d]
    probe = dict(avg)
    if codes:
        if sum(95 <= c <= 99 for c in codes) * 2 >= len(codes):
            probe["weather_code"] = 95
        elif sum(c in (45, 48) for c in codes) * 2 >= len(codes):
            probe["weather_code"] = 45
    emoji, cond = classify(probe, day)
    avg = {"emoji": emoji, "condition": cond, **avg}

    srcs = {}
    for n, r in results.items():
        e, t = classify(r["data"], day) if r["ok"] else (None, None)
        srcs[n] = {
            "name": SOURCES[n][1], "scope": SOURCES[n][3],
            "ok": r["ok"], "latency_ms": r["latency_ms"], "error": r["error"],
            "emoji": e, "condition": t,
            "data": {k: (int(v) if k == "weather_code" else round(v, 2))
                     for k, v in r["data"].items()},
        }

    return {
        "location": {"name": label, "latitude": round(lat, 4), "longitude": round(lon, 4)},
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "is_day": day,
        "method": method,
        "robust": robust,
        "units": {k: u for k, _l, u, _d, _f in METRICS},
        "sources_ok": len(per),
        "sources_total": len(results),
        "sources_skipped": skipped,
        "average": avg,
        "stats": stats,
        "sources": srcs,
    }


# ----------------------------------------------------------------- TUI

COLOR = False


def sty(text, *codes):
    if not COLOR or not codes:
        return text
    return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"


def dw(s):
    w = 0
    for i, ch in enumerate(s):
        if ch == "\ufe0f" or unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in "WF":
            w += 2
        elif i + 1 < len(s) and s[i + 1] == "\ufe0f":
            w += 2
        else:
            w += 1
    return w


def trunc(s, width):
    if dw(s) <= width:
        return s
    while s and dw(s) > width - 1:
        s = s[:-1]
    return s + "…"


def pad(s, width, align="right"):
    gap = max(0, width - dw(s))
    if align == "right":
        return " " * gap + s
    if align == "center":
        return " " * (gap // 2) + s + " " * (gap - gap // 2)
    return s + " " * gap


def cell(text, width, align="right", *codes):
    return sty(pad(trunc(text, width), width, align), *codes)


def temp_color(t):
    return "94" if t < 0 else "96" if t < 10 else "92" if t < 20 else "93" if t < 28 else "91"


def fmt(key, v, dec):
    if v is None:
        return "—"
    return f"{v:.0f}°" if key == "wind_dir" else f"{v:.{dec}f}"


COLS = [
    ("temperature", "Temp", "°C", 1),
    ("feels_like", "Feel", "°C", 1),
    ("temp_max", "High", "°C", 1),
    ("temp_min", "Low", "°C", 1),
    ("humidity", "Humid", "%", 0),
    ("pressure", "Press", "hPa", 0),
    ("wind_speed", "Wind", "m/s", 1),
    ("wind_gust", "Gust", "m/s", 1),
    ("wind_dir", "Dir", "", 0),
    ("cloud_cover", "Cloud", "%", 0),
    ("precipitation", "Rain", "mm/h", 1),
]


def render_tui(res, emoji=True):
    W_L, W_C, W_E = 11, 7, 4
    total = W_L + W_C * len(COLS) + (W_E if emoji else 0) + 2
    avg, stats, srcs = res["average"], res["stats"], res["sources"]
    L = []
    bar = sty("│", "90")

    def boxed(text, *codes):
        return bar + sty(pad(text, total - 2, "left"), *codes) + bar

    loc = res["location"]
    ns = "N" if loc["latitude"] >= 0 else "S"
    ew = "E" if loc["longitude"] >= 0 else "W"
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    sub = f"{abs(loc['latitude']):.2f}°{ns} {abs(loc['longitude']):.2f}°{ew} · {now}"
    lead = f" {avg.get('emoji', '')} " if emoji and avg.get("emoji") else " "
    L.append(sty("╭" + "─" * (total - 2) + "╮", "90"))
    L.append(boxed(f"{lead}{loc['name']}", "1", "97"))
    L.append(boxed(" " + sub, "90"))
    L.append(sty("╰" + "─" * (total - 2) + "╯", "90"))

    if "temperature" in avg:
        t = avg["temperature"]
        e = f"{avg['emoji']}  " if emoji else ""
        head = f" {e}" + sty(f" {t:.1f}°C ", "1", "30", "46" if t < 20 else "43")
        head += "  " + sty(avg["condition"], "1")

        calc = avg.get("feels_like")
        srcs_feel = avg.get("feels_like_sources")
        if calc is not None:
            head += f"  · feels {calc:.1f}°"
            if srcs_feel is not None and abs(calc - srcs_feel) > 0.3:
                head += f" (src {srcs_feel:.1f}°)"

        # Add high / low in the headline too
        if avg.get("temp_max") is not None and avg.get("temp_min") is not None:
            head += f"  · {avg['temp_max']:.0f}° / {avg['temp_min']:.0f}°"
        L += ["", head]

        bits = []
        if "wind_speed" in avg:
            wtxt = f"wind {avg['wind_speed']:.1f} m/s"
            if "wind_dir_compass" in avg:
                wtxt += f" {avg['wind_dir_compass']}"
            if "wind_gust" in avg:
                wtxt += f" (gusts {avg['wind_gust']:.1f})"
            bits.append(wtxt)
        if "humidity" in avg:
            bits.append(f"humidity {avg['humidity']:.0f}%")
        if "cloud_cover" in avg:
            bits.append(f"clouds {avg['cloud_cover']:.0f}%")
        if "precipitation" in avg:
            bits.append(f"rain {avg['precipitation']:.1f} mm/h")
        if "pressure" in avg:
            bits.append(f"{avg['pressure']:.0f} hPa")
        L.append("    " + sty("  ·  ".join(bits), "37"))
    L.append("")

    def head_row(items, codes):
        r = cell("", W_L, "left")
        for it in items:
            r += cell(it, W_C, "right", *codes)
        if emoji:
            r += cell("", W_E)
        return " " + r

    L.append(head_row([c[1] for c in COLS], ("1",)))
    L.append(head_row([c[2] for c in COLS], ("90",)))
    rule = " " + sty("─" * (total - 2), "90")
    L.append(rule)

    groups = [("nordic", "Sweden / Nordic"), ("world", "Worldwide")]
    for scope, title in groups:
        members = [n for n in srcs if srcs[n]["scope"] == scope]
        if not members:
            continue
        L.append(" " + sty(f"▸ {title}", "90"))
        for n in members:
            s = srcs[n]
            label = SOURCES[n][2]
            if not s["ok"]:
                msg = trunc(s["error"] or "failed", total - W_L - 3)
                L.append(" " + cell(label, W_L, "left", "2;31") + sty(msg, "2;31"))
                continue
            r = cell(label, W_L, "left")
            for key, _h, _u, dec in COLS:
                v = s["data"].get(key)
                if v is None:
                    r += cell("—", W_C, "right", "90")
                elif n in stats.get(key, {}).get("outliers", []):
                    r += cell(fmt(key, v, dec) + "!", W_C, "right", "93")
                else:
                    r += cell(fmt(key, v, dec), W_C, "right")
            if emoji:
                r += cell(s["emoji"] or "", W_E, "center")
            L.append(" " + r)
    L.append(rule)

    # AVERAGE row
    r = cell("AVERAGE", W_L, "left", "1", "96")
    for key, _h, _u, dec in COLS:
        if key not in avg:
            r += cell("—", W_C, "right", "90")
            continue
        v = avg[key]
        codes = ("1", temp_color(v)) if key in ("temperature", "feels_like", "temp_max", "temp_min") else ("1", "96")
        r += cell(fmt(key, v, dec), W_C, "right", *codes)
    if emoji:
        r += cell(avg.get("emoji", ""), W_E, "center")
    L.append(" " + r)

    # spread ± row
    r = cell("spread ±", W_L, "left", "90")
    for key, _h, _u, dec in COLS:
        st = stats.get(key)
        if not st or st["n"] < 2:
            r += cell("", W_C)
        else:
            d = 0 if key == "wind_dir" else max(dec, 1)
            r += cell(f"±{st['stdev']:.{d}f}", W_C, "right", "90")
    L.append(" " + r)
    L.append(rule)

    legend = (f" {res['sources_ok']}/{res['sources_total']} sources · "
              f"{res['method']}{' (robust)' if res['robust'] else ''} · "
              "± = std-dev · ! = outlier · feels = calculated")
    L.append(sty(legend, "90"))
    if res["sources_skipped"]:
        names = ", ".join(SOURCES[n][2] for n in res["sources_skipped"])
        L.append(sty(f" skipped (outside Nordic coverage): {names}", "90"))

    L.append("")
    line, width = " ", 1
    for n, s in srcs.items():
        if not s["ok"]:
            continue
        item = f"{sty('●', '92')} {SOURCES[n][2]} {s['latency_ms']}ms"
        iw = 2 + len(SOURCES[n][2]) + 1 + len(str(s["latency_ms"])) + 2 + 2
        if width + iw > total:
            L.append(sty(line, "90") if not COLOR else line)
            line, width = " ", 1
        line += item + "  "
        width += iw
    if line.strip():
        L.append(line)
    return "\n".join(L)


# ----------------------------------------------------------------- main

def collect(args, label, lat, lon):
    if args.sources:
        names, skipped = args.sources, []
    else:
        nordic = in_nordic(lat, lon)
        names = [n for n in SOURCES if SOURCES[n][3] == "world" or nordic]
        skipped = [n for n in SOURCES if n not in names]
    with ThreadPoolExecutor(max_workers=len(names)) as ex:
        futs = [ex.submit(run_source, n, lat, lon, args.timeout) for n in names]
        results = dict(f.result() for f in futs)
    results = {n: results[n] for n in names}
    return build_result(label, lat, lon, results, skipped, args.method, args.robust)


def main():
    global COLOR
    p = argparse.ArgumentParser(
        prog="sweather",
        description="Weather from free sources (Sweden/Nordic + worldwide), averaged.")
    p.add_argument("location", nargs="?", help="place name (default: Stockholm)")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--country", help="ISO country code for geocoding, or 'world'")
    p.add_argument("--json", action="store_true", help="raw JSON output")
    p.add_argument("--compact", action="store_true", help="single-line JSON")
    p.add_argument("--method", choices=["mean", "median"], default="mean")
    p.add_argument("--robust", action="store_true", help="exclude outlier sources from the average")
    p.add_argument("--sources", help=f"comma list from: {','.join(SOURCES)}")
    p.add_argument("--timeout", type=float, default=10.0)
    p.add_argument("--watch", type=int, metavar="SECONDS", help="refresh interval")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--no-emoji", action="store_true", help="hide emoji in the TUI")
    p.add_argument("--list-cities", action="store_true")
    p.add_argument("--list-sources", action="store_true")
    p.add_argument("--version", action="version", version=VERSION)
    args = p.parse_args()

    if args.list_cities:
        print("\n".join(sorted(c.title() for c in CITIES)))
        return
    if args.list_sources:
        for k, (_f, full, _s, scope) in SOURCES.items():
            print(f"{k:<16} {scope:<7} {full}")
        return
    if args.sources:
        args.sources = [s.strip() for s in args.sources.split(",") if s.strip()]
        bad = [s for s in args.sources if s not in SOURCES]
        if bad:
            p.error(f"unknown source(s): {', '.join(bad)}")
    if (args.lat is None) != (args.lon is None):
        p.error("--lat and --lon must be given together")

    COLOR = (sys.stdout.isatty() and not args.no_color and not os.environ.get("NO_COLOR")
             and not args.json)

    label, lat, lon = resolve_location(args)

    if args.json:
        res = collect(args, label, lat, lon)
        print(json.dumps(res, ensure_ascii=False, indent=None if args.compact else 2))
        sys.exit(0 if res["sources_ok"] else 1)

    res = None
    try:
        while True:
            res = collect(args, label, lat, lon)
            if args.watch and sys.stdout.isatty():
                sys.stdout.write("\x1b[2J\x1b[H")
            print(render_tui(res, emoji=not args.no_emoji))
            if not args.watch:
                break
            print(sty(f"\n refreshing every {args.watch}s · Ctrl-C to quit", "90"))
            time.sleep(args.watch)
    except KeyboardInterrupt:
        print()
    sys.exit(0 if res and res["sources_ok"] else 1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
