"""Parsing of the real-time data of Arpa Piemonte, without I/O.

Two sources, measured on 2026-11-17:

- the files of the Arpa website: a GeoJSON Feature per station and quantity,
  with hourly readings keyed by their time in UTC ("2026-11-17T02:00") and
  their automatic validation; about the last 6 days;
- the api_realtime: JSON records with an offset in their times, about the
  last 3 days. Every answer is ``application/problem+json``, even a 200, and
  a query it cannot answer is a 200 whose fields are all null.
"""

from __future__ import annotations

import datetime as dt
import logging
import math
from collections.abc import Mapping
from typing import Final

from .const import PIEMONTE_NETWORK
from .exceptions import ArpaPiemonteParseError
from .models import (
    Param,
    ParamReading,
    ParamSeries,
    RealtimeField,
    RealtimeRecord,
    RealtimeStation,
    Sensor,
    Thresholds,
    Validation,
)
from .urls import sensor_id

_LOGGER = logging.getLogger(__name__)

GEOJSON_TIME_FORMAT: Final = "%Y-%m-%dT%H:%M"
"""Format of the times of the files of the website, in UTC."""

THRESHOLD_KEYS: Final = (
    "pre-alarm_threshold",
    "guard_threshold",
    "danger_threshold",
)
"""Thresholds in the level files (``idro``), in that order; with a hyphen."""


def parse_sensors(data: object) -> tuple[Sensor, ...]:
    """Return the stations of the list of the website (``sensors.geojson``).

    A station that cannot be read is left out (logged at debug level). Raises
    :class:`ArpaPiemonteParseError` when the list has no station.
    """
    features = _mapping(data, "The station list").get("features")
    if not isinstance(features, list):
        msg = "The station list has no features"
        raise ArpaPiemonteParseError(msg)
    sensors = []
    for feature in features:
        try:
            sensors.append(_sensor(feature))
        except ArpaPiemonteParseError as err:
            _LOGGER.debug("Station left out: %s", err)
    if not sensors:
        msg = "The station list has no station"
        raise ArpaPiemonteParseError(msg)
    return tuple(sensors)


def parse_series(data: object, param: Param, station: str | None = None) -> ParamSeries:
    """Return the readings of a file of a quantity of a station.

    With ``station``, the file must be that station's. Raises
    :class:`ArpaPiemonteParseError` when the file does not have the expected
    format.
    """
    properties = _mapping(_mapping(data, "The file").get("properties"), "properties")
    found = _text(properties, "sensor")
    if found is None or (station is not None and found != station):
        msg = f"Asked for station {station}, the file is of station {found}"
        raise ArpaPiemonteParseError(msg)
    cells = _mapping(properties.get(param.value), f"The readings of {param.value}")
    readings = sorted(
        (
            reading
            for key, cell in cells.items()
            if (reading := _param_reading(key, cell))
        ),
        key=lambda reading: reading.time,
    )
    thresholds = None
    if param is Param.LEVEL:
        pre_alarm, guard, danger = (
            _number(properties.get(key)) for key in THRESHOLD_KEYS
        )
        thresholds = Thresholds(pre_alarm, guard, danger)
    return ParamSeries(
        sensor_id=found,
        param=param,
        name=_text(properties, "name") or found,
        readings=tuple(readings),
        river=_text(properties, "river"),
        basin=_text(properties, "basin"),
        hydrometric_zero=_number(properties.get("zero_hydrometric")),
        thresholds=thresholds,
        description=_text(properties, "description"),
    )


def parse_pie_anag(data: object) -> tuple[RealtimeStation, ...]:
    """Return the stations of Piedmont of the api_realtime (``pie_anag``).

    A station that cannot be read is left out (logged at debug level). Raises
    :class:`ArpaPiemonteParseError` when the answer is not a list of stations.
    """
    if not isinstance(data, list):
        msg = "The stations of the api_realtime are not a list"
        raise ArpaPiemonteParseError(msg)
    stations = []
    for record in data:
        if (
            not isinstance(record, Mapping)
            or record.get("id_network") != PIEMONTE_NETWORK
        ):
            continue
        try:
            stations.append(_realtime_station(record))
        except ArpaPiemonteParseError as err:
            _LOGGER.debug("Station left out: %s", err)
    if not stations:
        msg = "The api_realtime has no station of Piedmont"
        raise ArpaPiemonteParseError(msg)
    return tuple(stations)


def parse_data_pie_page(
    data: object, station_code: str
) -> tuple[list[RealtimeRecord], int]:
    """Return the records of a station in a page of the api_realtime, and its pages.

    A page without records has ``data`` null. Records of other stations are
    left out. Raises :class:`ArpaPiemonteParseError` when the page does not
    have the expected format.
    """
    page = _mapping(data, "The page")
    total_pages = page.get("total_pages")
    if total_pages is None:
        total_pages = 0
    if isinstance(total_pages, bool) or not isinstance(total_pages, int):
        msg = f"total_pages is not a number: {total_pages!r}"
        raise ArpaPiemonteParseError(msg)
    items = page.get("data")
    if items is None:
        return [], total_pages
    if not isinstance(items, list):
        msg = "The records are not a list"
        raise ArpaPiemonteParseError(msg)
    records = [
        _realtime_record(item)
        for item in items
        if isinstance(item, Mapping) and item.get("station_code") == station_code
    ]
    return records, total_pages


def parse_status(data: object) -> str:
    """Return the status of the api_realtime ("healthy")."""
    status = _text(_mapping(data, "The status"), "status")
    if status is None:
        msg = "The api_realtime gave no status"
        raise ArpaPiemonteParseError(msg)
    return status


def parse_decimal(value: object) -> float | None:
    """Return a number the api_realtime writes as text ("2.3", "3", "").

    None for an empty or unreadable value.
    """
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if not text:
            return None
        try:
            return _number(float(text))
        except ValueError:
            _LOGGER.debug("Not a number: %r", value)
            return None
    return _number(value)


def _sensor(feature: object) -> Sensor:
    feature = _mapping(feature, "A station")
    properties = _mapping(feature.get("properties"), "A station")
    identifier = _text(properties, "sensor")
    if identifier is None:
        msg = "A station has no identifier"
        raise ArpaPiemonteParseError(msg)
    coordinates = _mapping(feature.get("geometry"), "A station").get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:  # noqa: PLR2004 - longitude and latitude
        msg = f"Station {identifier} has no coordinates"
        raise ArpaPiemonteParseError(msg)
    longitude, latitude = _number(coordinates[0]), _number(coordinates[1])
    if longitude is None or latitude is None:
        msg = f"Station {identifier} has no coordinates"
        raise ArpaPiemonteParseError(msg)
    published = properties.get("sensors")
    names = [str(name) for name in published] if isinstance(published, Mapping) else []
    known = {param.value: param for param in Param}
    return Sensor(
        id=identifier,
        name=_text(properties, "name") or identifier,
        latitude=latitude,
        longitude=longitude,
        altitude=_number(properties.get("quote")),
        params=frozenset(known[name] for name in names if name in known),
        municipality=_text(properties, "municipality"),
        river=_text(properties, "river"),
        basin=_text(properties, "basin"),
        other_params=tuple(sorted(name for name in names if name not in known)),
    )


def _param_reading(key: str, cell: object) -> ParamReading | None:
    """Return a reading of a file; None for a cell without value."""
    if not isinstance(cell, Mapping):
        msg = f"The reading of {key!r} is not an object"
        raise ArpaPiemonteParseError(msg)
    value = cell.get("value")
    if value is None:
        return None
    number = _number(value)
    if number is None:
        msg = f"The reading of {key!r} is not a number: {value!r}"
        raise ArpaPiemonteParseError(msg)
    valid_type = cell.get("valid_type")
    valid_type = valid_type if isinstance(valid_type, str) else None
    return ParamReading(
        time=_utc_time(key),
        value=number,
        validation=Validation.of(valid_type),
        valid_type=valid_type,
    )


def _utc_time(key: str) -> dt.datetime:
    try:
        return dt.datetime.strptime(key, GEOJSON_TIME_FORMAT).replace(tzinfo=dt.UTC)
    except ValueError as err:
        msg = f"Not a time: {key!r}"
        raise ArpaPiemonteParseError(msg) from err


def _realtime_station(record: Mapping[str, object]) -> RealtimeStation:
    code = _text(record, "station_code")
    name = _text(record, "name")
    latitude = _number(record.get("lat"))
    longitude = _number(record.get("lng"))
    if code is None or name is None or latitude is None or longitude is None:
        msg = f"Station without code, name or coordinates: {code!r}"
        raise ArpaPiemonteParseError(msg)
    return RealtimeStation(
        station_code=code,
        name=name,
        latitude=latitude,
        longitude=longitude,
        altitude=_number(record.get("quote")),
        station_type=_text(record, "station_type") or "",
        municipality=_text(record, "municipality") or "",
        municipality_code=_text(record, "municipality_code") or "",
        river=_text(record, "river_name"),
        basin=_text(record, "basin"),
        hydrometric_zero=parse_decimal(record.get("hydrometric_zero")),
        thresholds=Thresholds(
            parse_decimal(record.get("threshold_level")),
            parse_decimal(record.get("guard_threshold")),
            parse_decimal(record.get("danger_threshold")),
        ),
        sensor_id=_sensor_id(record),
    )


def _sensor_id(record: Mapping[str, object]) -> str | None:
    """Return the identifier on the website of a station of the api_realtime."""
    municipality = record.get("codice_istat_comune")
    number = record.get("progr_punto_com")
    if isinstance(number, str) and number.isdigit():
        number = int(number)
    if not isinstance(municipality, str) or not isinstance(number, int):
        return None
    try:
        return sensor_id(municipality, number)
    except ValueError:
        return None


def _realtime_record(item: Mapping[str, object]) -> RealtimeRecord:
    date = item.get("date")
    if not isinstance(date, str):
        msg = f"A record has no date: {date!r}"
        raise ArpaPiemonteParseError(msg)
    try:
        time = dt.datetime.fromisoformat(date)
    except ValueError as err:
        msg = f"Not a date: {date!r}"
        raise ArpaPiemonteParseError(msg) from err
    if time.tzinfo is None:
        msg = f"A date without offset: {date!r}"
        raise ArpaPiemonteParseError(msg)
    values = []
    for field in RealtimeField:
        raw = item.get(field.value)
        if raw is None:
            continue
        number = _number(raw)
        if number is None:
            msg = f"{field.value} is not a number: {raw!r}"
            raise ArpaPiemonteParseError(msg)
        values.append((field, number))
    return RealtimeRecord(time.astimezone(dt.UTC), tuple(values))


def _mapping(value: object, what: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        msg = f"{what} is not an object"
        raise ArpaPiemonteParseError(msg)
    return value


def _text(record: Mapping[str, object], key: str) -> str | None:
    """Return a text of a record, stripped; None when missing or empty."""
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _number(value: object) -> float | None:
    """Return a finite number as a float; None for anything else."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None
