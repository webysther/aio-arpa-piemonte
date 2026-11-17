"""Async client for the real-time data of the stations of Arpa Piemonte.

Arpa Piemonte publishes the readings of its stations (river levels, rain,
temperature, humidity, wind, snow) in two places: the files read by the
station pages of its website, hourly with their validation, and the
documented api_realtime, a few hours later.

The data is by Arpa Piemonte, under CC BY 4.0: credit it with
:data:`ATTRIBUTION`. aioarpapiemonte is not affiliated with Arpa Piemonte.
"""

from .client import ArpaPiemonteClient
from .const import ATTRIBUTION, DEFAULT_REQUEST_TIMEOUT, PIEMONTE_NETWORK
from .exceptions import (
    ArpaPiemonteConnectionError,
    ArpaPiemonteError,
    ArpaPiemonteNotFoundError,
    ArpaPiemonteParseError,
)
from .models import (
    USABLE,
    LevelStatus,
    Param,
    ParamReading,
    ParamSeries,
    Reading,
    RealtimeData,
    RealtimeField,
    RealtimeRecord,
    RealtimeStation,
    Sensor,
    Thresholds,
    Validation,
    station_page_url,
)
from .urls import sensor_id

__all__ = [
    "ATTRIBUTION",
    "DEFAULT_REQUEST_TIMEOUT",
    "PIEMONTE_NETWORK",
    "USABLE",
    "ArpaPiemonteClient",
    "ArpaPiemonteConnectionError",
    "ArpaPiemonteError",
    "ArpaPiemonteNotFoundError",
    "ArpaPiemonteParseError",
    "LevelStatus",
    "Param",
    "ParamReading",
    "ParamSeries",
    "Reading",
    "RealtimeData",
    "RealtimeField",
    "RealtimeRecord",
    "RealtimeStation",
    "Sensor",
    "Thresholds",
    "Validation",
    "__version__",
    "sensor_id",
    "station_page_url",
]

__version__ = "0.1.0"
