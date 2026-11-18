"""Parsing of the data of Arpa Piemonte, without I/O.

The readings of the stations come from two sources, measured on 2026-11-17:

- the files of the Arpa website: a GeoJSON Feature per station and quantity,
  with hourly readings keyed by their time in UTC ("2026-11-17T02:00") and
  their automatic validation; about the last 6 days;
- the api_realtime: JSON records with an offset in their times, about the
  last 3 days. Every answer is ``application/problem+json``, even a 200, and
  a query it cannot answer is a 200 whose fields are all null.

The natural risks come from the widgets of the website (the alerts of a
municipality, the heat waves), its list of earthquakes, and the avalanche
bulletins of EAWS (CAAML v6), measured on 2026-11-17 and 18.
"""

from __future__ import annotations

import datetime as dt
import logging
import math
from collections.abc import Mapping
from typing import Final

from .const import PIEMONTE_EAWS_REGION, PIEMONTE_NETWORK
from .exceptions import ArpaPiemonteParseError
from .models import (
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
    MunicipalityAlerts,
    OperationalPhase,
    Param,
    ParamReading,
    ParamSeries,
    RealtimeField,
    RealtimeRecord,
    RealtimeStation,
    RegionBulletin,
    RiskLevel,
    RiskType,
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

ALERT_LEVELS: Final[Mapping[str, AlertLevel]] = {
    "BIANCO": AlertLevel.NOT_EVALUATED,
    "VERDE": AlertLevel.GREEN,
    "GIALLO": AlertLevel.YELLOW,
    "GIALLA": AlertLevel.YELLOW,
    "ARANCIONE": AlertLevel.ORANGE,
    "ROSSO": AlertLevel.RED,
    "ROSSA": AlertLevel.RED,
}
"""Levels of the widget of a municipality, by the colour it writes.

VERDE and BIANCO were seen on 2026-11-17 and 18; the others are the colours
the widget names (``colore_allerta_GIALLO_hex``), and their feminine forms.
"""

OPERATIONAL_PHASES: Final[Mapping[str, OperationalPhase]] = {
    "nessuna fase operativa": OperationalPhase.NONE,
    "attenzione": OperationalPhase.ATTENTION,
    "preallarme": OperationalPhase.PRE_ALARM,
    "allarme": OperationalPhase.ALARM,
}
"""Phases by their text, lower case, as the widget lists them
(``fase_operativa_comunale_legenda``)."""

AVALANCHE_DANGERS: Final[Mapping[str, AvalancheDanger]] = {
    "no_snow": AvalancheDanger.NO_SNOW,
    "low": AvalancheDanger.LOW,
    "moderate": AvalancheDanger.MODERATE,
    "considerable": AvalancheDanger.CONSIDERABLE,
    "high": AvalancheDanger.HIGH,
    "very_high": AvalancheDanger.VERY_HIGH,
}
"""Dangers by their value in CAAML v6 (``mainValue``); "no_rating" is UNKNOWN."""

REVIEWED_EARTHQUAKE: Final = "rivisti"
"""``dati_elaborati`` of an earthquake reviewed by a seismologist."""

_EMPTY_TEXTS: Final = frozenset({"", "-"})
"""Texts written for a missing value: the api_realtime gives the river of the
264 stations without a hydrometer as "-" (``river_name``, measured on
2026-11-17), as Meteo 3R does."""


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


def parse_municipality_alerts(
    data: object, municipality_code: str
) -> MunicipalityAlerts:
    """Return the alerts of a municipality, from its widget.

    A level the widget does not write is left out, and a colour
    aioarpapiemonte does not know is UNKNOWN. Raises
    :class:`ArpaPiemonteParseError` when the widget has no level at all.
    """
    widget = _mapping(data, "The widget")
    risks = tuple(
        RiskLevel(risk, day, _alert_level(text))
        for risk in RiskType
        for day in AlertDay
        if (text := _text(widget, f"{risk.value}_day_{day.value}")) is not None
    )
    alert = _text(widget, "allerta")
    if alert is None and not risks:
        msg = f"The widget of {municipality_code} has no alert"
        raise ArpaPiemonteParseError(msg)
    phase = _text(widget, "fase_operativa_comunale_attuata")
    issue = _aware_time(widget, "emissione")
    zones = (_text(widget, "zone_di_allerta") or "").split(",")
    return MunicipalityAlerts(
        municipality_code=municipality_code,
        name=_text(widget, "nome_comune") or municipality_code,
        alert=_alert_level(alert),
        risks=risks,
        current_danger=_alert_level(_text(widget, "pericolo_attuale")),
        current_danger_time=_utc_of(
            widget, "aggiornamento_livello_di_pericolo_attuale"
        ),
        phase=OPERATIONAL_PHASES.get(
            (phase or "").casefold(), OperationalPhase.UNKNOWN
        ),
        phase_text=phase,
        phase_time=_utc_of(widget, "aggiornamento_fase_operativa_comunale_attuata"),
        bulletin=_text(widget, "numero_bollettino"),
        issued=_utc_of(widget, "emesso_il"),
        issue_day=None if issue is None else issue.date(),
        next_update=_utc_of(widget, "prossimo_aggiornamento"),
        zones=tuple(zone.strip() for zone in zones if zone.strip()),
    )


def parse_earthquakes(data: object) -> tuple[Earthquake, ...]:
    """Return the earthquakes of the list of Arpa, from the newest.

    An event that cannot be read is left out (logged at debug level). Raises
    :class:`ArpaPiemonteParseError` when the list is not a list.
    """
    if not isinstance(data, list):
        msg = "The earthquakes are not a list"
        raise ArpaPiemonteParseError(msg)
    earthquakes = []
    for item in data:
        try:
            earthquakes.append(_earthquake(item))
        except ArpaPiemonteParseError as err:
            _LOGGER.debug("Earthquake left out: %s", err)
    return tuple(sorted(earthquakes, key=lambda quake: quake.time, reverse=True))


def parse_heat_forecast(data: object, city: HeatCity) -> HeatForecast:
    """Return the heat-wave bulletin of a city, from its widget.

    The days are under the name of the city in capitals ("TORINO"), as in
    the widgets of the 8 cities (measured on 2026-11-18). Raises
    :class:`ArpaPiemonteParseError` when the city has no day.
    """
    widget = _mapping(data, "The heat-wave bulletin")
    cells = _mapping(widget.get(city.value.upper()), f"The days of {city.value}")
    days = sorted(
        (_heat_day(key, cell) for key, cell in cells.items()),
        key=lambda heat: heat.day,
    )
    if not days:
        msg = f"The heat-wave bulletin of {city.value} has no day"
        raise ArpaPiemonteParseError(msg)
    return HeatForecast(
        city=city,
        issued=_utc_of(widget, "emissione"),
        next_update=_utc_of(widget, "prossimo_aggiornamento"),
        note=_text(widget, "note"),
        days=tuple(days),
    )


def parse_avalanche_bulletin(data: object) -> AvalancheBulletin:
    """Return the avalanche bulletins of the micro-regions of Piedmont.

    ``data`` is a CAAML v6 file of EAWS: the micro-regions of other members
    are left out. Raises :class:`ArpaPiemonteParseError` when no micro-region
    of Piedmont has a bulletin.
    """
    bulletins = _mapping(data, "The avalanche bulletin").get("bulletins")
    regions = [
        region
        for bulletin in _list(bulletins)
        for region in _region_bulletins(_mapping(bulletin, "A bulletin"))
    ]
    if not regions:
        msg = "The avalanche bulletin has no micro-region of Piedmont"
        raise ArpaPiemonteParseError(msg)
    return AvalancheBulletin(tuple(regions))


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


def _alert_level(text: str | None) -> AlertLevel:
    if text is None:
        return AlertLevel.UNKNOWN
    level = ALERT_LEVELS.get(text.upper())
    if level is None:
        _LOGGER.debug("Unknown alert level: %r", text)
        return AlertLevel.UNKNOWN
    return level


def _earthquake(item: object) -> Earthquake:
    event = _mapping(item, "An earthquake")
    identifier = _text(event, "ID evento")
    time = _aware_time(event, "Data e ora (UTC)", dt.UTC)
    latitude = _number(event.get("Latitudine (N)"))
    longitude = _number(event.get("Longitudine (E)"))
    magnitude = _number(event.get("valore"))
    if (
        identifier is None
        or time is None
        or latitude is None
        or longitude is None
        or magnitude is None
    ):
        msg = f"An earthquake without id, time, position or magnitude: {identifier!r}"
        raise ArpaPiemonteParseError(msg)
    return Earthquake(
        id=identifier,
        time=time.astimezone(dt.UTC),
        district=_text(event, "Distretto sismico"),
        latitude=latitude,
        longitude=longitude,
        depth=_number(event.get("(km)")),
        magnitude=magnitude,
        magnitude_type=_text(event, "tipo"),
        reviewed=_text(event, "dati_elaborati") == REVIEWED_EARTHQUAKE,
    )


def _heat_day(key: str, cell: object) -> HeatDay:
    try:
        day = dt.datetime.fromisoformat(key).date()
    except ValueError as err:
        msg = f"Not a day: {key!r}"
        raise ArpaPiemonteParseError(msg) from err
    values = _mapping(cell, f"The heat of {key}")
    level = parse_decimal(values.get("livello_disagio"))
    hot_days = parse_decimal(values.get("giorni_consecutivi_caldo"))
    return HeatDay(
        day=day,
        level=HeatLevel.of_arpa(level),
        description=_text(values, "livello_disagio_descrizione"),
        # Sic: the widget writes "dettalio".
        detail=_text(values, "livello_disagio_dettalio"),
        max_temperature=parse_decimal(values.get("temperatura_massima")),
        min_temperature=parse_decimal(values.get("temperatura_minima")),
        max_apparent_temperature=parse_decimal(
            values.get("temperatura_massima_percepita")
        ),
        min_apparent_temperature=parse_decimal(
            values.get("temperatura_minima_percepita")
        ),
        hot_days=None if hot_days is None else int(hot_days),
    )


def _region_bulletins(bulletin: Mapping[str, object]) -> list[RegionBulletin]:
    """Return the bulletin of each micro-region of Piedmont a bulletin covers."""
    region_ids = [
        region_id
        for region in _list(bulletin.get("regions"))
        if isinstance(region, Mapping)
        and (region_id := _text(region, "regionID")) is not None
        and region_id.startswith(f"{PIEMONTE_EAWS_REGION}-")
    ]
    valid = _mapping_or_empty(bulletin.get("validTime"))
    ratings = tuple(
        DangerRating(
            AVALANCHE_DANGERS.get(
                _text(rating, "mainValue") or "", AvalancheDanger.UNKNOWN
            ),
            *_elevation(rating),
            period=_text(rating, "validTimePeriod"),
        )
        for rating in _list(bulletin.get("dangerRatings"))
        if isinstance(rating, Mapping)
    )
    problems = tuple(
        problem
        for item in _list(bulletin.get("avalancheProblems"))
        if (problem := _avalanche_problem(item)) is not None
    )
    tendency = next(
        (
            text
            for item in _list(bulletin.get("tendency"))
            if isinstance(item, Mapping)
            and (text := _text(item, "tendencyType")) is not None
        ),
        None,
    )
    activity = _mapping_or_empty(bulletin.get("avalancheActivity"))
    return [
        RegionBulletin(
            region_id=region_id,
            bulletin_id=_text(bulletin, "bulletinID"),
            published=_utc_of(bulletin, "publicationTime"),
            valid_from=_utc_of(valid, "startTime"),
            valid_to=_utc_of(valid, "endTime"),
            ratings=ratings,
            problems=problems,
            tendency=tendency,
            highlights=_text(activity, "highlights"),
        )
        for region_id in region_ids
    ]


def _avalanche_problem(item: object) -> AvalancheProblem | None:
    if not isinstance(item, Mapping):
        return None
    problem_type = _text(item, "problemType")
    if problem_type is None:
        return None
    size = _number(item.get("avalancheSize"))
    return AvalancheProblem(
        problem_type,
        aspects=tuple(
            aspect for aspect in _list(item.get("aspects")) if isinstance(aspect, str)
        ),
        lower_bound=_elevation(item)[0],
        upper_bound=_elevation(item)[1],
        period=_text(item, "validTimePeriod"),
        size=None if size is None else int(size),
        frequency=_text(item, "frequency"),
        stability=_text(item, "snowpackStability"),
    )


def _elevation(item: Mapping[str, object]) -> tuple[str | None, str | None]:
    """Return the lowest and highest elevation of a rating or problem."""
    elevation = _mapping_or_empty(item.get("elevation"))
    return _text(elevation, "lowerBound"), _text(elevation, "upperBound")


def _aware_time(
    record: Mapping[str, object], key: str, naive: dt.tzinfo | None = None
) -> dt.datetime | None:
    """Return a time with its offset ("2026-11-17T23:01:00+0100").

    A time without offset is in the time zone ``naive``; without it, the time
    is not read. None for a missing or unreadable time (logged at debug
    level).
    """
    text = _text(record, key)
    if text is None:
        return None
    try:
        time = dt.datetime.fromisoformat(text)
    except ValueError:
        _LOGGER.debug("Not a time: %s %r", key, text)
        return None
    if time.tzinfo is None:
        if naive is None:
            _LOGGER.debug("A time without offset: %s %r", key, text)
            return None
        time = time.replace(tzinfo=naive)
    return time


def _utc_of(record: Mapping[str, object], key: str) -> dt.datetime | None:
    """Return a time with its offset in UTC; None as :func:`_aware_time`."""
    time = _aware_time(record, key)
    return None if time is None else time.astimezone(dt.UTC)


def _list(value: object) -> list[object]:
    """Return a list; an empty one for anything else."""
    return value if isinstance(value, list) else []


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping(value: object, what: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        msg = f"{what} is not an object"
        raise ArpaPiemonteParseError(msg)
    return value


def _text(record: Mapping[str, object], key: str) -> str | None:
    """Return a text of a record, stripped; None when missing or empty."""
    value = record.get(key)
    if not isinstance(value, str) or value.strip() in _EMPTY_TEXTS:
        return None
    return value.strip()


def _number(value: object) -> float | None:
    """Return a finite number as a float; None for anything else."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None
