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
from .geo import distance_km

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


class RiskType(_Coded):
    """A risk of the alert bulletin, by the word the municipality widget writes."""

    HYDROGEOLOGICAL = "idrogeologico"
    """Landslides and floods of the small basins (rischio idrogeologico)."""
    HYDRAULIC = "idraulico"
    """Floods of the main rivers (rischio idraulico)."""
    THUNDERSTORMS = "temporali"
    """Thunderstorms (rischio temporali)."""
    SNOW = "neve"
    """Snow (rischio neve)."""
    AVALANCHES = "valanghe"
    """Avalanches (rischio valanghe): not evaluated out of season."""


RISK_TYPE_CODES: Final[Mapping[RiskType, int]] = {
    RiskType.HYDROGEOLOGICAL: 1,
    RiskType.HYDRAULIC: 2,
    RiskType.THUNDERSTORMS: 3,
    RiskType.SNOW: 4,
    RiskType.AVALANCHES: 5,
}
"""Codes of the risks, proposed by aioarpapiemonte."""


class HeatCity(_Coded):
    """A city of the heat-wave bulletin, a provincial capital, by its file name."""

    ALESSANDRIA = "alessandria"
    ASTI = "asti"
    BIELLA = "biella"
    CUNEO = "cuneo"
    NOVARA = "novara"
    TORINO = "torino"
    VERBANIA = "verbania"
    VERCELLI = "vercelli"

    @property
    def municipality_code(self) -> str:
        """Return the ISTAT code of the city ("001272")."""
        return _HEAT_CITIES[self][0]

    @property
    def province_code(self) -> str:
        """Return the ISTAT code of the province of the city, its first 3 digits."""
        return self.municipality_code[:3]

    @property
    def latitude(self) -> float:
        """Return the latitude of the city, WGS84."""
        return _HEAT_CITIES[self][1]

    @property
    def longitude(self) -> float:
        """Return the longitude of the city, WGS84."""
        return _HEAT_CITIES[self][2]

    @classmethod
    def capital_of(cls, municipality_code: str) -> HeatCity | None:
        """Return the capital of the province of a municipality, by its ISTAT code.

        None outside the provinces of Piedmont: some stations of the network
        are in the province of Pavia (018).
        """
        return next(
            (city for city in cls if city.province_code == municipality_code[:3]),
            None,
        )

    @classmethod
    def nearest(cls, latitude: float, longitude: float) -> HeatCity:
        """Return the city nearest to a position."""
        return min(
            cls,
            key=lambda city: distance_km(
                latitude, longitude, city.latitude, city.longitude
            ),
        )


HEAT_CITY_CODES: Final[Mapping[HeatCity, int]] = {
    HeatCity.ALESSANDRIA: 1,
    HeatCity.ASTI: 2,
    HeatCity.BIELLA: 3,
    HeatCity.CUNEO: 4,
    HeatCity.NOVARA: 5,
    HeatCity.TORINO: 6,
    HeatCity.VERBANIA: 7,
    HeatCity.VERCELLI: 8,
}
"""Codes of the cities of the heat-wave bulletin, proposed by aioarpapiemonte."""

_HEAT_CITIES: Final[Mapping[HeatCity, tuple[str, float, float]]] = {
    HeatCity.ALESSANDRIA: ("006003", 44.9191, 8.6504),
    HeatCity.ASTI: ("005005", 44.9092, 8.2121),
    HeatCity.BIELLA: ("096004", 45.5926, 8.0188),
    HeatCity.CUNEO: ("004078", 44.3790, 7.5372),
    HeatCity.NOVARA: ("003106", 45.4366, 8.6124),
    HeatCity.TORINO: ("001272", 45.0764, 7.6821),
    HeatCity.VERBANIA: ("103072", 45.9470, 8.5352),
    HeatCity.VERCELLI: ("002158", 45.3244, 8.3894),
}
"""The ISTAT code and the position of each city: the mean of the stations of
the Piedmont network in the city, as the Meteo 3R list gave them on 2026-11-17
(Torino 8, Vercelli 1, the others 2 or 3)."""

_CODES: Final[Mapping[type[_Coded], Mapping[Any, int]]] = {
    Param: PARAM_CODES,
    RealtimeField: REALTIME_FIELD_CODES,
    RiskType: RISK_TYPE_CODES,
    HeatCity: HEAT_CITY_CODES,
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


class AlertLevel(_NamedLevel):
    """The level of a risk, or of the danger now, as the alert bulletin colors it.

    Levels compare with each other (``level >= AlertLevel.YELLOW``).
    """

    UNKNOWN = 0
    """A text aioarpapiemonte does not know."""
    NOT_EVALUATED = 1
    """White (BIANCO): not evaluated, as the avalanches out of season."""
    GREEN = 2
    """Green (VERDE): no significant phenomena expected."""
    YELLOW = 3
    """Yellow (GIALLO): localized phenomena."""
    ORANGE = 4
    """Orange (ARANCIONE): widespread phenomena."""
    RED = 5
    """Red (ROSSO): numerous and/or extensive phenomena."""

    @property
    def is_alert(self) -> bool:
        """Return whether the level is an alert: yellow or higher."""
        return self >= AlertLevel.YELLOW


class AlertDay(_NamedLevel):
    """A day of the alert bulletin: the day it is issued and the next.

    The bulletin is issued around 13:00: until then, its day of issue is
    yesterday. :meth:`MunicipalityAlerts.day_of` gives the day of a date.
    """

    ISSUE_DAY = 0
    """The day the bulletin is issued (``day_0``)."""
    NEXT_DAY = 1
    """The next day (``day_1``)."""


class OperationalPhase(_NamedLevel):
    """The operational phase a municipality has declared (fase operativa comunale)."""

    UNKNOWN = 0
    """A text aioarpapiemonte does not know."""
    NONE = 1
    """No operational phase ("Nessuna Fase Operativa")."""
    ATTENTION = 2
    """Attention ("Attenzione")."""
    PRE_ALARM = 3
    """Pre-alarm ("Preallarme")."""
    ALARM = 4
    """Alarm ("Allarme")."""


@dataclass(frozen=True, slots=True)
class RiskLevel:
    """The level of a risk on a day."""

    risk: RiskType
    day: AlertDay
    level: AlertLevel


@dataclass(frozen=True, slots=True)
class MunicipalityAlerts:
    """The alerts of a municipality, as the municipality widget of Arpa gives them.

    The widget asks to keep its layout unless only the bell (the highest
    alert) is used; its data is under CC BY 4.0, credited to Arpa Piemonte.
    """

    municipality_code: str
    """ISTAT code of the municipality, the current one ("096050")."""
    name: str
    """Name of the municipality."""
    alert: AlertLevel
    """The highest alert of the municipality (``allerta``): the bell."""
    risks: tuple[RiskLevel, ...]
    """The level of each risk on each day of the bulletin."""
    current_danger: AlertLevel
    """The danger now, from the rain and the rivers measured (pericolo attuale)."""
    current_danger_time: dt.datetime | None
    """When the danger now was assessed."""
    phase: OperationalPhase
    """The operational phase the municipality has declared."""
    phase_text: str | None
    """The phase as published ("Nessuna Fase Operativa")."""
    phase_time: dt.datetime | None
    """When the phase was declared."""
    bulletin: str | None
    """Number of the alert bulletin ("334/2026")."""
    issued: dt.datetime | None
    """When the bulletin was issued."""
    issue_day: dt.date | None
    """The day the bulletin was issued, the first day of its levels."""
    next_update: dt.datetime | None
    """When the next bulletin is due."""
    zones: tuple[str, ...]
    """The alert zones of the municipality ("Piem-B"); some have two."""

    def level(self, risk: RiskType, day: AlertDay) -> AlertLevel:
        """Return the level of a risk on a day of the bulletin; UNKNOWN without it."""
        return next(
            (
                item.level
                for item in self.risks
                if item.risk is risk and item.day is day
            ),
            AlertLevel.UNKNOWN,
        )

    def highest(self, day: AlertDay) -> AlertLevel:
        """Return the highest level of the risks of a day; UNKNOWN without any."""
        return max(
            (item.level for item in self.risks if item.day is day),
            default=AlertLevel.UNKNOWN,
        )

    def day_of(self, date: dt.date) -> AlertDay | None:
        """Return the day of the bulletin that is a date; None when it covers none.

        The bulletin is issued around 13:00: in the morning, its first day is
        yesterday, and today is its second.
        """
        if self.issue_day is None:
            return None
        return next(
            (
                day
                for day in AlertDay
                if self.issue_day + dt.timedelta(days=day) == date
            ),
            None,
        )

    def level_on(self, risk: RiskType, date: dt.date) -> AlertLevel:
        """Return the level of a risk on a date; UNKNOWN when the bulletin has none."""
        day = self.day_of(date)
        return AlertLevel.UNKNOWN if day is None else self.level(risk, day)

    def highest_on(self, date: dt.date) -> AlertLevel:
        """Return the highest level of the risks on a date; UNKNOWN without any."""
        day = self.day_of(date)
        return AlertLevel.UNKNOWN if day is None else self.highest(day)


@dataclass(frozen=True, slots=True)
class Earthquake:
    """An earthquake of the last 30 days, as the seismic network of Arpa lists it."""

    id: str
    """Identifier of the event ("261117064149")."""
    time: dt.datetime
    """Time of the earthquake, in UTC."""
    district: str | None
    """Seismic district ("Alpi Cozie")."""
    latitude: float
    """Latitude of the epicentre, WGS84."""
    longitude: float
    """Longitude of the epicentre, WGS84."""
    depth: float | None
    """Depth, in km."""
    magnitude: float
    """Magnitude."""
    magnitude_type: str | None
    """Type of the magnitude ("ML", local magnitude)."""
    reviewed: bool
    """Whether a seismologist reviewed it (``dati_elaborati`` "rivisti").

    Arpa lists the events of magnitude 1.0 or more once reviewed, and those of
    2.5 or more automatically within minutes; every event of 2026-11-17 was
    reviewed, so the text of the others is unverified.
    """

    def distance_km(self, latitude: float, longitude: float) -> float:
        """Return the distance from a position to the epicentre, in km."""
        return distance_km(latitude, longitude, self.latitude, self.longitude)


class HeatLevel(_NamedLevel):
    """The bioclimatic discomfort of a day, by the colour of its level.

    Arpa numbers the levels 0 to 3: the thresholds are the 75th, 90th and 95th
    percentiles of the apparent temperature ("Guida alla lettura del
    Bollettino Ondate di Calore").
    """

    UNKNOWN = 0
    """A level aioarpapiemonte does not know."""
    GREEN = 1
    """Level 0: no discomfort."""
    YELLOW = 2
    """Level 1: above the 75th percentile."""
    ORANGE = 3
    """Level 2: above the 90th percentile."""
    RED = 4
    """Level 3: above the 95th percentile."""

    @property
    def arpa_level(self) -> int | None:
        """Return the level as Arpa numbers it, 0 to 3; None when unknown."""
        return None if self is HeatLevel.UNKNOWN else self.value - 1

    @classmethod
    def of_arpa(cls, level: float | None) -> HeatLevel:
        """Return the level Arpa numbers 0 to 3; UNKNOWN for any other."""
        if level is None or not level.is_integer():
            return cls.UNKNOWN
        return cls.from_code(int(level) + 1) or cls.UNKNOWN


@dataclass(frozen=True, slots=True)
class HeatDay:
    """The heat of a day in a city."""

    day: dt.date
    """The day."""
    level: HeatLevel
    """The bioclimatic discomfort."""
    description: str | None
    """The level as Arpa names it ("Nessun disagio")."""
    detail: str | None
    """What the level means, as Arpa writes it."""
    max_temperature: float | None
    """Highest temperature, in °C."""
    min_temperature: float | None
    """Lowest temperature, in °C."""
    max_apparent_temperature: float | None
    """Highest apparent temperature, in °C."""
    min_apparent_temperature: float | None
    """Lowest apparent temperature, in °C."""
    hot_days: int | None
    """Consecutive hot days."""


@dataclass(frozen=True, slots=True)
class HeatForecast:
    """The heat-wave bulletin of a city: 3 days, from 15 May to about 30 September.

    Out of season, the file keeps the last bulletin: compare ``next_update``
    with now.
    """

    city: HeatCity
    """The city."""
    issued: dt.datetime | None
    """When the bulletin was issued."""
    next_update: dt.datetime | None
    """When the next bulletin is due."""
    note: str | None
    """The note of the bulletin, when it has one."""
    days: tuple[HeatDay, ...]
    """The days, from the first."""

    def on(self, day: dt.date) -> HeatDay | None:
        """Return the heat of a day; None when the bulletin does not cover it."""
        return next((item for item in self.days if item.day == day), None)


class AvalancheDanger(_NamedLevel):
    """The avalanche danger, on the European scale of EAWS (1 low to 5 very high)."""

    UNKNOWN = 0
    """Not rated, or a value aioarpapiemonte does not know."""
    NO_SNOW = 1
    """No snow."""
    LOW = 2
    """1, low."""
    MODERATE = 3
    """2, moderate."""
    CONSIDERABLE = 4
    """3, considerable."""
    HIGH = 5
    """4, high."""
    VERY_HIGH = 6
    """5, very high."""

    @property
    def scale(self) -> int | None:
        """Return the level on the European scale, 1 to 5; None for no rating."""
        return self.value - 1 if self >= AvalancheDanger.LOW else None


@dataclass(frozen=True, slots=True)
class DangerRating:
    """A danger of a bulletin, at some elevations and time of the day."""

    danger: AvalancheDanger
    lower_bound: str | None = None
    """Lowest elevation, in metres, or "treeline"; None from the bottom."""
    upper_bound: str | None = None
    """Highest elevation, in metres, or "treeline"; None to the top."""
    period: str | None = None
    """Time of the day: "earlier", "later" or "all_day"; None for all day."""


@dataclass(frozen=True, slots=True)
class AvalancheProblem:
    """An avalanche problem of a bulletin."""

    problem_type: str
    """The problem, as EAWS names it ("persistent_weak_layers", "wet_snow")."""
    aspects: tuple[str, ...] = ()
    """The aspects it concerns ("N", "NE"...)."""
    lower_bound: str | None = None
    """Lowest elevation, as in :class:`DangerRating`."""
    upper_bound: str | None = None
    """Highest elevation, as in :class:`DangerRating`."""
    period: str | None = None
    """Time of the day, as in :class:`DangerRating`."""
    size: int | None = None
    """Expected avalanche size, 1 to 5."""
    frequency: str | None = None
    """How many slopes are concerned ("none", "few", "some", "many")."""
    stability: str | None = None
    """Stability of the snowpack ("good", "fair", "poor", "very_poor")."""


@dataclass(frozen=True, slots=True)
class RegionBulletin:
    """The avalanche bulletin of a micro-region of Piedmont (EAWS IT-21)."""

    region_id: str
    """Identifier of the micro-region ("IT-21-TO-03"); its name is in
    :data:`~aioarpapiemonte.geo.MICRO_REGION_NAMES`."""
    bulletin_id: str | None
    """Identifier of the bulletin, shared by the micro-regions it covers."""
    published: dt.datetime | None
    """When the bulletin was published, in UTC: about 16:00 the day before."""
    valid_from: dt.datetime | None
    """Start of the day the bulletin is for, in UTC."""
    valid_to: dt.datetime | None
    """End of the day the bulletin is for, in UTC."""
    ratings: tuple[DangerRating, ...]
    """The danger at each elevation and time of the day."""
    problems: tuple[AvalancheProblem, ...]
    """The avalanche problems."""
    tendency: str | None
    """The tendency for the next day ("decreasing", "steady", "increasing")."""
    highlights: str | None = None
    """The headline of the bulletin, in English."""

    @property
    def danger(self) -> AvalancheDanger:
        """Return the highest danger of the bulletin; UNKNOWN without any."""
        return max(
            (rating.danger for rating in self.ratings), default=AvalancheDanger.UNKNOWN
        )


@dataclass(frozen=True, slots=True)
class AvalancheBulletin:
    """The avalanche bulletins of Piedmont for a day, by micro-region.

    Published by AINEVA for Piedmont in the format of EAWS (CAAML v6), from
    December to May; the licence of the bulletin is not stated.
    """

    regions: tuple[RegionBulletin, ...]

    def of_region(self, region_id: str) -> RegionBulletin | None:
        """Return the bulletin of a micro-region; None when it is not covered."""
        return next(
            (region for region in self.regions if region.region_id == region_id),
            None,
        )


def station_page_url(sensor_id: str, param: Param) -> str:
    """Return the public page of a station on the Arpa website."""
    return STATION_PAGE_URL.format(sensor_id=sensor_id, param=param.value)
