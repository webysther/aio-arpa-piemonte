"""Tests of the distances and the avalanche micro-regions."""

from __future__ import annotations

import math

import pytest

from aioarpapiemonte import (
    MICRO_REGION_NAMES,
    ArpaPiemonteParseError,
    distance_km,
    micro_region_at,
    micro_regions,
)
from aioarpapiemonte.geo import EARTH_RADIUS_KM, parse_micro_regions

SQUARE = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]
"""A square of 10 degrees, as longitude and latitude."""
HOLE = [[4.0, 4.0], [6.0, 4.0], [6.0, 6.0], [4.0, 6.0], [4.0, 4.0]]
"""A hole in the middle of the square."""


def feature(
    region_id: object,
    coordinates: object,
    kind: str = "MultiPolygon",
    end_date: str | None = None,
) -> dict[str, object]:
    """Return a feature of a micro-region."""
    return {
        "type": "Feature",
        "properties": {"id": region_id, "start_date": None, "end_date": end_date},
        "geometry": {"type": kind, "coordinates": coordinates},
    }


def test_distance() -> None:
    """Test a degree of a meridian, and the distance from Torino to Pray.

    On the WGS84 ellipsoid, Torino is 78.71 km from Pray (geographiclib).
    """
    assert distance_km(0, 0, 1, 0) == pytest.approx(EARTH_RADIUS_KM * math.pi / 180)
    assert distance_km(45.0764, 7.6821, 45.6739, 8.22167) == pytest.approx(
        78.71, rel=0.005
    )
    assert distance_km(0, 0, 0, 180) == pytest.approx(EARTH_RADIUS_KM * math.pi)


@pytest.mark.parametrize(
    ("place", "latitude", "longitude", "region"),
    [
        ("Bardonecchia", 45.0786, 6.7036, "IT-21-TO-03"),
        ("Sestriere", 44.958, 6.879, "IT-21-TO-03"),
        ("Usseaux", 45.0486, 7.0286, "IT-21-TO-02"),
        ("Ceresole Reale", 45.4333, 7.2333, "IT-21-TO-05"),
        ("Crissolo", 44.6986, 7.1575, "IT-21-CN-05"),
        ("Limone Piemonte", 44.2013, 7.5763, "IT-21-CN-02"),
        ("Macugnaga", 45.9686, 7.9672, "IT-21-VB-01"),
        ("Torino", 45.0703, 7.6869, None),
        ("Pray", 45.6739, 8.22167, None),
    ],
)
def test_micro_region_at(
    place: str, latitude: float, longitude: float, region: str | None
) -> None:
    """Test the micro-region of places, checked with shapely on 2026-11-18."""
    assert micro_region_at(latitude, longitude) == region, place


def test_shipped_micro_regions() -> None:
    """Test that the 14 micro-regions in use are shipped, each with its name."""
    regions = micro_regions()

    assert sorted(region.id for region in regions) == sorted(MICRO_REGION_NAMES)
    assert all(region.name for region in regions)
    assert micro_regions() is regions


def test_hole() -> None:
    """Test that a position in a hole is outside, and the ended ones skipped."""
    (region,) = parse_micro_regions(
        {
            "features": [
                feature("IT-21-XX-01", [SQUARE, HOLE], "Polygon"),
                feature("IT-21-XX-01", [[SQUARE]], end_date="2022-03-04"),
            ]
        }
    )

    assert region.contains(2, 2)
    assert not region.contains(5, 5)
    assert not region.contains(5, 11)
    assert region.name is None


def test_multipolygon() -> None:
    """Test a micro-region of two polygons, and an open ring."""
    other = [[[20.0, 0.0], [30.0, 0.0], [30.0, 10.0], [20.0, 10.0]]]
    (region,) = parse_micro_regions({"features": [feature("A", [[SQUARE], other])]})

    assert region.contains(5, 25)
    assert region.contains(5, 5)
    assert not region.contains(5, 15)


@pytest.mark.parametrize(
    ("data", "match"),
    [
        ([], "no features"),
        ({"features": {}}, "no features"),
        ({"features": []}, "in use"),
        ({"features": [feature("A", [[SQUARE]], end_date="2022")]}, "in use"),
        ({"features": ["A"]}, "not an object"),
        ({"features": [{"properties": {}}]}, "no properties"),
        ({"features": [feature(1, [[SQUARE]])]}, "without identifier"),
        ({"features": [feature("A", [[SQUARE]], "Point")]}, "without identifier"),
        ({"features": [feature("A", "polygons")]}, "without identifier"),
        ({"features": [feature("A", [[]])]}, "no rings"),
        ({"features": [feature("A", [["ring"]])]}, "fewer than 3"),
        ({"features": [feature("A", [[SQUARE[:2]]])]}, "fewer than 3"),
        ({"features": [feature("A", ["ring"])]}, "no rings"),
        ({"features": [feature("A", [[[[0, 0], [1, 1], [0]]]])]}, "Not a point"),
        ({"features": [feature("A", [[[[0, 0], [1, 1], [True, 0]]]])]}, "Not a point"),
        ({"features": [feature("A", [[[[0, 0], [1, 1], "point"]]])]}, "Not a point"),
    ],
)
def test_broken_micro_regions(data: object, match: str) -> None:
    """Test that a file that is not of micro-regions is an error."""
    with pytest.raises(ArpaPiemonteParseError, match=match):
        parse_micro_regions(data)
