"""Tests of aioarpapiemonte."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
REAL = FIXTURES / "real"
"""Unmodified files of Arpa Piemonte, downloaded on 2026-11-17 around 02:30 UTC.

The natural risks were downloaded on 2026-11-18 around 06:04 UTC: the widgets
of Pray (``widget_096050.json``) and Asti, in two alert zones
(``widget_005005.json``), the earthquakes, the heat waves of Torino (the last
bulletin of the season, of 2026-09-30) and the avalanche bulletins of EAWS of
2026-04-18 (``2026-04-18-IT-21.json``), the season being over.
"""

PRAY = "188"
"""Pray Sessera in the network: a hydrometer with all three thresholds."""
PRAY_SENSOR = "002105900"
"""Pray Sessera on the website: the ISTAT code of Pray before 1992 (002105)."""
PRAY_MUNICIPALITY = "096050"
"""The current ISTAT code of Pray, in the province of Biella."""


def real_bytes(name: str) -> bytes:
    """Return a real file of Arpa Piemonte, byte for byte."""
    return (REAL / name).read_bytes()


def real_json(name: str) -> object:
    """Return the decoded JSON of a real file of Arpa Piemonte."""
    data: object = json.loads(real_bytes(name))
    return data


def utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> dt.datetime:
    """Return an aware datetime in UTC."""
    return dt.datetime(year, month, day, hour, minute, tzinfo=dt.UTC)
