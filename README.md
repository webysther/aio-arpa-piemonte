# aioarpapiemonte

Async Python client for the real-time data of the stations of
[Arpa Piemonte](https://www.arpa.piemonte.it): river levels, rain,
temperature, humidity, wind and snow of the 374 stations of the Piedmont
network, from its two official sources:

- the **files of the Arpa website**, read by its station pages: hourly
  readings with their automatic validation, about 40 minutes after the hour,
  for the last 6 days, with the thresholds of the hydrometers;
- the **[api_realtime](https://utility.arpa.piemonte.it/api_realtime/docs)**:
  every quantity of a station in one request, about 3 hours and 40 minutes
  after the hour, for the last 3 days.

It also reads the natural risks: the alerts of each municipality, the
earthquakes and the heat waves of the Arpa website, and the avalanche
bulletins of Piedmont, published by AINEVA through EAWS.

asyncio and aiohttp, fully typed (mypy strict). The files are asked whether
they changed (`If-None-Match`, `If-Modified-Since`): an unchanged file is
neither downloaded nor parsed again.

For the readings every 30 minutes of the Meteo 3R app of Arpa Piemonte, see
[aiometeo3r](https://github.com/webysther/aio-meteo3r).

## Installation

```bash
pip install aioarpapiemonte
```

Python 3.13 or newer.

## Usage

```python
import asyncio

from aioarpapiemonte import ArpaPiemonteClient, Param, RealtimeField


async def main() -> None:
    async with ArpaPiemonteClient() as client:
        # The website: hourly readings with their validation
        series = await client.get_series(Param.LEVEL, "002105900")  # Pray Sessera
        latest = series.latest()
        if latest is not None:
            status = series.thresholds.status(latest.value) if series.thresholds else None
            print(f"{series.name}: {latest.value} m at {latest.time:%H:%M} UTC,"
                  f" {latest.validation}, {status}")

        # The api_realtime: every quantity in one request, a few hours later
        data = await client.get_realtime_data("188")
        rain = data.latest(RealtimeField.CUM_RAIN_24H)
        if rain is not None:
            print(f"Rain in 24 h: {rain.value} mm at {rain.time:%H:%M} UTC")


asyncio.run(main())
```

```text
PRAY SESSERA: 0.86 m at 02:00 UTC, to_verify, normal
Rain in 24 h: 0.0 mm at 23:00 UTC
```

### Two identifiers

A station has a code in the network (`"188"`, the api_realtime and Meteo 3R)
and an identifier on the website (`"002105900"`). The website one is the ISTAT
code of the municipality when the station was set up, which can be an old
code, and the number of the station in it: it cannot be made from the current
ISTAT code. `get_realtime_stations()` gives both:

```python
import asyncio

from aioarpapiemonte import ArpaPiemonteClient


async def main() -> None:
    async with ArpaPiemonteClient() as client:
        stations = await client.get_realtime_stations()
    pray = next(s for s in stations if s.station_code == "188")
    print(f"{pray.name}: station {pray.station_code}, website {pray.sensor_id},"
          f" municipality {pray.municipality_code}")


asyncio.run(main())
```

```text
PRAY SESSERA: station 188, website 002105900, municipality 096050
```

### Natural risks

```python
import asyncio
import datetime as dt
from zoneinfo import ZoneInfo

from aioarpapiemonte import (
    MICRO_REGION_NAMES,
    ArpaPiemonteClient,
    ArpaPiemonteNotFoundError,
    HeatCity,
    RiskType,
)

PRAY = (45.6739, 8.22167)


async def main() -> None:
    today = dt.datetime.now(ZoneInfo("Europe/Rome")).date()
    tomorrow = today + dt.timedelta(days=1)
    async with ArpaPiemonteClient() as client:
        # The alerts of a municipality, by its current ISTAT code
        alerts = await client.get_municipality_alerts("096050")
        print(f"{alerts.name} ({', '.join(alerts.zones)}), bulletin {alerts.bulletin}")
        for risk in RiskType:
            print(f"  {risk}: today {alerts.level_on(risk, today)},"
                  f" tomorrow {alerts.level_on(risk, tomorrow)}")
        print(f"  danger now: {alerts.current_danger}, phase: {alerts.phase}")

        # The earthquakes of the last 30 days, within 100 km
        for quake in await client.get_earthquakes():
            if quake.distance_km(*PRAY) <= 100:
                print(f"M{quake.magnitude} {quake.district}, {quake.time:%Y-%m-%d}:"
                      f" {quake.distance_km(*PRAY):.0f} km")

        # The heat waves, in the capital of the province (Biella)
        city = HeatCity.capital_of(alerts.municipality_code) or HeatCity.nearest(*PRAY)
        forecast = await client.get_heat_forecast(city)
        heat = forecast.on(today)
        print(f"Heat in {city}: {heat.level if heat else 'no bulletin today'}")

        # The avalanches, in the micro-region of a position (Macugnaga)
        region = await client.get_micro_region(45.9686, 7.9672)
        print(f"{region}, {MICRO_REGION_NAMES[region]}")
        try:
            bulletin = await client.get_avalanche_bulletin(today)
        except ArpaPiemonteNotFoundError:
            print("  no avalanche bulletin: out of season")
        else:
            print(f"  avalanche danger: {bulletin.of_region(region).danger}")


asyncio.run(main())
```

```text
Pray (Piem-B), bulletin 334/2026
  idrogeologico: today green, tomorrow unknown
  idraulico: today green, tomorrow unknown
  temporali: today green, tomorrow unknown
  neve: today green, tomorrow unknown
  valanghe: today not_evaluated, tomorrow unknown
  danger now: green, phase: none
M1.1 Alpi Pennine, 2026-11-17: 60 km
M1.3 Alpi Pennine, 2026-11-11: 97 km
M1.4 Alpi Pennine, 2026-11-07: 94 km
Heat in biella: no bulletin today
IT-21-VB-01, Alpi Pennine di Confine
  no avalanche bulletin: out of season
```

The alert bulletin is issued around 13:00, for that day and the next: in the
morning, its first day is yesterday. `level_on(risk, date)` gives the level of
a date, and UNKNOWN when the bulletin does not cover it yet (tomorrow, above,
at 07:20); `level(risk, AlertDay.ISSUE_DAY)` gives a day of the bulletin as
published.

## Reference

### Client

`ArpaPiemonteClient(session=None, *, request_timeout=15.0, user_agent=None)`

Pass the `aiohttp.ClientSession` of your application: the client never closes
it. Without one, use the client as an async context manager; its own session
keeps no cookies (the website sets one on every answer).

| Method | Source | Returns |
| --- | --- | --- |
| `get_sensors()` | website, `sensors.geojson` (617 KB) | `Sensor` of each station, with the quantities it publishes |
| `get_series(param, station)` | website, `<param>/<station>.geojson` | `ParamSeries`: hourly readings, validation, thresholds |
| `get_realtime_stations()` | api_realtime, `pie_anag` | `RealtimeStation`, with `sensor_id` |
| `get_realtime_data(station_code)` | api_realtime, `data_pie` | `RealtimeData`: records of the last 3 days |
| `get_realtime_status()` | api_realtime, `status` | `"healthy"` |
| `get_municipality_alerts(municipality_code)` | website, `widget/comuni/<code>/index.json` | `MunicipalityAlerts`: each risk today and tomorrow, the danger now, the operational phase |
| `get_earthquakes()` | website, `data/sismica/sismica_tabella.json` | `Earthquake` of the last 30 days, newest first |
| `get_heat_forecast(city)` | website, `widget/caldo/<city>/index.json` | `HeatForecast`: 3 days, from 15 May to about 30 September |
| `get_avalanche_bulletin(day)` | EAWS, `static.avalanche.report` | `AvalancheBulletin`: danger and problems by micro-region, from December to May |
| `get_micro_region(latitude, longitude)` | shipped with the package | the micro-region of a position, or `None` |

`user_agent` names your application in the requests. The default is
`aioarpapiemonte/<version> (+<repository>)`; it is sent with each request, so
it replaces the one of a shared session.

### Quantities

| `Param` (website) | Unit | `RealtimeField` (api_realtime) | Unit |
| --- | --- | --- | --- |
| `LEVEL` (`idro`) | m | `HYDROMETRIC_LEVEL` | m |
| `TEMPERATURE` (`terma`) | °C | `AIR_TEMPERATURE` | °C |
| `HUMIDITY` (`igro`) | % | `HUMIDITY` | % |
| `RAIN_10_MIN` (`pluv`) | mm, see below | `CUM_RAIN_1H` ... `CUM_RAIN_24H` | mm |
| `WIND_SPEED` (`velv`), `WIND_SPEED_SECONDARY` (`vels`), `GUST_SPEED` (`velr`) | m/s | `WIND`, `GUST_OF_WIND` | km/h |
| `WIND_DIRECTION` (`dirv`) | ° | `WIND_DIRECTION`, `GUST_DIRECTION` | ° |
| `SNOW_DEPTH` (`nivo`) | cm | `SNOW_HEIGHT` | cm |
| `PRESSURE` (`baro`) | hPa | | |
| `RADIATION` (`radd`) | W/m² | | |

The rain of the website files is described by them as "Livello pioggia sui 10
minuti", and was lower than the rain of the hour of the api_realtime in 5 of
73 hours: it is not the rain of the hour. For it, read `CUM_RAIN_1H`.

### Validation

Each reading of the website has a `Validation`, from the first letter of its
code (`valid_type`), as the station pages color it: `OK` (green),
`TO_VERIFY` (V..., yellow: often the latest hours), `SUSPECT` (W..., orange),
`INVALID` (A..., red), `MISSING` (M... or none, grey). `ParamSeries.latest()`
returns the newest reading that is not invalid nor missing: a fast rise of a
river can be suspect while true.

### Natural risks

- **Alerts** (`MunicipalityAlerts`): the level of each `RiskType`
  (`HYDROGEOLOGICAL`, `HYDRAULIC`, `THUNDERSTORMS`, `SNOW`, `AVALANCHES`) on
  each `AlertDay` of the bulletin, or on a date (`level_on`, `highest_on`);
  `alert`, the highest of the municipality (the bell of the widget);
  `current_danger`, assessed from the rain and the rivers measured; `phase`,
  the operational phase the municipality declared (`OperationalPhase`: `NONE`,
  `ATTENTION`, `PRE_ALARM`, `ALARM`); the `bulletin` number, its `issued` and
  `next_update` times, and the alert `zones` ("Piem-B"; a few municipalities
  are in two). An `AlertLevel` is `UNKNOWN`, `NOT_EVALUATED` (white: the
  avalanches out of season), `GREEN`, `YELLOW`, `ORANGE` or `RED`: they
  compare, and `is_alert` from yellow. The widget uses the current ISTAT code
  of the municipality, as the api_realtime gives it.
- **Earthquakes** (`Earthquake`): time in UTC, epicentre, depth, magnitude
  (local magnitude, ML), whether a seismologist `reviewed` it, and
  `distance_km(latitude, longitude)`. The list covers about 6 to 10° E and
  43.5 to 47° N.
- **Heat waves** (`HeatForecast`): the 8 provincial capitals (`HeatCity`,
  with `capital_of(municipality_code)` and `nearest(latitude, longitude)`),
  3 days each, with the `HeatLevel` of bioclimatic discomfort (`GREEN` to
  `RED`, the levels 0 to 3 of Arpa: the 75th, 90th and 95th percentiles of
  the apparent temperature), temperatures and consecutive hot days. Out of
  season the file keeps the last bulletin: `on(today)` is `None`.
- **Avalanches** (`AvalancheBulletin`): the bulletin of each micro-region
  (`of_region(region_id)`, a `RegionBulletin`), with its `danger` (the
  highest of its `ratings`, an `AvalancheDanger` from `LOW` to `VERY_HIGH`,
  `scale` 1 to 5), its ratings by elevation and time of day, its avalanche
  `problems` and its `tendency`. Out of season, `get_avalanche_bulletin`
  raises `ArpaPiemonteNotFoundError`. The 14 micro-regions of Piedmont cover
  its mountains, not its plains and hills: Torino and Pray are in none.
  `micro_region_at(latitude, longitude)` is the blocking form of
  `get_micro_region`, and `MICRO_REGION_NAMES` names them.

### Errors

All errors derive from `ArpaPiemonteError`:

- `ArpaPiemonteConnectionError`: network error, error status, timeout;
- `ArpaPiemonteParseError`: an answer that is not the expected format;
- `ArpaPiemonteNotFoundError`: the file does not exist, for example a quantity
  the station does not publish, or an avalanche bulletin out of season.

Invalid identifiers raise `ValueError` before any request.

## Data source and attribution

The data is by **Arpa Piemonte**, under the
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
license ([legal notes](https://www.arpa.piemonte.it/note-legali)). Credit it as
`ATTRIBUTION` does, "Fonte: Arpa Piemonte - www.arpa.piemonte.it", and link the
page of the station when you can (`ParamSeries.page_url`).

The widgets of the alerts and of the heat waves ask to cite the source and to
keep the layout of the widgets of Arpa; the widget of a municipality, unless
only its bell, the highest alert, is used (`nota_implementazione_widget`).

The avalanche bulletins are by **AINEVA** ("AINEVA Piemonte"), published in
the format of EAWS at [avalanche.report](https://avalanche.report); their
licence is not stated. Credit them as `AVALANCHE_ATTRIBUTION` does. The
micro-regions and their names, shipped with the package, are by
[EAWS](https://gitlab.com/eaws/eaws-regions), under CC0.

aioarpapiemonte is **not affiliated with or endorsed by Arpa Piemonte, AINEVA
or EAWS**. The real-time data is validated automatically only, and may be
corrected later by Arpa Piemonte; it comes without any guarantee of
availability. Do not rely on it for safety: for alerts, follow the official
bulletins and the civil protection.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install --editable . --group dev   # pip >= 25.1
ruff format --check . && ruff check .
mypy
pytest --cov
```

The tests never reach Arpa Piemonte: a local HTTPS server answers for its hosts
(`tests/server.py`), with real files in `tests/fixtures/real`.

## License

MIT, see [LICENSE](https://github.com/webysther/aio-arpa-piemonte/blob/main/LICENSE).
