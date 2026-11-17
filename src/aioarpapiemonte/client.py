"""Async client of the real-time data of Arpa Piemonte."""

from __future__ import annotations

import asyncio
import json
import logging
from functools import partial
from http import HTTPStatus
from typing import TYPE_CHECKING, Self

import aiohttp

from ._http import ConditionalCache
from .const import DEFAULT_REQUEST_TIMEOUT, MAX_PAGES, REPOSITORY_URL
from .exceptions import (
    ArpaPiemonteConnectionError,
    ArpaPiemonteNotFoundError,
    ArpaPiemonteParseError,
)
from .models import Param, RealtimeData, RealtimeRecord
from .parsers import (
    parse_data_pie_page,
    parse_pie_anag,
    parse_sensors,
    parse_series,
    parse_status,
)
from .urls import (
    data_pie_url,
    pie_anag_url,
    sensors_url,
    series_url,
    status_url,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .models import ParamSeries, RealtimeStation, Sensor

_LOGGER = logging.getLogger(__name__)


class ArpaPiemonteClient:
    """Async client of the real-time data of the stations of Arpa Piemonte.

    Two sources, for the same stations and readings:

    - the files of the Arpa website (:meth:`get_sensors`, :meth:`get_series`):
      hourly readings with their validation, about 40 minutes after the hour;
    - the api_realtime (:meth:`get_realtime_stations`,
      :meth:`get_realtime_data`): every quantity of a station in one request,
      about 3 hours and 40 minutes after the hour.

    Pass the ``aiohttp.ClientSession`` of the application (it is never closed
    by the client), or use the client as an async context manager to let it
    manage its own session. The files of the website are asked whether they
    changed since the last answer (``If-None-Match``, ``If-Modified-Since``):
    when they did not, the client returns the object it returned before.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        *,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
        user_agent: str | None = None,
    ) -> None:
        """Initialize the client.

        ``request_timeout`` applies to each request, in seconds.
        ``user_agent`` names the application in the requests (default:
        aioarpapiemonte and its version).
        """
        self._session = session
        self._close_session = False
        self._request_timeout = request_timeout
        self._user_agent = user_agent or _default_user_agent()
        self._sensors: ConditionalCache[tuple[Sensor, ...]] = ConditionalCache()
        self._series: ConditionalCache[ParamSeries] = ConditionalCache()

    async def __aenter__(self) -> Self:
        """Enter the async context."""
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Exit the async context, closing the session owned by the client."""
        await self.close()

    async def close(self) -> None:
        """Close the session if the client created it."""
        if self._session is not None and self._close_session:
            await self._session.close()
            self._session = None
            self._close_session = False

    async def get_sensors(self) -> tuple[Sensor, ...]:
        """Return the stations of the Arpa website, with their quantities.

        The list is 617 KB, uncompressed, and written again every 15 minutes:
        read it to choose a station, not at every update.

        Raises :class:`ArpaPiemonteConnectionError` or
        :class:`ArpaPiemonteParseError`.
        """
        return await self._get(sensors_url(), parse_sensors, self._sensors)

    async def get_series(self, param: Param, station: str) -> ParamSeries:
        """Return the hourly readings of a quantity of a station.

        ``station`` is the identifier of the station on the website
        ("002105900", see :func:`aioarpapiemonte.sensor_id`). Raises
        ``ValueError`` for an identifier that is not 9 digits,
        :class:`ArpaPiemonteNotFoundError` when the station does not publish
        the quantity, :class:`ArpaPiemonteConnectionError` or
        :class:`ArpaPiemonteParseError`.
        """
        param = Param(param)
        url = series_url(param, station)
        return await self._get(
            url, partial(parse_series, param=param, station=station), self._series
        )

    async def get_realtime_status(self) -> str:
        """Return the status of the api_realtime ("healthy").

        Raises :class:`ArpaPiemonteConnectionError` or
        :class:`ArpaPiemonteParseError`.
        """
        return parse_status(await self._fetch_json(status_url()))

    async def get_realtime_stations(self) -> tuple[RealtimeStation, ...]:
        """Return the stations of Piedmont of the api_realtime.

        They give the identifier of each station on the website
        (``sensor_id``). Raises :class:`ArpaPiemonteConnectionError` or
        :class:`ArpaPiemonteParseError`.
        """
        data = await self._fetch_json(pie_anag_url())
        return await asyncio.to_thread(parse_pie_anag, data)

    async def get_realtime_data(self, station_code: str) -> RealtimeData:
        """Return the records of a station of the last 3 days, from the oldest.

        ``station_code`` is the code of the station in the network ("188").
        A station the api_realtime does not know has no records. Raises
        ``ValueError`` for a code that is not letters and digits,
        :class:`ArpaPiemonteConnectionError` or
        :class:`ArpaPiemonteParseError`.
        """
        data_pie_url(station_code)
        records: dict[object, RealtimeRecord] = {}
        page = 1
        while True:
            data = await self._fetch_json(data_pie_url(station_code, page))
            found, total_pages = parse_data_pie_page(data, station_code)
            records.update((record.time, record) for record in found)
            if page >= total_pages:
                break
            if page >= MAX_PAGES:
                msg = f"The records of {station_code} have more than {MAX_PAGES} pages"
                raise ArpaPiemonteParseError(msg)
            page += 1
        return RealtimeData(
            station_code,
            tuple(sorted(records.values(), key=lambda record: record.time)),
        )

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            # The website sets a cookie on every answer: keep none.
            self._session = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
            self._close_session = True
        return self._session

    async def _get[T](
        self, url: str, parse: Callable[[object], T], cache: ConditionalCache[T]
    ) -> T:
        """Return the file at a URL parsed, or the same object when unchanged."""
        body, headers = await self._request(url, cache.validators(url))
        if body is None:
            value = cache.get(url)
            if value is None:
                msg = f"HTTP status 304 fetching {url}, without a previous answer"
                raise ArpaPiemonteConnectionError(msg)
            return value
        value = await asyncio.to_thread(_decode, url, body, parse)
        cache.store(
            url,
            value,
            etag=headers.get(aiohttp.hdrs.ETAG),
            last_modified=headers.get(aiohttp.hdrs.LAST_MODIFIED),
        )
        return value

    async def _fetch_json(self, url: str) -> object:
        body, _ = await self._request(url, {})
        if body is None:
            msg = f"HTTP status 304 fetching {url}, without asking"
            raise ArpaPiemonteConnectionError(msg)
        return await asyncio.to_thread(_decode, url, body, _identity)

    async def _request(
        self, url: str, validators: dict[str, str]
    ) -> tuple[bytes | None, dict[str, str]]:
        """Return the body and headers at a URL; no body when unchanged (304)."""
        session = self._get_session()
        headers = {"User-Agent": self._user_agent, **validators}
        _LOGGER.debug("Fetching %s", url)
        try:
            async with (
                asyncio.timeout(self._request_timeout),
                session.get(url, headers=headers) as response,
            ):
                if response.status == HTTPStatus.NOT_MODIFIED:
                    return None, {}
                if response.status == HTTPStatus.NOT_FOUND:
                    msg = f"HTTP status 404 fetching {url}"
                    raise ArpaPiemonteNotFoundError(msg)
                response.raise_for_status()
                return await response.read(), dict(response.headers)
        except TimeoutError as err:
            msg = f"Timeout fetching {url}"
            raise ArpaPiemonteConnectionError(msg) from err
        except aiohttp.ClientResponseError as err:
            msg = f"HTTP status {err.status} fetching {url}"
            raise ArpaPiemonteConnectionError(msg) from err
        except (aiohttp.ClientError, OSError) as err:
            msg = f"Error fetching {url}: {err!r}"
            raise ArpaPiemonteConnectionError(msg) from err


def _default_user_agent() -> str:
    from . import __version__  # noqa: PLC0415 - the package imports this module

    return f"aioarpapiemonte/{__version__} (+{REPOSITORY_URL})"


def _identity(data: object) -> object:
    return data


def _decode[T](url: str, body: bytes, parse: Callable[[object], T]) -> T:
    """Decode and parse a body: run in a worker thread, it can be 617 KB.

    The api_realtime sends every answer as ``application/problem+json``: the
    content type is not looked at.
    """
    try:
        data: object = json.loads(body)
    except ValueError as err:
        msg = f"Invalid JSON from {url}"
        raise ArpaPiemonteParseError(msg) from err
    return parse(data)
