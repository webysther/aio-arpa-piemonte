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

asyncio and aiohttp, fully typed (mypy strict). The files of the website are
asked whether they changed (`If-None-Match`, `If-Modified-Since`): an
unchanged file is neither downloaded nor parsed again.

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

### Errors

All errors derive from `ArpaPiemonteError`:

- `ArpaPiemonteConnectionError`: network error, error status, timeout;
- `ArpaPiemonteParseError`: an answer that is not the expected format;
- `ArpaPiemonteNotFoundError`: the file does not exist, for example a quantity
  the station does not publish.

Invalid identifiers raise `ValueError` before any request.

## Data source and attribution

The data is by **Arpa Piemonte**, under the
[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
license ([legal notes](https://www.arpa.piemonte.it/note-legali)). Credit it as
`ATTRIBUTION` does, "Fonte: Arpa Piemonte - www.arpa.piemonte.it", and link the
page of the station when you can (`ParamSeries.page_url`).

aioarpapiemonte is **not affiliated with or endorsed by Arpa Piemonte**. The
real-time data is validated automatically only, and may be corrected later by
Arpa Piemonte; it comes without any guarantee of availability. Do not rely on
it for safety: for alerts, follow the official bulletins and the civil
protection.

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
