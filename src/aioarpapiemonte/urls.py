"""Addresses of the real-time data of Arpa Piemonte."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final
from urllib.parse import urlencode

from .const import DATA_PIE_PAGE_SIZE, GEOJSON_BASE_URL, REALTIME_BASE_URL

if TYPE_CHECKING:
    from .models import Param

_SENSOR_ID: Final = re.compile(r"\d{9}")
"""An identifier of a station on the Arpa website: 9 digits."""

_STATION_CODE: Final = re.compile(r"[0-9A-Za-z]+")
"""A code of a station in the network: letters and digits ("188", "S4059")."""

_MUNICIPALITY_CODE: Final = re.compile(r"\d{6}")
"""An ISTAT code of a municipality: 6 digits."""

_MAX_NUMBER: Final = 999
"""Highest number of a station in its municipality: it has 3 digits."""


def sensor_id(municipality_code: str, number: int) -> str:
    """Return the identifier of a station on the Arpa website.

    It is the ISTAT code of the municipality the station was set up in
    (``codice_istat_comune``, which can be an old code: Pray is 002105, from
    the province of Vercelli, while its code is now 096050) and the number of
    the station in it (``progr_punto_com``), in 3 digits: "002105900".

    Raises ``ValueError`` when they are not 6 digits and a number up to 999.
    """
    if not _MUNICIPALITY_CODE.fullmatch(municipality_code) or not (
        0 <= number <= _MAX_NUMBER
    ):
        msg = f"Invalid station: {municipality_code!r}, {number!r}"
        raise ValueError(msg)
    return f"{municipality_code}{number:03d}"


def sensors_url() -> str:
    """Return the URL of the list of the stations of the website."""
    return f"{GEOJSON_BASE_URL}sensors.geojson"


def series_url(param: Param, station: str) -> str:
    """Return the URL of the readings of a quantity of a station.

    Raises ``ValueError`` when the station is not 9 digits.
    """
    if not _SENSOR_ID.fullmatch(station):
        msg = f"Invalid station identifier: {station!r}"
        raise ValueError(msg)
    return f"{GEOJSON_BASE_URL}{param.value}/{station}.geojson"


def status_url() -> str:
    """Return the URL of the status of the api_realtime."""
    return f"{REALTIME_BASE_URL}status"


def pie_anag_url() -> str:
    """Return the URL of the stations of the api_realtime."""
    return f"{REALTIME_BASE_URL}pie_anag"


def data_pie_url(station_code: str, page: int = 1) -> str:
    """Return the URL of a page of the records of a station.

    Raises ``ValueError`` for a code that is not letters and digits.
    """
    if not _STATION_CODE.fullmatch(station_code):
        msg = f"Invalid station code: {station_code!r}"
        raise ValueError(msg)
    query = urlencode(
        {"station_code": station_code, "page_size": DATA_PIE_PAGE_SIZE, "page": page}
    )
    return f"{REALTIME_BASE_URL}data_pie?{query}"
