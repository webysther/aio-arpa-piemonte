"""Tests of the models and the identifiers."""

from __future__ import annotations

import pytest

from aioarpapiemonte import (
    LevelStatus,
    Param,
    Reading,
    RealtimeData,
    RealtimeField,
    RealtimeRecord,
    Thresholds,
    Validation,
    sensor_id,
)
from aioarpapiemonte.urls import data_pie_url, series_url

from . import utc

CODED: tuple[type[Param | RealtimeField | Validation | LevelStatus], ...] = (
    Param,
    RealtimeField,
    Validation,
    LevelStatus,
)


@pytest.mark.parametrize("enum", CODED)
def test_codes(enum: type[Param | RealtimeField | Validation | LevelStatus]) -> None:
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
