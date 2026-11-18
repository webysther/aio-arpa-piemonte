"""Positions: distances, and the avalanche micro-regions of Piedmont.

The micro-regions are those of the avalanche bulletins of EAWS for Piedmont
(IT-21): the 14 in use since 2022-03-04. The package ships them as EAWS
publishes them (CC0, https://gitlab.com/eaws/eaws-regions), without the
older ones: the features without ``end_date`` of
``IT-21_micro-regions.geojson``, downloaded from https://regions.avalanches.org
on 2026-11-18, with their names.
"""

from __future__ import annotations

import functools
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from typing import Final

from .exceptions import ArpaPiemonteParseError

EARTH_RADIUS_KM: Final = 6371.0088
"""Mean radius of the Earth (IUGG), in km.

On this sphere, a distance differs from the one on the ellipsoid by less than
0.5%: 250 m in 50 km.
"""

MICRO_REGIONS_FILE: Final = "IT-21_micro-regions.geojson"
"""The micro-regions shipped with the package, in its ``data`` folder."""

MICRO_REGION_NAMES: Final[Mapping[str, str]] = {
    "IT-21-CN-01": "Valli del Monregalese",
    "IT-21-CN-02": "Valli Gesso e Vermenagna",
    "IT-21-CN-03": "Valle Stura",
    "IT-21-CN-04": "Valli Maira e Grana",
    "IT-21-CN-05": "Valli Varaita e Po",
    "IT-21-TO-01": "Valli Germanasca e Pellice",
    "IT-21-TO-02": "Valli Susa e Chisone",
    "IT-21-TO-03": "Alte Valli Susa e Chisone",
    "IT-21-TO-04": "Alpi Graie",
    "IT-21-TO-05": "Alpi Graie di confine",
    "IT-21-VB-01": "Alpi Pennine di Confine",
    "IT-21-VB-02": "Alpi Lepontine Nord",
    "IT-21-VB-03": "Alpi Lepontine Sud",
    "IT-21-VC-01": "Alpi Pennine",
}
"""Names of the micro-regions in use, in Italian, as EAWS gives them
(``micro-regions_names/it.json``, 2026-11-18).

The bulletins name their micro-regions too, but those of 2026-04-18 gave the
names of the micro-regions before 2022-03-04, numbered otherwise (their
IT-21-TO-03 was "Alpi Graie", now IT-21-TO-04), and none to IT-21-TO-05: the
identifiers of the bulletins are the current ones, their names are not read.
"""

_MIN_RING_POINTS: Final = 3
"""Points a ring needs to enclose an area."""

type Ring = tuple[tuple[float, float], ...]
"""A ring of a polygon: its points, as longitude and latitude."""


def distance_km(
    latitude: float, longitude: float, other_latitude: float, other_longitude: float
) -> float:
    """Return the distance between two positions, in km (haversine formula)."""
    phi, other_phi = math.radians(latitude), math.radians(other_latitude)
    half_lambda = math.radians(other_longitude - longitude) / 2
    chord = (
        math.sin((other_phi - phi) / 2) ** 2
        + math.cos(phi) * math.cos(other_phi) * math.sin(half_lambda) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(chord, 1.0)))


@dataclass(frozen=True, slots=True)
class MicroRegion:
    """A micro-region of the avalanche bulletins."""

    id: str
    """Identifier of the micro-region ("IT-21-TO-03")."""
    polygons: tuple[tuple[Ring, ...], ...]
    """Its polygons: each an outer ring, then its holes."""

    @property
    def name(self) -> str | None:
        """Return the name of the micro-region; None for one EAWS did not name."""
        return MICRO_REGION_NAMES.get(self.id)

    def contains(self, latitude: float, longitude: float) -> bool:
        """Return whether a position is in the micro-region."""
        return any(_in_polygon(longitude, latitude, rings) for rings in self.polygons)


def parse_micro_regions(data: object) -> tuple[MicroRegion, ...]:
    """Return the micro-regions in use of a GeoJSON of EAWS: without ``end_date``.

    Raises :class:`ArpaPiemonteParseError` when it has none, or a feature
    that is not a micro-region.
    """
    features = data.get("features") if isinstance(data, Mapping) else None
    if not isinstance(features, list):
        msg = "The micro-regions have no features"
        raise ArpaPiemonteParseError(msg)
    regions = tuple(
        region for feature in features if (region := _micro_region(feature))
    )
    if not regions:
        msg = "No micro-region is in use"
        raise ArpaPiemonteParseError(msg)
    return regions


@functools.cache
def micro_regions() -> tuple[MicroRegion, ...]:
    """Return the micro-regions of Piedmont shipped with the package.

    Reads a file of 190 KB the first time: from an event loop, call it in a
    worker thread, as ``ArpaPiemonteClient.get_micro_region`` does.
    """
    path = resources.files(__package__ or __name__).joinpath("data", MICRO_REGIONS_FILE)
    return parse_micro_regions(json.loads(path.read_bytes()))


def micro_region_at(latitude: float, longitude: float) -> str | None:
    """Return the micro-region of a position; None outside them.

    The micro-regions cover the mountains of Piedmont, not its plains and
    hills. Reads them the first time, see :func:`micro_regions`.
    """
    return next(
        (
            region.id
            for region in micro_regions()
            if region.contains(latitude, longitude)
        ),
        None,
    )


def _micro_region(feature: object) -> MicroRegion | None:
    """Return the micro-region of a feature; None for one no longer in use."""
    if not isinstance(feature, Mapping):
        msg = "A micro-region is not an object"
        raise ArpaPiemonteParseError(msg)
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, Mapping) or not isinstance(geometry, Mapping):
        msg = "A micro-region has no properties or geometry"
        raise ArpaPiemonteParseError(msg)
    if properties.get("end_date") is not None:
        return None
    identifier = properties.get("id")
    coordinates = geometry.get("coordinates")
    polygons = {"Polygon": [coordinates], "MultiPolygon": coordinates}.get(
        str(geometry.get("type"))
    )
    if not isinstance(identifier, str) or not isinstance(polygons, list):
        msg = f"A micro-region without identifier or polygons: {identifier!r}"
        raise ArpaPiemonteParseError(msg)
    return MicroRegion(identifier, tuple(_polygon(polygon) for polygon in polygons))


def _polygon(polygon: object) -> tuple[Ring, ...]:
    if not isinstance(polygon, list) or not polygon:
        msg = "A polygon has no rings"
        raise ArpaPiemonteParseError(msg)
    return tuple(_ring(ring) for ring in polygon)


def _ring(ring: object) -> Ring:
    if not isinstance(ring, list) or len(ring) < _MIN_RING_POINTS:
        msg = "A ring has fewer than 3 points"
        raise ArpaPiemonteParseError(msg)
    return tuple(_point(point) for point in ring)


def _point(point: object) -> tuple[float, float]:
    if (
        isinstance(point, list)
        and len(point) >= 2  # noqa: PLR2004 - longitude and latitude, maybe altitude
        and all(
            isinstance(value, int | float) and not isinstance(value, bool)
            for value in point[:2]
        )
    ):
        return float(point[0]), float(point[1])
    msg = f"Not a point: {point!r}"
    raise ArpaPiemonteParseError(msg)


def _in_polygon(x: float, y: float, rings: tuple[Ring, ...]) -> bool:
    """Return whether a point is in a polygon with holes (the even-odd rule).

    A ray from the point crosses the rings an odd number of times when the
    point is inside the outer ring and outside its holes.
    """
    crossings = 0
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                crossings += 1
    return crossings % 2 == 1
