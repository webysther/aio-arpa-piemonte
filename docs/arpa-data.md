# Arpa Piemonte data: station files and api_realtime

The station data of Arpa Piemonte that aioarpapiemonte reads, or could read,
as studied for the [Arpa Piemonte](https://github.com/webysther/ha-arpa-piemonte) integration.
Measured on 2026-11-16 and 17. The numbers are measurements of those days:
measure again, politely, before relying on one. Anything not confirmed is
marked **Unverified**.

Related:
[the natural-risk products of Arpa](arpa-risk-products.md) (alerts, current
danger, floods, landslides, avalanches, heat, fire, earthquakes, open data),
[the files of Meteo 3R](https://github.com/webysther/aio-meteo3r/blob/main/docs/meteo3r-data.md),
and [the research notes of the integration](https://github.com/webysther/ha-arpa-piemonte/blob/main/docs/research.md).

## The files of the website

**Base:** `https://www.arpa.piemonte.it/rischi_naturali/data/tr/`. Measured
2026-11-17.

### `sensors.geojson`

- **Size and coverage:** 617,226 B, 381 stations, rewritten every 15 min.
- **Property keys:** area, basin, basin_surface, creation_date,
  date_start_publication, date_validity, locality, municipality, name, note,
  province, province_sign, quote, region, river, sensor, sensors, source,
  station_type, utm_x_wgs84, utm_y_wgs84, zero_hydrometric.
- **The station table** (`snippets_arpa_graphs/tabella_stazioni/`) is built
  from this file.

### Parameters per station

| Param | Stations | Meaning |
| --- | --- | --- |
| `pluv` | 288 | rain (10 min; hourly is `pluv_hh`) |
| `terma` | 278 | air temperature |
| `igro` | 146 | humidity |
| `idro` | 115 | level, with the thresholds in the file |
| `velr` / `vels` | 91 | gust / wind speed (m/s) |
| `velv` / `dirv` | 81 | wind speed (m/s) / direction |
| `nivo` | 78 | snow depth |
| `radd` | 64 | global solar radiation (W/m²) |
| `baro` | 45 | pressure (hPa) |

### Per-station files

- **`{param}/{id9}.geojson`:** 17,298–17,899 B, not compressed, ETag +
  Last-Modified, rewritten every 15 min.
  - Hourly, in UTC, timed at the end of the hour.
  - About 6–7 days (145–168 cells).
  - A validation code on each reading (`OK`, `VTA`…); null cells (`MMM`,
    `A…`) are dropped.
  - **Unverified:** whether the ETag changes every 15 min even without new
    data.
- **`{param}/sensors.json`:** a map from name to `id9`, 1–3 KB (velv 2,575 B,
  baro 1,396 B).
- **`pluv_hh/{id9}.geojson`:** hourly rain, 20,645 B, 173 cells (7–8 days,
  from 00:00Z seven days back).
  - Its hours match Meteo 3R `P_1H` at :00 exactly.
  - It is the file the Arpa charts use.
  - **The library cannot read it yet:** `Param("pluv_hh")` raises.
- **`nivo_v/{id9}.geojson`:** daily validated snow (`hs_validato`,
  `hn_validato`, each with a validity code), seasonal. Not in the library.
- **Wind:** the chart page loads `velv` (or `vels` if `velv` fails), plus
  `dirv` and `velr`, all in m/s (×3.6 for km/h).

### The chart page and the guide

- **Letters to files**, as the chart page maps them: I idro, T terma, H igro,
  N nivo (+nivo_v), P pluv_hh, V wind, B baro, R radd.
- **Thresholds:** drawn as flat lines from the `idro` file
  (`pre-alarm_threshold`, `guard_threshold`, `danger_threshold`).
- **Cumulative rain:** a running sum of `pluv_hh` from the first hour in the
  file, computed by the page.
- **Arpa guide** "Dati orari in tempo reale – Guida alla lettura dei dati",
  v1.0, 2024-10-03:
  - automatically validated data, which operators may still change;
  - all times in UTC;
  - hourly aggregates of the last 7 days, updated every 15 min;
  - rain in mm/h (sum within the hour, timed at its end; the cumulative over
    7 days is drawn as a line);
  - temperature, humidity, radiation (W/m²), wind speed (m/s), wind direction
    (° from N, clockwise) and pressure (hPa) are sampled at the hour;
  - gust (m/s) is the maximum within the hour, timed at its end;
  - level (m above the hydrometric zero) and snow depth (cm) are timed at the
    end of the interval.
- **Known issue:** the integration's device link opens `param=pluv`
  (10-minute rain), while the site uses `pluv_hh`.

## The api_realtime

- **Base:** `https://utility.arpa.piemonte.it/api_realtime/`.
- **`pie_anag`:** 171,132 B, 374 PIE stations.
  - The raw JSON has `province` and `province_code`, which the library does
    not parse yet.
  - `river_name` is `"-"` for 264 stations; the library's `_text` keeps it.
    **Bug:** the fallback labels read "Acceglio — - (Acceglio)".
- **`data_pie?station_code=&page_size=10000&page=N`:** about 24 KB, 74–76
  hourly records over about 3 days, ending about 3 h after Meteo 3R. No
  ETag, so never a `304`.
  - Fields: `air_temperature`, `humidity`, `cum_rain_1h/3h/6h/12h/24h`,
    `wind`, `wind_direction`, `gust_of_wind`, `gust_direction`,
    `snow_height`, `hydrometric_level`.
  - No pressure, no radiation, no thresholds, no validation codes.
- **`status`:** `{"status":"healthy","version":"1.1"}`.

### The service

- **What it is:** FastAPI, OpenAPI 3.1.0, "Arpa Piemonte API Realtime" v1.1.
- **Docs:** `/openapi.json`, `/docs` (Swagger) and `/redoc` answer 200; `/`
  and `/swagger` answer 404.
- **Access:** no authentication. The only network is PIE. It has no
  bulletins, alerts or forecasts.

### Endpoints

Source: quoted from `openapi.json`, 2026-11-17.

| Endpoint | What | Parameters |
| --- | --- | --- |
| `GET /status` | health check | — |
| `GET /data_pie` | station data of the last 3 days | `station_code`, `date_from`, `date_to`, `page` (1), `page_size` (100, max 10000) |
| `GET /pie_anag` | station registry | `station_code`, `name`, `station_type`, `municipality_code`, `municipality`, `basin`, `codice_istat_comune`, `progr_punto_com` |
| `GET /pie_neve` | validated snow height of the snow stations | `station_code`, `date_from`, `date_to` (no paging) |
| `GET /ggd` | heating and cooling degree days | `station_code`, `date_from`, `date_to`, `page`, `page_size` |

- **`pie_neve`:** a bare list, e.g.
  `{"id_network":"PIE","station_code":"001","date":"2026-11-10T08:00:00+01:00","validated_snow_height":10}`.
  On 2026-11-17 it had 560 records: 80 stations × 7 days, one value per day
  at 08:00 local. It is not in the library yet.
- **`ggd`:** 54,600 records since 2025-07-01. Not risk data.
- **Quirks:**
  - every response, 200s included, is `content-type:
    application/problem+json`;
  - no ETag, Last-Modified or Cache-Control;
  - validation errors come in the FastAPI style (`{"detail":[...]}`).

## Still unverified

- Whether the ETag of a station file changes every 15 minutes even without
  new data.
- `pluv_hh` (hourly rain, the file the Arpa charts use) and `nivo_v` (daily
  validated snow) are not read by the library yet: `Param("pluv_hh")`
  raises.
- How `pie_neve`, the website files `nivo_v` and Meteo 3R `HS_V` relate: all
  three are a daily snow depth.
- The 9-digit website id is built on the **old** ISTAT code of the
  municipality for at least Pray (`002105900`, while Pray is `096050`); it
  is likely so for every station of Biella (096) and VCO (103). See
  [the municipality widget](arpa-risk-products.md#municipality-widget).
