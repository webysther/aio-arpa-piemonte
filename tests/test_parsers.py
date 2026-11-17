"""Tests of the parsing of the real-time data of Arpa Piemonte."""

from __future__ import annotations

import math

import pytest

from aioarpapiemonte import (
    ArpaPiemonteParseError,
    Param,
    RealtimeField,
    Thresholds,
    Validation,
)
from aioarpapiemonte.parsers import (
    parse_data_pie_page,
    parse_decimal,
    parse_pie_anag,
    parse_sensors,
    parse_series,
    parse_status,
)

from . import PRAY, PRAY_SENSOR, real_json, utc

FEATURE: dict[str, object] = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [8.22167, 45.67389, 409.0]},
    "properties": {"sensor": PRAY_SENSOR, "name": "PRAY SESSERA", "sensors": {}},
}

ANAG: dict[str, object] = {
    "id_network": "PIE",
    "station_code": "188",
    "name": "PRAY SESSERA",
    "lat": 45.6739,
    "lng": 8.22167,
    "station_type": "IPT",
    "codice_istat_comune": "002105",
    "progr_punto_com": 900,
}


def level_file(cells: object, **properties: object) -> dict[str, object]:
    """Return a level file of Pray with the given readings."""
    return {
        **FEATURE,
        "properties": {"sensor": PRAY_SENSOR, "idro": cells, **properties},
    }


class TestSensors:
    """The station list of the website."""

    def test_real_list(self) -> None:
        """Test the stations of the real list, and Pray."""
        sensors = parse_sensors(real_json("sensors.geojson"))

        assert len(sensors) == 381
        assert sum(Param.LEVEL in sensor.params for sensor in sensors) == 115
        pray = next(sensor for sensor in sensors if sensor.id == PRAY_SENSOR)
        assert pray.params == {Param.LEVEL, Param.RAIN_10_MIN, Param.TEMPERATURE}
        assert (pray.latitude, pray.longitude, pray.altitude) == (
            45.67389,
            8.22167,
            409.0,
        )
        assert pray.river == "SESSERA"
        assert pray.page_url().endswith("?id=002105900&param=idro")

    def test_unknown_quantity_and_unreadable_stations(self) -> None:
        """Test that unknown quantities are listed and broken stations left out."""
        sensors = parse_sensors(
            {
                "features": [
                    {
                        **FEATURE,
                        "properties": {
                            "sensor": PRAY_SENSOR,
                            "sensors": {"nivo_v": {}},
                        },
                    },
                    "not a feature",
                    {**FEATURE, "properties": {"name": "No identifier"}},
                    {**FEATURE, "geometry": {"coordinates": [8.2]}},
                    {**FEATURE, "geometry": {"coordinates": ["8.2", 45.6]}},
                ]
            }
        )

        assert len(sensors) == 1
        assert sensors[0].params == frozenset()
        assert sensors[0].other_params == ("nivo_v",)
        assert sensors[0].name == PRAY_SENSOR
        assert sensors[0].page_url().endswith("&param=idro")
        assert sensors[0].page_url(Param.SNOW_DEPTH).endswith("&param=nivo")

    @pytest.mark.parametrize("data", [[], {"features": None}, {"features": []}])
    def test_no_station(self, data: object) -> None:
        """Test that a list without stations is an error."""
        with pytest.raises(ArpaPiemonteParseError):
            parse_sensors(data)


class TestSeries:
    """A file of a quantity of a station."""

    def test_real_level(self) -> None:
        """Test the real level of Pray, with its thresholds and validation."""
        series = parse_series(
            real_json("idro_002105900.geojson"), Param.LEVEL, PRAY_SENSOR
        )

        assert series.name == "PRAY SESSERA"
        assert series.thresholds == Thresholds(2.3, 3.0, 3.8)
        assert series.hydrometric_zero == 400.7
        assert series.description == "Livello idrometrico"
        assert len(series) == 147
        times = [reading.time for reading in series]
        assert times == sorted(times)
        latest = series.latest()
        assert latest is not None
        assert (latest.time, latest.value) == (utc(2026, 11, 17, 2), 0.86)
        assert latest.validation is Validation.TO_VERIFY
        assert latest.valid_type == "VTA"
        assert series.latest({Validation.OK}) is not latest

    def test_real_temperature_has_no_thresholds(self) -> None:
        """Test that only the level has thresholds."""
        series = parse_series(real_json("terma_002105900.geojson"), Param.TEMPERATURE)

        assert series.thresholds is None
        assert series.page_url.endswith("&param=terma")

    def test_real_snow_without_values(self) -> None:
        """Test that invalid and missing cells, without value, are not readings."""
        data = real_json("nivo_001019900.geojson")
        series = parse_series(data, Param.SNOW_DEPTH)

        assert isinstance(data, dict)
        assert len(series) < len(data["properties"]["nivo"])
        assert all(reading.validation is not Validation.MISSING for reading in series)

    def test_real_rain_is_of_10_minutes(self) -> None:
        """Test that the rain files say they are of 10 minutes."""
        series = parse_series(real_json("pluv_001013900.geojson"), Param.RAIN_10_MIN)

        assert series.description == "Livello pioggia sui 10 minuti"

    def test_invalid_reading_with_value_is_skipped_by_latest(self) -> None:
        """Test that the latest reading skips an invalid one."""
        series = parse_series(
            level_file(
                {
                    "2026-11-17T01:00": {"value": 1, "valid_type": "OK"},
                    "2026-11-17T02:00": {"value": 9.0, "valid_type": "AIC"},
                    "2026-11-17T03:00": {"value": None, "valid_type": "MMM"},
                }
            ),
            Param.LEVEL,
        )

        assert [reading.value for reading in series] == [1.0, 9.0]
        latest = series.latest()
        assert latest is not None
        assert latest.value == 1.0
        assert series.thresholds == Thresholds()
        assert series.name == PRAY_SENSOR

    @pytest.mark.parametrize(
        "data",
        [
            [],
            {"properties": None},
            level_file({}, sensor=None),
            {"properties": {"sensor": PRAY_SENSOR}},
            level_file({"2026-11-17T01:00": 1.0}),
            level_file({"2026-11-17T01:00": {"value": "1.0"}}),
            level_file({"17/11/2026 01:00": {"value": 1.0}}),
        ],
    )
    def test_unexpected_format(self, data: object) -> None:
        """Test that an unexpected file is an error."""
        with pytest.raises(ArpaPiemonteParseError):
            parse_series(data, Param.LEVEL)

    def test_wrong_station(self) -> None:
        """Test that the file must be of the station asked for."""
        with pytest.raises(ArpaPiemonteParseError, match="002105900"):
            parse_series(level_file({}), Param.LEVEL, "002105901")


class TestRealtime:
    """The api_realtime."""

    def test_real_stations(self) -> None:
        """Test the real stations, with the identifiers on the website."""
        stations = parse_pie_anag(real_json("pie_anag.json"))

        assert len(stations) == 374
        pray = next(station for station in stations if station.station_code == PRAY)
        assert pray.sensor_id == PRAY_SENSOR
        assert pray.municipality_code == "096050"
        assert pray.thresholds == Thresholds(2.3, 3.0, 3.8)
        assert pray.hydrometric_zero == 400.7
        assert pray.river == "SESSERA"
        rain_gauge = next(s for s in stations if s.station_code == "001")
        assert rain_gauge.river is None
        assert sum(station.river is None for station in stations) == 264

    def test_station_identifier(self) -> None:
        """Test the identifier on the website, from text or broken values."""
        stations = parse_pie_anag(
            [
                {**ANAG, "progr_punto_com": "5"},
                {**ANAG, "station_code": "189", "progr_punto_com": None},
                {**ANAG, "station_code": "190", "codice_istat_comune": "2105"},
                {**ANAG, "station_code": "191", "lat": None},
                {**ANAG, "id_network": "LIG"},
                "not a station",
            ]
        )

        assert [station.sensor_id for station in stations] == ["002105005", None, None]
        assert stations[0].thresholds == Thresholds()
        assert stations[0].station_type == "IPT"

    @pytest.mark.parametrize("data", [{}, [], [{**ANAG, "id_network": "VDA"}]])
    def test_no_station(self, data: object) -> None:
        """Test that no station of Piedmont is an error."""
        with pytest.raises(ArpaPiemonteParseError):
            parse_pie_anag(data)

    def test_real_records(self) -> None:
        """Test the real records of Pray, in UTC."""
        records, pages = parse_data_pie_page(real_json("data_pie_188.json"), PRAY)

        assert pages == 1
        assert len(records) == 74
        last = records[-1]
        assert last.time == utc(2026, 11, 16, 23)
        assert last.get(RealtimeField.HYDROMETRIC_LEVEL) == 0.88
        assert last.get(RealtimeField.HUMIDITY) is None

    def test_unknown_station(self) -> None:
        """Test that a station the api_realtime does not know has no records."""
        assert parse_data_pie_page(real_json("data_pie_999.json"), "999") == ([], 0)
        assert parse_data_pie_page({"total_pages": None, "data": None}, "999") == (
            [],
            0,
        )

    def test_records_of_other_stations_are_left_out(self) -> None:
        """Test that records of other stations are left out."""
        records, _ = parse_data_pie_page(
            {
                "total_pages": 1,
                "data": [
                    {"station_code": "189", "date": "2026-11-17T00:00:00+01:00"},
                    "not a record",
                    {
                        "station_code": PRAY,
                        "date": "2026-11-17T00:00:00+01:00",
                        "wind": 3,
                    },
                ],
            },
            PRAY,
        )

        assert len(records) == 1
        assert records[0].get(RealtimeField.WIND) == 3.0

    @pytest.mark.parametrize(
        "data",
        [
            [],
            {"total_pages": "1"},
            {"total_pages": True},
            {"total_pages": 1, "data": {}},
            {"total_pages": 1, "data": [{"station_code": PRAY}]},
            {"total_pages": 1, "data": [{"station_code": PRAY, "date": "yesterday"}]},
            {
                "total_pages": 1,
                "data": [{"station_code": PRAY, "date": "2026-11-17T00:00"}],
            },
            {
                "total_pages": 1,
                "data": [
                    {"station_code": PRAY, "date": "2026-11-17T00:00Z", "wind": "3"},
                ],
            },
        ],
    )
    def test_unexpected_page(self, data: object) -> None:
        """Test that an unexpected page is an error."""
        with pytest.raises(ArpaPiemonteParseError):
            parse_data_pie_page(data, PRAY)

    def test_status(self) -> None:
        """Test the status of the api_realtime."""
        assert parse_status(real_json("status.json")) == "healthy"
        with pytest.raises(ArpaPiemonteParseError):
            parse_status({"status": ""})


@pytest.mark.parametrize(
    ("value", "number"),
    [
        ("2.3", 2.3),
        ("3", 3.0),
        (" 2,5 ", 2.5),
        ("", None),
        ("n/d", None),
        ("nan", None),
        (2, 2.0),
        (math.inf, None),
        (True, None),
        (None, None),
    ],
)
def test_parse_decimal(value: object, number: float | None) -> None:
    """Test numbers written as texts."""
    assert parse_decimal(value) == number
