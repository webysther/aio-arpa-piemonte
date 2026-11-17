"""Models of the real-time data of Arpa Piemonte.

Every model is a frozen dataclass of plain values and tuples: two downloads of
the same data compare equal.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Any, Final, Self

from .const import STATION_PAGE_URL

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping


class _NamedLevel(IntEnum):
    """Ordered level shown by its lower-case name: ``str(level) == "suspect"``."""

    def __str__(self) -> str:
        return self.name.lower()

    def __format__(self, format_spec: str) -> str:
        return format(str(self), format_spec)

    @property
    def code(self) -> int:
        """Return the numeric code of the value: its number."""
        return int(self)

    @classmethod
    def from_code(cls, code: int) -> Self | None:
        """Return the value of a numeric code; None when no value has it."""
        return next((member for member in cls if member.code == code), None)


class _Coded(StrEnum):
    """A value named by the text Arpa Piemonte uses, with a numeric code."""

    @property
    def code(self) -> int:
        """Return the numeric code of the value."""
        return _CODES[type(self)][self]

    @classmethod
    def from_code(cls, code: int) -> Self | None:
        """Return the value of a numeric code; None when no value has it."""
        return next((member for member in cls if member.code == code), None)


class Param(_Coded):
    """A quantity of the real-time files of the Arpa website, by its folder.

    Units are those the files state (``units_sym``).
    """

    LEVEL = "idro"
    """Water level, in m above the hydrometric zero, at the end of the hour."""
    RAIN_10_MIN = "pluv"
    """Rain, in mm: "Livello pioggia sui 10 minuti", as the files describe it.

    Not the rain of the hour: it was lower than the rain of the hour of the
    api_realtime in 5 of 73 hours, and equal in the others, mostly without
    rain (measured on 2026-11-17). For the rain of the hours, read
    ``RealtimeField.CUM_RAIN_1H`` and the others.
    """
    TEMPERATURE = "terma"
    """Air temperature, in °C, at the end of the hour."""
    HUMIDITY = "igro"
    """Relative humidity, in %, at the end of the hour."""
    PRESSURE = "baro"
    """Air pressure, in hPa."""
    SNOW_DEPTH = "nivo"
    """Snow depth, in cm."""
    RADIATION = "radd"
    """Global solar radiation, in W/m²."""
    WIND_SPEED = "velv"
    """Wind speed, in m/s."""
    WIND_SPEED_SECONDARY = "vels"
    """Wind speed of a second sensor, in m/s: the station page shows it when
    ``velv`` is missing."""
    GUST_SPEED = "velr"
    """Speed of the strongest gust of the hour, in m/s."""
    WIND_DIRECTION = "dirv"
    """Direction the wind comes from, in degrees."""

    @property
    def unit(self) -> str:
        """Return the unit of the quantity."""
        return PARAM_UNITS[self]


PARAM_CODES: Final[Mapping[Param, int]] = {
    Param.LEVEL: 1,
    Param.RAIN_10_MIN: 2,
    Param.TEMPERATURE: 3,
    Param.HUMIDITY: 4,
    Param.PRESSURE: 5,
    Param.SNOW_DEPTH: 6,
    Param.RADIATION: 7,
    Param.WIND_SPEED: 8,
    Param.WIND_SPEED_SECONDARY: 9,
    Param.GUST_SPEED: 10,
    Param.WIND_DIRECTION: 11,
}
"""Codes of the quantities of the files, proposed by aioarpapiemonte."""

PARAM_UNITS: Final[Mapping[Param, str]] = {
    Param.LEVEL: "m",
    Param.RAIN_10_MIN: "mm",
    Param.TEMPERATURE: "°C",
    Param.HUMIDITY: "%",
    Param.PRESSURE: "hPa",
    Param.SNOW_DEPTH: "cm",
    Param.RADIATION: "W/m²",
    Param.WIND_SPEED: "m/s",
    Param.WIND_SPEED_SECONDARY: "m/s",
    Param.GUST_SPEED: "m/s",
    Param.WIND_DIRECTION: "°",
}
"""Units of the quantities, as the files state them (measured on 2026-11-17)."""


class RealtimeField(_Coded):
    """A quantity of the records of the api_realtime, by its field."""

    AIR_TEMPERATURE = "air_temperature"
    """Air temperature, in °C."""
    HUMIDITY = "humidity"
    """Relative humidity, in %."""
    CUM_RAIN_1H = "cum_rain_1h"
    """Rain in the hour that ends at the time of the record, in mm."""
    CUM_RAIN_3H = "cum_rain_3h"
    """Rain in the 3 hours that end at the time of the record, in mm."""
    CUM_RAIN_6H = "cum_rain_6h"
    """Rain in the 6 hours that end at the time of the record, in mm."""
    CUM_RAIN_12H = "cum_rain_12h"
    """Rain in the 12 hours that end at the time of the record, in mm."""
    CUM_RAIN_24H = "cum_rain_24h"
    """Rain in the 24 hours that end at the time of the record, in mm."""
    WIND = "wind"
    """Wind speed, in km/h."""
    WIND_DIRECTION = "wind_direction"
    """Direction the wind comes from, in degrees."""
    GUST_OF_WIND = "gust_of_wind"
    """Speed of the strongest gust, in km/h."""
    GUST_DIRECTION = "gust_direction"
    """Direction the strongest gust comes from, in degrees."""
    SNOW_HEIGHT = "snow_height"
    """Snow depth, in cm."""
    HYDROMETRIC_LEVEL = "hydrometric_level"
    """Water level, in m above the hydrometric zero."""

    @property
    def unit(self) -> str:
        """Return the unit of the quantity."""
        return REALTIME_FIELD_UNITS[self]


REALTIME_FIELD_CODES: Final[Mapping[RealtimeField, int]] = {
    RealtimeField.AIR_TEMPERATURE: 1,
    RealtimeField.HUMIDITY: 2,
    RealtimeField.CUM_RAIN_1H: 3,
    RealtimeField.CUM_RAIN_3H: 4,
    RealtimeField.CUM_RAIN_6H: 5,
    RealtimeField.CUM_RAIN_12H: 6,
    RealtimeField.CUM_RAIN_24H: 7,
    RealtimeField.WIND: 8,
    RealtimeField.WIND_DIRECTION: 9,
    RealtimeField.GUST_OF_WIND: 10,
    RealtimeField.GUST_DIRECTION: 11,
    RealtimeField.SNOW_HEIGHT: 12,
    RealtimeField.HYDROMETRIC_LEVEL: 13,
}
"""Codes of the fields of the api_realtime, proposed by aioarpapiemonte."""

REALTIME_FIELD_UNITS: Final[Mapping[RealtimeField, str]] = {
    RealtimeField.AIR_TEMPERATURE: "°C",
    RealtimeField.HUMIDITY: "%",
    RealtimeField.CUM_RAIN_1H: "mm",
    RealtimeField.CUM_RAIN_3H: "mm",
    RealtimeField.CUM_RAIN_6H: "mm",
    RealtimeField.CUM_RAIN_12H: "mm",
    RealtimeField.CUM_RAIN_24H: "mm",
    RealtimeField.WIND: "km/h",
    RealtimeField.WIND_DIRECTION: "°",
    RealtimeField.GUST_OF_WIND: "km/h",
    RealtimeField.GUST_DIRECTION: "°",
    RealtimeField.SNOW_HEIGHT: "cm",
    RealtimeField.HYDROMETRIC_LEVEL: "m",
}
"""Units of the fields of the api_realtime, which states none.

Measured on 2026-11-17 against the files of the Arpa website, which state
theirs: level, temperature, humidity and snow are equal; wind and gust are 3.6
times the files in m/s (3.5 to 3.67, from the rounding), so in km/h.
"""

_CODES: Final[Mapping[type[_Coded], Mapping[Any, int]]] = {
    Param: PARAM_CODES,
    RealtimeField: REALTIME_FIELD_CODES,
}
"""The table of codes of each enum named by a text."""


class Validation(_NamedLevel):
    """The automatic validation of a reading of the files (``valid_type``).

    Arpa writes a code of three letters; its first letter gives the color of
    the station page: green, yellow, orange or red. Measured on 2026-11-17:
    OK; VTA, VIA, VIC, VSD; WTB, WSD; AIC, ASA; MMM. The A and M codes came
    without a value.
    """

    UNKNOWN = 0
    """A code aioarpapiemonte does not know."""
    OK = 1
    """Valid ("OK", green)."""
    TO_VERIFY = 2
    """To be verified (V..., yellow): the latest hours, often."""
    SUSPECT = 3
    """Suspect (W..., orange)."""
    INVALID = 4
    """Invalid (A..., red)."""
    MISSING = 5
    """Missing (M..., or no code: grey)."""

    @classmethod
    def of(cls, valid_type: str | None) -> Validation:
        """Return the validation of a ``valid_type``."""
        if not valid_type:
            return cls.MISSING
        return _VALIDATION_LETTERS.get(valid_type[0].upper(), cls.UNKNOWN)


_VALIDATION_LETTERS: Final[Mapping[str, Validation]] = {
    "O": Validation.OK,
    "V": Validation.TO_VERIFY,
    "W": Validation.SUSPECT,
    "A": Validation.INVALID,
    "M": Validation.MISSING,
}
"""Validation of each first letter of ``valid_type``, from the station page."""

USABLE: Final = frozenset(
    {Validation.OK, Validation.TO_VERIFY, Validation.SUSPECT, Validation.UNKNOWN}
)
"""The validations of a reading worth showing: all but invalid and missing.

A fast rise of a river can be suspect for the automatic validation while true:
it is shown, with its validation.
"""


class LevelStatus(_NamedLevel):
    """The water level against the thresholds of the station, ordered."""

    UNKNOWN = 0
    """The station has no thresholds."""
    NORMAL = 1
    """Below every threshold."""
    PRE_ALARM = 2
    """At or above the pre-alarm threshold."""
    GUARD = 3
    """At or above the guard threshold."""
    DANGER = 4
    """At or above the danger threshold."""


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Alert thresholds of a hydrometer, in metres above the hydrometric zero."""

    pre_alarm: float | None = None
    """Pre-alarm threshold."""
    guard: float | None = None
    """Guard threshold."""
    danger: float | None = None
    """Danger threshold."""

    def status(self, level: float) -> LevelStatus:
        """Return the highest threshold the level reaches.

        A missing threshold is skipped; without any, the status is UNKNOWN.
        """
        limits = (
            (LevelStatus.DANGER, self.danger),
            (LevelStatus.GUARD, self.guard),
            (LevelStatus.PRE_ALARM, self.pre_alarm),
        )
        known = [(status, limit) for status, limit in limits if limit is not None]
        if not known:
            return LevelStatus.UNKNOWN
        return next(
            (status for status, limit in known if level >= limit), LevelStatus.NORMAL
        )


@dataclass(frozen=True, slots=True)
class Reading:
    """A value measured at a time."""

    time: dt.datetime
    """Time of the measurement, in UTC."""
    value: float
    """The value, in the unit of its quantity."""


@dataclass(frozen=True, slots=True)
class Sensor:
    """A station of the Arpa website (``sensors.geojson``).

    Its identifier is the ISTAT code of its municipality when it was set up,
    which can be an old one, and its number in that municipality.
    """

    id: str
    """Identifier of the station on the website, 9 digits ("002105900")."""
    name: str
    """Name of the station."""
    latitude: float
    """Latitude, WGS84."""
    longitude: float
    """Longitude, WGS84."""
    altitude: float | None
    """Altitude, in metres."""
    params: frozenset[Param]
    """The quantities the station publishes."""
    municipality: str | None = None
    """Municipality of the station."""
    river: str | None = None
    """River a hydrometer measures."""
    basin: str | None = None
    """Basin of the station."""
    other_params: tuple[str, ...] = ()
    """Quantities of the station aioarpapiemonte does not know."""

    def page_url(self, param: Param | None = None) -> str:
        """Return the public page of the station; its first quantity by default."""
        if param is None:
            param = min(self.params, key=lambda item: item.code, default=Param.LEVEL)
        return station_page_url(self.id, param)


@dataclass(frozen=True, slots=True)
class ParamReading:
    """A reading of a file of the Arpa website."""

    time: dt.datetime
    """End of the hour of the reading, in UTC."""
    value: float
    """The value, in the unit of its quantity."""
    validation: Validation
    """The automatic validation of the reading."""
    valid_type: str | None = None
    """The validation code as published ("OK", "VTA")."""


@dataclass(frozen=True, slots=True)
class ParamSeries:
    """The hourly readings of a quantity of a station, about the last 6 days."""

    sensor_id: str
    """Identifier of the station on the website."""
    param: Param
    """The quantity."""
    name: str
    """Name of the station."""
    readings: tuple[ParamReading, ...]
    """The readings with a value, from the oldest."""
    river: str | None = None
    """River a hydrometer measures."""
    basin: str | None = None
    """Basin of the station."""
    hydrometric_zero: float | None = None
    """Altitude of the zero of the level, in metres."""
    thresholds: Thresholds | None = None
    """Alert thresholds of a hydrometer; None for the other quantities."""
    description: str | None = None
    """Description of the quantity by Arpa ("Livello idrometrico")."""

    def __iter__(self) -> Iterator[ParamReading]:
        """Iterate over the readings, from the oldest."""
        return iter(self.readings)

    def __len__(self) -> int:
        """Return the number of readings."""
        return len(self.readings)

    def latest(self, accept: Collection[Validation] = USABLE) -> ParamReading | None:
        """Return the newest reading whose validation is accepted."""
        return next(
            (
                reading
                for reading in reversed(self.readings)
                if reading.validation in accept
            ),
            None,
        )

    @property
    def page_url(self) -> str:
        """Return the public page of the station for this quantity."""
        return station_page_url(self.sensor_id, self.param)


@dataclass(frozen=True, slots=True)
class RealtimeStation:
    """A station of the api_realtime (``pie_anag``)."""

    station_code: str
    """Code of the station in the network, leading zeros kept ("188")."""
    name: str
    """Name of the station, in capitals."""
    latitude: float
    """Latitude, WGS84, rounded to 4 decimals."""
    longitude: float
    """Longitude, WGS84."""
    altitude: float | None
    """Altitude, in metres."""
    station_type: str
    """Letters of the sensors of the station ("IPT"), as published."""
    municipality: str
    """Municipality of the station."""
    municipality_code: str
    """ISTAT code of the municipality, the current one."""
    river: str | None
    """River a hydrometer measures."""
    basin: str | None
    """Basin of the station."""
    hydrometric_zero: float | None
    """Altitude of the zero of the level, in metres."""
    thresholds: Thresholds
    """Alert thresholds of the level; all None without hydrometer."""
    sensor_id: str | None
    """Identifier of the station on the Arpa website ("002105900").

    Made of ``codice_istat_comune`` and ``progr_punto_com``; None when either
    is missing. 373 of the 374 stations have a file on the website
    (measured on 2026-11-17).
    """


@dataclass(frozen=True, slots=True)
class RealtimeRecord:
    """The values of a station at an hour, from the api_realtime."""

    time: dt.datetime
    """Time of the record, in UTC."""
    values: tuple[tuple[RealtimeField, float], ...]
    """The fields with a value."""

    def get(self, field: RealtimeField) -> float | None:
        """Return the value of a field; None when it has none."""
        return next((value for key, value in self.values if key is field), None)


@dataclass(frozen=True, slots=True)
class RealtimeData:
    """The records of a station, about the last 3 days, from the oldest."""

    station_code: str
    """Code of the station in the network."""
    records: tuple[RealtimeRecord, ...]
    """The records, at strictly increasing times."""

    def latest(self, field: RealtimeField) -> Reading | None:
        """Return the newest value of a field; None when there is none."""
        for record in reversed(self.records):
            value = record.get(field)
            if value is not None:
                return Reading(record.time, value)
        return None


def station_page_url(sensor_id: str, param: Param) -> str:
    """Return the public page of a station on the Arpa website."""
    return STATION_PAGE_URL.format(sensor_id=sensor_id, param=param.value)
