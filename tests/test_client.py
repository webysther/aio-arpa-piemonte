"""Tests of the client against the local server standing in for Arpa Piemonte."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
from typing import TYPE_CHECKING

import aiohttp
import pytest

from aioarpapiemonte import (
    MAX_PAGES,
    AlertLevel,
    ArpaPiemonteClient,
    ArpaPiemonteConnectionError,
    ArpaPiemonteNotFoundError,
    ArpaPiemonteParseError,
    HeatCity,
    Param,
    RealtimeField,
    __version__,
)
from aioarpapiemonte.urls import (
    avalanche_bulletin_url,
    data_pie_url,
    earthquakes_url,
    heat_forecast_url,
    municipality_alerts_url,
    pie_anag_url,
    sensors_url,
    series_url,
    status_url,
)

from . import PRAY, PRAY_MUNICIPALITY, PRAY_SENSOR, real_bytes, utc

if TYPE_CHECKING:
    from .server import FakeArpa

LEVEL_URL = series_url(Param.LEVEL, PRAY_SENSOR)
ETAG = '"4495-6606edcc552f8"'
LAST_MODIFIED = "Tue, 17 Nov 2026 01:32:06 GMT"
AVALANCHE_DAY = dt.date(2026, 4, 18)
"""The day of the real avalanche bulletins."""


def page(page_number: int, total_pages: int, *hours: int) -> bytes:
    """Return a page of records of Pray at the given hours of 2026-11-16 (UTC)."""
    data = [
        {
            "station_code": PRAY,
            "date": f"2026-11-16T{hour:02d}:00:00+00:00",
            "hydrometric_level": 0.8,
        }
        for hour in hours
    ]
    return json.dumps(
        {"page": page_number, "total_pages": total_pages, "data": data}
    ).encode()


async def test_level(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test the level of a station, with the User-Agent of the library."""
    arpa.add(LEVEL_URL, body=real_bytes("idro_002105900.geojson"))

    series = await client.get_series(Param.LEVEL, PRAY_SENSOR)

    assert series.thresholds is not None
    assert (
        arpa.requests[0]
        .headers["User-Agent"]
        .startswith(f"aioarpapiemonte/{__version__} (+https://")
    )


@pytest.mark.parametrize(
    ("etag", "last_modified"),
    [(ETAG, LAST_MODIFIED), (ETAG, None), (None, LAST_MODIFIED)],
)
async def test_unchanged_file_is_not_parsed_again(
    client: ArpaPiemonteClient,
    arpa: FakeArpa,
    etag: str | None,
    last_modified: str | None,
) -> None:
    """Test that an unchanged file returns the same object."""
    arpa.add(
        LEVEL_URL,
        body=real_bytes("idro_002105900.geojson"),
        etag=etag,
        last_modified=last_modified,
    )

    first = await client.get_series(Param.LEVEL, PRAY_SENSOR)
    second = await client.get_series(Param.LEVEL, PRAY_SENSOR)

    assert second is first
    assert arpa.requests[1].headers.get("If-None-Match") == etag
    assert arpa.requests[1].headers.get("If-Modified-Since") == last_modified


async def test_unexpected_not_modified(
    client: ArpaPiemonteClient, arpa: FakeArpa
) -> None:
    """Test that a 304 without a previous answer is an error."""
    arpa.add(LEVEL_URL, status=304)

    with pytest.raises(ArpaPiemonteConnectionError, match="without a previous"):
        await client.get_series(Param.LEVEL, PRAY_SENSOR)


async def test_quantity_not_published(client: ArpaPiemonteClient) -> None:
    """Test that a quantity the station does not publish is not found."""
    with pytest.raises(ArpaPiemonteNotFoundError):
        await client.get_series(Param.WIND_SPEED, PRAY_SENSOR)


async def test_sensors(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test the list of the stations of the website."""
    arpa.add(sensors_url(), body=real_bytes("sensors.geojson"))

    assert len(await client.get_sensors()) == 381


async def test_realtime(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test the stations, records and status of the api_realtime."""
    arpa.add(status_url(), body=real_bytes("status.json"))
    arpa.add(pie_anag_url(), body=real_bytes("pie_anag.json"))
    arpa.add(data_pie_url(PRAY), body=real_bytes("data_pie_188.json"))

    assert await client.get_realtime_status() == "healthy"
    assert len(await client.get_realtime_stations()) == 374
    data = await client.get_realtime_data(PRAY)

    assert len(data.records) == 74
    level = data.latest(RealtimeField.HYDROMETRIC_LEVEL)
    assert level is not None
    assert level.time == utc(2026, 11, 16, 23)


async def test_realtime_pages(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test that every page is read, records sorted and without repetition."""
    arpa.add(data_pie_url(PRAY, 1), body=page(1, 3, 5, 3))
    arpa.add(data_pie_url(PRAY, 2), body=page(2, 3, 4, 5))
    arpa.add(data_pie_url(PRAY, 3), body=page(3, 3, 6))

    data = await client.get_realtime_data(PRAY)

    assert [record.time.hour for record in data.records] == [3, 4, 5, 6]


async def test_realtime_without_end(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test that a server announcing pages without end is an error."""
    for number in range(1, MAX_PAGES + 1):
        arpa.add(data_pie_url(PRAY, number), body=page(number, 99, number))

    with pytest.raises(ArpaPiemonteParseError, match="more than"):
        await client.get_realtime_data(PRAY)

    assert len(arpa.requests) == MAX_PAGES


async def test_realtime_unknown_station(
    client: ArpaPiemonteClient, arpa: FakeArpa
) -> None:
    """Test that a station the api_realtime does not know has no records."""
    arpa.add(data_pie_url("999"), body=real_bytes("data_pie_999.json"))

    data = await client.get_realtime_data("999")

    assert data.records == ()


async def test_realtime_not_modified_without_asking(
    client: ArpaPiemonteClient, arpa: FakeArpa
) -> None:
    """Test that a 304 the client did not ask for is an error."""
    arpa.add(status_url(), status=304)

    with pytest.raises(ArpaPiemonteConnectionError, match="without asking"):
        await client.get_realtime_status()


@pytest.mark.parametrize(
    ("route", "error"),
    [
        ({"status": 500}, ArpaPiemonteConnectionError),
        ({"status": 403}, ArpaPiemonteConnectionError),
        ({"disconnect": True}, ArpaPiemonteConnectionError),
        ({"body": b"{not json"}, ArpaPiemonteParseError),
        ({"body": b"\xff\xfe"}, ArpaPiemonteParseError),
    ],
)
async def test_failures(
    client: ArpaPiemonteClient,
    arpa: FakeArpa,
    route: dict[str, object],
    error: type[Exception],
) -> None:
    """Test that every failure is an error of the library."""
    arpa.add(pie_anag_url(), **route)  # type: ignore[arg-type]

    with pytest.raises(error):
        await client.get_realtime_stations()


async def test_unreachable(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test that a host that cannot be resolved is a connection error."""
    arpa.unresolvable.add("utility.arpa.piemonte.it")

    with pytest.raises(ArpaPiemonteConnectionError) as error:
        await client.get_realtime_status()

    assert isinstance(error.value.__cause__, aiohttp.ClientConnectorError)


async def test_timeout(session: aiohttp.ClientSession, arpa: FakeArpa) -> None:
    """Test that a stalled answer is a connection error."""
    arpa.add(status_url(), before=arpa.hang)
    client = ArpaPiemonteClient(session, request_timeout=0.1)

    with pytest.raises(ArpaPiemonteConnectionError, match="Timeout"):
        await client.get_realtime_status()


async def test_cancellation_propagates(
    client: ArpaPiemonteClient, arpa: FakeArpa
) -> None:
    """Test that cancelling a request is not turned into an error."""
    started = asyncio.Event()

    async def hang() -> None:
        started.set()
        await arpa.hang()

    arpa.add(status_url(), before=hang)
    task = asyncio.create_task(client.get_realtime_status())
    await started.wait()

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


async def test_municipality_alerts(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test the alerts of a municipality, asked whether they changed."""
    arpa.add(
        municipality_alerts_url(PRAY_MUNICIPALITY),
        body=real_bytes("widget_096050.json"),
        etag='"9d4-66086a263fa3a"',
        last_modified="Wed, 18 Nov 2026 05:53:46 GMT",
    )

    alerts = await client.get_municipality_alerts(PRAY_MUNICIPALITY)

    assert alerts.alert is AlertLevel.GREEN
    assert await client.get_municipality_alerts(PRAY_MUNICIPALITY) is alerts
    assert arpa.requests[1].headers["If-None-Match"] == '"9d4-66086a263fa3a"'


async def test_earthquakes(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test the earthquakes of the last 30 days."""
    arpa.add(earthquakes_url(), body=real_bytes("sismica_tabella.json"))

    assert len(await client.get_earthquakes()) == 28


async def test_heat_forecast(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test the heat-wave bulletin of a city."""
    arpa.add(heat_forecast_url(HeatCity.TORINO), body=real_bytes("caldo_torino.json"))

    forecast = await client.get_heat_forecast(HeatCity.TORINO)

    assert forecast.city is HeatCity.TORINO
    assert len(forecast.days) == 3


async def test_avalanche_bulletin(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test the avalanche bulletins of a day, and none out of season."""
    arpa.add(
        avalanche_bulletin_url(AVALANCHE_DAY),
        body=real_bytes("2026-04-18-IT-21.json"),
    )

    bulletin = await client.get_avalanche_bulletin(AVALANCHE_DAY)

    assert len(bulletin.regions) == 14
    assert arpa.requests[0].url.startswith("https://static.avalanche.report/")
    with pytest.raises(ArpaPiemonteNotFoundError):
        await client.get_avalanche_bulletin(dt.date(2026, 11, 18))


async def test_past_avalanche_bulletins_are_not_kept(
    client: ArpaPiemonteClient, arpa: FakeArpa
) -> None:
    """Test that only the bulletins of the 2 latest days asked are kept."""
    days = [AVALANCHE_DAY - dt.timedelta(days=number) for number in (2, 1, 0)]
    for day in days:
        arpa.add(
            avalanche_bulletin_url(day),
            body=real_bytes("2026-04-18-IT-21.json"),
            etag=f'"{day}"',
        )
    for day in days:
        await client.get_avalanche_bulletin(day)

    await client.get_avalanche_bulletin(days[0])
    await client.get_avalanche_bulletin(days[2])

    assert "If-None-Match" not in arpa.requests[3].headers
    assert arpa.requests[4].headers["If-None-Match"] == f'"{days[2]}"'


async def test_micro_region(client: ArpaPiemonteClient, arpa: FakeArpa) -> None:
    """Test the micro-region of a position, without any request."""
    assert await client.get_micro_region(45.0786, 6.7036) == "IT-21-TO-03"
    assert await client.get_micro_region(45.0703, 7.6869) is None
    assert arpa.requests == []


async def test_invalid_identifiers_are_checked_before_any_request(
    client: ArpaPiemonteClient, arpa: FakeArpa
) -> None:
    """Test that invalid identifiers raise before any request."""
    with pytest.raises(ValueError, match="Invalid station"):
        await client.get_series(Param.LEVEL, "188")
    with pytest.raises(ValueError, match="Invalid station code"):
        await client.get_realtime_data("../188")
    with pytest.raises(ValueError, match="Invalid municipality code"):
        await client.get_municipality_alerts("96050")

    assert arpa.requests == []


async def test_custom_user_agent(
    session: aiohttp.ClientSession, arpa: FakeArpa
) -> None:
    """Test that the User-Agent of the application is sent."""
    arpa.add(status_url(), body=real_bytes("status.json"))

    await ArpaPiemonteClient(session, user_agent="MyApp/1.0").get_realtime_status()

    assert arpa.requests[0].headers["User-Agent"] == "MyApp/1.0"


async def test_own_session_is_closed(
    arpa: FakeArpa, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the session the client creates is closed, without cookies."""
    sessions: list[aiohttp.ClientSession] = []

    def session_factory(**kwargs: object) -> aiohttp.ClientSession:
        assert isinstance(kwargs["cookie_jar"], aiohttp.DummyCookieJar)
        sessions.append(arpa.client_session(**kwargs))
        return sessions[-1]

    monkeypatch.setattr(aiohttp, "ClientSession", session_factory)
    arpa.add(status_url(), body=real_bytes("status.json"))

    async with ArpaPiemonteClient() as client:
        await client.get_realtime_status()
        await client.get_realtime_status()

    assert len(sessions) == 1
    assert sessions[0].closed
    await client.close()


async def test_injected_session_is_not_closed(
    session: aiohttp.ClientSession, arpa: FakeArpa
) -> None:
    """Test that an injected session is left open."""
    arpa.add(status_url(), body=real_bytes("status.json"))

    async with ArpaPiemonteClient(session) as client:
        await client.get_realtime_status()

    assert not session.closed
