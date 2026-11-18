"""Async client for the data of Arpa Piemonte: its stations and natural risks.

Arpa Piemonte publishes the readings of its stations (river levels, rain,
temperature, humidity, wind, snow) in two places: the files read by the
station pages of its website, hourly with their validation, and the
documented api_realtime, a few hours later. Its website also publishes the
alerts of each municipality, the earthquakes and the heat waves; AINEVA
publishes the avalanche bulletins of Piedmont through EAWS.

The data is by Arpa Piemonte, under CC BY 4.0: credit it with
:data:`ATTRIBUTION`, and the avalanche bulletins with
:data:`AVALANCHE_ATTRIBUTION`. aioarpapiemonte is not affiliated with Arpa
Piemonte, AINEVA or EAWS.
"""

from .client import ArpaPiemonteClient
from .const import (
    ATTRIBUTION,
    AVALANCHE_ATTRIBUTION,
    DEFAULT_REQUEST_TIMEOUT,
    MAX_PAGES,
    PIEMONTE_EAWS_REGION,
    PIEMONTE_NETWORK,
)
from .exceptions import (
    ArpaPiemonteConnectionError,
    ArpaPiemonteError,
    ArpaPiemonteNotFoundError,
    ArpaPiemonteParseError,
)
from .geo import (
    MICRO_REGION_NAMES,
    MicroRegion,
    distance_km,
    micro_region_at,
    micro_regions,
)
from .models import (
    USABLE,
    AlertDay,
    AlertLevel,
    AvalancheBulletin,
    AvalancheDanger,
    AvalancheProblem,
    DangerRating,
    Earthquake,
    HeatCity,
    HeatDay,
    HeatForecast,
    HeatLevel,
    LevelStatus,
    MunicipalityAlerts,
    OperationalPhase,
    Param,
    ParamReading,
    ParamSeries,
    Reading,
    RealtimeData,
    RealtimeField,
    RealtimeRecord,
    RealtimeStation,
    RegionBulletin,
    RiskLevel,
    RiskType,
    Sensor,
    Thresholds,
    Validation,
    station_page_url,
)
from .urls import sensor_id

__all__ = [
    "ATTRIBUTION",
    "AVALANCHE_ATTRIBUTION",
    "DEFAULT_REQUEST_TIMEOUT",
    "MAX_PAGES",
    "MICRO_REGION_NAMES",
    "PIEMONTE_EAWS_REGION",
    "PIEMONTE_NETWORK",
    "USABLE",
    "AlertDay",
    "AlertLevel",
    "ArpaPiemonteClient",
    "ArpaPiemonteConnectionError",
    "ArpaPiemonteError",
    "ArpaPiemonteNotFoundError",
    "ArpaPiemonteParseError",
    "AvalancheBulletin",
    "AvalancheDanger",
    "AvalancheProblem",
    "DangerRating",
    "Earthquake",
    "HeatCity",
    "HeatDay",
    "HeatForecast",
    "HeatLevel",
    "LevelStatus",
    "MicroRegion",
    "MunicipalityAlerts",
    "OperationalPhase",
    "Param",
    "ParamReading",
    "ParamSeries",
    "Reading",
    "RealtimeData",
    "RealtimeField",
    "RealtimeRecord",
    "RealtimeStation",
    "RegionBulletin",
    "RiskLevel",
    "RiskType",
    "Sensor",
    "Thresholds",
    "Validation",
    "__version__",
    "distance_km",
    "micro_region_at",
    "micro_regions",
    "sensor_id",
    "station_page_url",
]

__version__ = "0.2.0"
