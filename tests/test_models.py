"""Tests of the models and the identifiers."""

from __future__ import annotations

import datetime as dt

import pytest

from aioarpapiemonte import (
    AlertDay,
    AlertLevel,
    AvalancheDanger,
    HeatCity,
    HeatLevel,
    LevelStatus,
    OperationalPhase,
    Param,
    Reading,
    RealtimeData,
    RealtimeField,
    RealtimeRecord,
    RiskType,
    Thresholds,
    Validation,
    sensor_id,
)
from aioarpapiemonte.urls import (
    avalanche_bulletin_url,
    data_pie_url,
    earthquakes_url,
    heat_forecast_url,
    municipality_alerts_url,
    series_url,
)

from . import PRAY_MUNICIPALITY, utc

type Coded = (
    Param
    | RealtimeField
    | RiskType
    | HeatCity
    | Validation
    | LevelStatus
    | AlertLevel
    | AlertDay
    | OperationalPhase
    | HeatLevel
    | AvalancheDanger
)

CODED: tuple[type[Coded], ...] = (
    Param,
    RealtimeField,
    RiskType,
    HeatCity,
    Validation,
    LevelStatus,
    AlertLevel,
    AlertDay,
    OperationalPhase,
    HeatLevel,
    AvalancheDanger,
)


@pytest.mark.parametrize("enum", CODED)
def test_codes(enum: type[Coded]) -> None:
    """Test that codes are unique and give their value back."""
    codes = [member.code for member in enum]

    assert len(set(codes)) == len(codes)
    assert all(enum.from_code(member.code) is member for member in enum)
    assert enum.from_code(-1) is None


def test_units() -> None:
    """Test that every quantity has its unit, wind in km/h in the api_realtime."""
    assert all(param.unit for param in Param)
    assert all(field.unit for field in RealtimeField)
    assert Param.WIND_SPEED.unit == "m/s"
    assert RealtimeField.WIND.unit == "km/h"


@pytest.mark.parametrize(
    ("valid_type", "validation"),
    [
        ("OK", Validation.OK),
        ("VTA", Validation.TO_VERIFY),
        ("WTB", Validation.SUSPECT),
        ("AIC", Validation.INVALID),
        ("MMM", Validation.MISSING),
        ("", Validation.MISSING),
        (None, Validation.MISSING),
        ("XYZ", Validation.UNKNOWN),
    ],
)
def test_validation(valid_type: str | None, validation: Validation) -> None:
    """Test the validation of each kind of code."""
    assert Validation.of(valid_type) is validation


def test_validation_prints_its_name() -> None:
    """Test that a validation prints as its name."""
    assert str(Validation.TO_VERIFY) == "to_verify"
    assert f"{Validation.OK:>3}" == " ok"


@pytest.mark.parametrize(
    ("thresholds", "level", "status"),
    [
        (Thresholds(2.3, 3.0, 3.8), 0.86, LevelStatus.NORMAL),
        (Thresholds(2.3, 3.0, 3.8), 3.0, LevelStatus.GUARD),
        (Thresholds(2.3, 3.0, 3.8), 3.8, LevelStatus.DANGER),
        (Thresholds(2.3, None, None), 2.5, LevelStatus.PRE_ALARM),
        (Thresholds(), 2.5, LevelStatus.UNKNOWN),
    ],
)
def test_threshold_status(
    thresholds: Thresholds, level: float, status: LevelStatus
) -> None:
    """Test the level against the thresholds."""
    assert thresholds.status(level) is status


def test_latest_record_value() -> None:
    """Test the latest value of a field, skipping records without it."""
    data = RealtimeData(
        "188",
        (
            RealtimeRecord(utc(2026, 11, 16, 22), ((RealtimeField.WIND, 3.0),)),
            RealtimeRecord(utc(2026, 11, 16, 23), ()),
        ),
    )

    assert data.latest(RealtimeField.WIND) == Reading(utc(2026, 11, 16, 22), 3.0)
    assert data.latest(RealtimeField.HUMIDITY) is None


@pytest.mark.parametrize(
    ("municipality", "number", "identifier"),
    [("002105", 900, "002105900"), ("001019", 5, "001019005")],
)
def test_sensor_id(municipality: str, number: int, identifier: str) -> None:
    """Test the identifier of a station on the website."""
    assert sensor_id(municipality, number) == identifier


@pytest.mark.parametrize(
    ("municipality", "number"), [("2105", 900), ("002105", 1000), ("002105", -1)]
)
def test_invalid_sensor_id(municipality: str, number: int) -> None:
    """Test that a broken identifier is refused."""
    with pytest.raises(ValueError, match="Invalid station"):
        sensor_id(municipality, number)


@pytest.mark.parametrize("station", ["00210590", "../002105900", "PIE_188"])
def test_invalid_series_url(station: str) -> None:
    """Test that a broken station identifier is refused."""
    with pytest.raises(ValueError, match="Invalid station identifier"):
        series_url(Param.LEVEL, station)


def test_data_pie_url() -> None:
    """Test the URL of a page of records."""
    assert data_pie_url("188", 2).endswith(
        "/data_pie?station_code=188&page_size=10000&page=2"
    )
    with pytest.raises(ValueError, match="Invalid station code"):
        data_pie_url("18 8")


def test_alert_levels() -> None:
    """Test that the levels compare, and alert from yellow."""
    assert AlertLevel.RED > AlertLevel.ORANGE > AlertLevel.YELLOW > AlertLevel.GREEN
    assert AlertLevel.GREEN > AlertLevel.NOT_EVALUATED > AlertLevel.UNKNOWN
    assert [level for level in AlertLevel if level.is_alert] == [
        AlertLevel.YELLOW,
        AlertLevel.ORANGE,
        AlertLevel.RED,
    ]
    assert str(AlertLevel.NOT_EVALUATED) == "not_evaluated"


def test_heat_levels() -> None:
    """Test the levels of discomfort as Arpa numbers them."""
    assert [level.arpa_level for level in HeatLevel] == [None, 0, 1, 2, 3]
    assert HeatLevel.of_arpa(0) is HeatLevel.GREEN
    assert HeatLevel.of_arpa(None) is HeatLevel.UNKNOWN


def test_avalanche_scale() -> None:
    """Test the European scale of the avalanche danger."""
    assert [danger.scale for danger in AvalancheDanger] == [None, None, 1, 2, 3, 4, 5]


@pytest.mark.parametrize(
    ("municipality", "city"),
    [
        (PRAY_MUNICIPALITY, HeatCity.BIELLA),
        ("001272", HeatCity.TORINO),
        ("103001", HeatCity.VERBANIA),
        ("002105", HeatCity.VERCELLI),
        ("018001", None),
    ],
)
def test_capital_of(municipality: str, city: HeatCity | None) -> None:
    """Test the capital of the province of a municipality; none in Pavia."""
    assert HeatCity.capital_of(municipality) is city


def test_heat_cities() -> None:
    """Test that each city is the nearest to itself, and Pray nearest to Biella."""
    assert all(
        HeatCity.nearest(city.latitude, city.longitude) is city for city in HeatCity
    )
    assert HeatCity.nearest(45.6739, 8.22167) is HeatCity.BIELLA
    assert HeatCity.NOVARA.municipality_code == "003106"
    assert HeatCity.NOVARA.province_code == "003"


def test_risk_urls() -> None:
    """Test the URLs of the natural risks."""
    assert municipality_alerts_url(PRAY_MUNICIPALITY) == (
        "https://www.arpa.piemonte.it/rischi_naturali/widget/comuni/096050/index.json"
    )
    assert earthquakes_url().endswith(
        "/rischi_naturali/data/sismica/sismica_tabella.json"
    )
    assert heat_forecast_url(HeatCity.TORINO).endswith(
        "/widget/caldo/torino/index.json"
    )
    assert avalanche_bulletin_url(dt.date(2026, 4, 18)) == (
        "https://static.avalanche.report/eaws_bulletins/2026-04-18/2026-04-18-IT-21.json"
    )


@pytest.mark.parametrize("code", ["96050", "0960500", "../096050", "ABCDEF"])
def test_invalid_municipality_code(code: str) -> None:
    """Test that a municipality code that is not 6 digits is refused."""
    with pytest.raises(ValueError, match="Invalid municipality code"):
        municipality_alerts_url(code)
