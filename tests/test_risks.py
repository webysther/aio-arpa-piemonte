"""Tests of the parsing and the models of the natural risks."""

from __future__ import annotations

import datetime as dt
import logging

import pytest

from aioarpapiemonte import (
    AlertDay,
    AlertLevel,
    ArpaPiemonteParseError,
    AvalancheBulletin,
    AvalancheDanger,
    DangerRating,
    Earthquake,
    HeatCity,
    HeatLevel,
    OperationalPhase,
    RegionBulletin,
    RiskType,
)
from aioarpapiemonte.parsers import (
    parse_avalanche_bulletin,
    parse_earthquakes,
    parse_heat_forecast,
    parse_municipality_alerts,
)

from . import PRAY_MUNICIPALITY, real_json, utc

WIDGET: dict[str, object] = {
    "nome_comune": "Pray",
    "allerta": "GIALLO",
    "emissione": "2026-11-17T00:00:00+01:00",
    "idrogeologico_day_0": "GIALLO",
    "idrogeologico_day_1": "ARANCIONE",
    "temporali_day_0": "ROSSA",
}
"""A widget of a municipality with alerts, made by hand: only green and white
were seen live."""

EARTHQUAKE: dict[str, object] = {
    "ID evento": "261117064149",
    "Data e ora (UTC)": "2026-11-17 06:42:50",
    "Latitudine (N)": 44.4862,
    "Longitudine (E)": 7.0928,
    "valore": 1.9,
}

HEAT_DAY: dict[str, object] = {"livello_disagio": "2", "temperatura_massima": "34"}

BULLETIN: dict[str, object] = {
    "bulletinID": "f8882e51",
    "regions": [{"regionID": "IT-21-TO-03"}],
    "dangerRatings": [{"mainValue": "high"}],
}


class TestMunicipalityAlerts:
    """The widget of the alerts of a municipality."""

    def test_pray(self) -> None:
        """Test the widget of Pray: all green, avalanches not evaluated."""
        alerts = parse_municipality_alerts(
            real_json("widget_096050.json"), PRAY_MUNICIPALITY
        )

        assert alerts.name == "Pray"
        assert alerts.alert is AlertLevel.GREEN
        assert len(alerts.risks) == 10
        assert alerts.level(RiskType.HYDRAULIC, AlertDay.NEXT_DAY) is AlertLevel.GREEN
        assert (
            alerts.level(RiskType.AVALANCHES, AlertDay.ISSUE_DAY)
            is AlertLevel.NOT_EVALUATED
        )
        assert alerts.highest(AlertDay.ISSUE_DAY) is AlertLevel.GREEN
        assert alerts.current_danger is AlertLevel.GREEN
        assert alerts.current_danger_time == utc(2026, 11, 18, 5, 50) + dt.timedelta(
            seconds=53
        )
        assert alerts.phase is OperationalPhase.NONE
        assert alerts.phase_text == "Nessuna Fase Operativa"
        assert alerts.phase_time == utc(2026, 11, 17, 13, 30) + dt.timedelta(seconds=12)
        assert alerts.bulletin == "334/2026"
        assert alerts.issued == utc(2026, 11, 17, 10, 57) + dt.timedelta(seconds=30)
        assert alerts.issue_day == dt.date(2026, 11, 17)
        assert alerts.next_update == utc(2026, 11, 18, 12)
        assert alerts.zones == ("Piem-B",)

    def test_two_zones(self) -> None:
        """Test that a municipality in two alert zones has both."""
        alerts = parse_municipality_alerts(real_json("widget_005005.json"), "005005")

        assert alerts.zones == ("Piem-G", "Piem-L")

    def test_levels(self) -> None:
        """Test the alert levels, a missing level and a missing time."""
        alerts = parse_municipality_alerts(WIDGET, PRAY_MUNICIPALITY)

        assert alerts.alert is AlertLevel.YELLOW
        assert alerts.highest(AlertDay.NEXT_DAY) is AlertLevel.ORANGE
        assert (
            alerts.level(RiskType.THUNDERSTORMS, AlertDay.ISSUE_DAY) is AlertLevel.RED
        )
        assert alerts.level(RiskType.SNOW, AlertDay.ISSUE_DAY) is AlertLevel.UNKNOWN
        assert alerts.current_danger is AlertLevel.UNKNOWN
        assert alerts.phase is OperationalPhase.UNKNOWN
        assert alerts.issued is None
        assert alerts.zones == ()
        assert alerts.highest(AlertDay.ISSUE_DAY).is_alert

    def test_days_by_date(self) -> None:
        """Test that before the next bulletin, today is its second day."""
        alerts = parse_municipality_alerts(WIDGET, PRAY_MUNICIPALITY)

        assert alerts.day_of(dt.date(2026, 11, 17)) is AlertDay.ISSUE_DAY
        assert alerts.day_of(dt.date(2026, 11, 18)) is AlertDay.NEXT_DAY
        assert alerts.day_of(dt.date(2026, 11, 19)) is None
        assert (
            alerts.level_on(RiskType.HYDROGEOLOGICAL, dt.date(2026, 11, 18))
            is AlertLevel.ORANGE
        )
        assert (
            alerts.level_on(RiskType.HYDROGEOLOGICAL, dt.date(2026, 11, 19))
            is AlertLevel.UNKNOWN
        )
        assert alerts.highest_on(dt.date(2026, 11, 17)) is AlertLevel.RED
        assert alerts.highest_on(dt.date(2026, 11, 16)) is AlertLevel.UNKNOWN

    def test_without_day_of_issue(self) -> None:
        """Test that without its day of issue, no date has a level."""
        alerts = parse_municipality_alerts(
            {**WIDGET, "emissione": "2026-11-17T00:00:00"}, PRAY_MUNICIPALITY
        )

        assert alerts.issue_day is None
        assert alerts.day_of(dt.date(2026, 11, 17)) is None

    @pytest.mark.parametrize(
        ("text", "phase"),
        [
            ("Attenzione", OperationalPhase.ATTENTION),
            ("PREALLARME", OperationalPhase.PRE_ALARM),
            ("Allarme", OperationalPhase.ALARM),
            ("Evacuazione", OperationalPhase.UNKNOWN),
        ],
    )
    def test_phases(self, text: str, phase: OperationalPhase) -> None:
        """Test the operational phases, whatever their case."""
        alerts = parse_municipality_alerts(
            {**WIDGET, "fase_operativa_comunale_attuata": text}, PRAY_MUNICIPALITY
        )

        assert alerts.phase is phase
        assert alerts.phase_text == text

    def test_unknown_colour(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that a colour aioarpapiemonte does not know is UNKNOWN."""
        caplog.set_level(logging.DEBUG)

        alerts = parse_municipality_alerts(
            {**WIDGET, "allerta": "VIOLA"}, PRAY_MUNICIPALITY
        )

        assert alerts.alert is AlertLevel.UNKNOWN
        assert "VIOLA" in caplog.text

    def test_without_levels(self) -> None:
        """Test that a widget without any level is an error, named by its code."""
        with pytest.raises(ArpaPiemonteParseError, match="no alert"):
            parse_municipality_alerts({"nome_comune": "Pray"}, PRAY_MUNICIPALITY)
        with pytest.raises(ArpaPiemonteParseError, match="not an object"):
            parse_municipality_alerts([], PRAY_MUNICIPALITY)

    def test_name_defaults_to_code(self) -> None:
        """Test that a widget without name is named by the code."""
        alerts = parse_municipality_alerts(
            {"allerta": "VERDE", "emesso_il": "not a time"}, PRAY_MUNICIPALITY
        )

        assert alerts.name == PRAY_MUNICIPALITY
        assert alerts.issued is None


class TestEarthquakes:
    """The earthquakes of the seismic network of Arpa."""

    def test_real_list(self) -> None:
        """Test the real list, newest first, all reviewed local magnitudes."""
        earthquakes = parse_earthquakes(real_json("sismica_tabella.json"))

        assert len(earthquakes) == 28
        assert earthquakes[0] == Earthquake(
            id="261117064149",
            time=utc(2026, 11, 17, 6, 42) + dt.timedelta(seconds=50),
            district="Alpi Cozie",
            latitude=44.4862,
            longitude=7.0928,
            depth=5.8,
            magnitude=1.9,
            magnitude_type="ML",
            reviewed=True,
        )
        assert list(earthquakes) == sorted(
            earthquakes, key=lambda quake: quake.time, reverse=True
        )
        assert all(quake.reviewed for quake in earthquakes)

    def test_minimal_event(self) -> None:
        """Test an event with only time, position and magnitude, and an offset."""
        (quake,) = parse_earthquakes(
            [{**EARTHQUAKE, "Data e ora (UTC)": "2026-11-17T07:42:50+01:00"}]
        )

        assert quake.time == utc(2026, 11, 17, 6, 42) + dt.timedelta(seconds=50)
        assert quake.district is None
        assert quake.depth is None
        assert not quake.reviewed

    @pytest.mark.parametrize(
        "event",
        [
            "not an object",
            {**EARTHQUAKE, "valore": None},
            {**EARTHQUAKE, "Data e ora (UTC)": "yesterday"},
            {**EARTHQUAKE, "Latitudine (N)": "44.5"},
        ],
    )
    def test_broken_event_is_left_out(self, event: object) -> None:
        """Test that an event that cannot be read is left out."""
        assert parse_earthquakes([event, EARTHQUAKE]) == parse_earthquakes([EARTHQUAKE])

    def test_not_a_list(self) -> None:
        """Test that a list that is not a list is an error, and none is fine."""
        with pytest.raises(ArpaPiemonteParseError, match="not a list"):
            parse_earthquakes({})
        assert parse_earthquakes([]) == ()

    def test_distance(self) -> None:
        """Test the distance from a position to the epicentre."""
        quake = parse_earthquakes([EARTHQUAKE])[0]

        assert quake.distance_km(44.4862, 7.0928) == 0
        # 159.13 km on the WGS84 ellipsoid (geographiclib)
        assert quake.distance_km(45.6739, 8.22167) == pytest.approx(159.13, rel=0.005)


class TestHeatForecast:
    """The heat-wave bulletin of a city."""

    def test_torino(self) -> None:
        """Test the last bulletin of Torino of the season."""
        forecast = parse_heat_forecast(real_json("caldo_torino.json"), HeatCity.TORINO)

        assert forecast.issued == utc(2026, 9, 29, 22)
        assert forecast.next_update == utc(2026, 9, 30, 22)
        assert forecast.note is None
        assert [day.day for day in forecast.days] == [
            dt.date(2026, 9, 30),
            dt.date(2026, 10, 1),
            dt.date(2026, 10, 2),
        ]
        first = forecast.days[0]
        assert first.level is HeatLevel.GREEN
        assert first.description == "Nessun disagio"
        assert first.detail is not None
        assert (first.max_temperature, first.min_temperature) == (26, 17)
        assert (first.max_apparent_temperature, first.min_apparent_temperature) == (
            26,
            18,
        )
        assert first.hot_days == 0
        assert forecast.on(dt.date(2026, 10, 1)) is forecast.days[1]
        assert forecast.on(dt.date(2026, 10, 3)) is None

    @pytest.mark.parametrize(
        ("level", "heat"),
        [
            ("1", HeatLevel.YELLOW),
            ("2", HeatLevel.ORANGE),
            ("3", HeatLevel.RED),
            ("4", HeatLevel.UNKNOWN),
            ("1.5", HeatLevel.UNKNOWN),
            ("", HeatLevel.UNKNOWN),
        ],
    )
    def test_levels(self, level: str, heat: HeatLevel) -> None:
        """Test the levels, numbered 0 to 3 by Arpa."""
        forecast = parse_heat_forecast(
            {"ASTI": {"2026-07-01T00:00:00+02:00": {"livello_disagio": level}}},
            HeatCity.ASTI,
        )

        assert forecast.days[0].level is heat
        assert forecast.days[0].hot_days is None

    def test_days_in_order(self) -> None:
        """Test that the days are sorted, whatever their order in the file."""
        forecast = parse_heat_forecast(
            {
                "emissione": "2026-07-01T00:00:00+02:00",
                "note": "Ondata di calore",
                "CUNEO": {
                    "2026-07-02T00:00:00+02:00": HEAT_DAY,
                    "2026-07-01T00:00:00+02:00": {
                        **HEAT_DAY,
                        "giorni_consecutivi_caldo": "3",
                    },
                },
            },
            HeatCity.CUNEO,
        )

        assert [day.day.day for day in forecast.days] == [1, 2]
        assert forecast.days[0].hot_days == 3
        assert forecast.days[1].max_temperature == 34
        assert forecast.note == "Ondata di calore"

    @pytest.mark.parametrize(
        ("data", "match"),
        [
            ({"CUNEO": {}}, "no day"),
            ({"cuneo": {"2026-07-01": HEAT_DAY}}, "not an object"),
            ({"CUNEO": {"July": HEAT_DAY}}, "Not a day"),
            ({"CUNEO": {"2026-07-01": "hot"}}, "not an object"),
            ([], "not an object"),
        ],
    )
    def test_broken(self, data: object, match: str) -> None:
        """Test that a bulletin without the days of the city is an error."""
        with pytest.raises(ArpaPiemonteParseError, match=match):
            parse_heat_forecast(data, HeatCity.CUNEO)


class TestAvalancheBulletin:
    """The avalanche bulletins of EAWS for Piedmont."""

    def test_real_bulletin(self) -> None:
        """Test the bulletins of 2026-04-18: 14 micro-regions in 3 bulletins."""
        bulletin = parse_avalanche_bulletin(real_json("2026-04-18-IT-21.json"))

        assert len(bulletin.regions) == 14
        assert len({region.bulletin_id for region in bulletin.regions}) == 3
        region = bulletin.of_region("IT-21-VB-01")
        assert region is not None
        assert region.danger is AvalancheDanger.CONSIDERABLE
        assert region.danger.scale == 3
        assert region.ratings[0] == DangerRating(
            AvalancheDanger.LOW, upper_bound="2600", period="earlier"
        )
        assert region.problems[0].problem_type == "persistent_weak_layers"
        assert region.problems[0].aspects == ("NW", "NE", "N", "E")
        assert region.problems[0].lower_bound == "2600"
        assert region.problems[0].size == 2
        assert region.problems[0].frequency == "some"
        assert region.problems[0].stability == "poor"
        assert region.tendency == "decreasing"
        assert region.published == utc(2026, 4, 17, 15)
        assert region.valid_from == utc(2026, 4, 17, 22)
        assert region.valid_to == utc(2026, 4, 18, 22)
        assert region.highlights is not None
        assert bulletin.of_region("IT-21-XX-01") is None

    def test_other_members_are_left_out(self) -> None:
        """Test that only the micro-regions of Piedmont are kept."""
        bulletin = parse_avalanche_bulletin(
            {
                "bulletins": [
                    {
                        **BULLETIN,
                        "regions": [
                            {"regionID": "IT-23-AO-01"},
                            {"regionID": "IT-21-TO-03"},
                            "IT-21-TO-04",
                            {"name": "Alpi Graie"},
                        ],
                    }
                ]
            }
        )

        assert [region.region_id for region in bulletin.regions] == ["IT-21-TO-03"]

    def test_sparse_bulletin(self) -> None:
        """Test a bulletin with only its micro-region and a danger."""
        bulletin = parse_avalanche_bulletin(
            {
                "bulletins": [
                    {
                        **BULLETIN,
                        "dangerRatings": [
                            {"mainValue": "no_rating"},
                            {"mainValue": "high", "elevation": "high"},
                            "very_high",
                        ],
                        "avalancheProblems": [
                            {"aspects": ["N"]},
                            "wind_slab",
                            {"problemType": "wind_slab", "aspects": ["N", 1]},
                        ],
                        "tendency": ["steady", {"validTime": {}}],
                        "validTime": "today",
                    }
                ]
            }
        )

        (region,) = bulletin.regions
        assert region.danger is AvalancheDanger.HIGH
        assert [rating.danger for rating in region.ratings] == [
            AvalancheDanger.UNKNOWN,
            AvalancheDanger.HIGH,
        ]
        assert region.ratings[1].lower_bound is None
        assert len(region.problems) == 1
        assert region.problems[0].aspects == ("N",)
        assert region.problems[0].size is None
        assert region.tendency is None
        assert region.valid_from is None
        assert region.published is None
        assert region.highlights is None

    @pytest.mark.parametrize(
        ("data", "match"),
        [
            ({}, "no micro-region"),
            ({"bulletins": "none"}, "no micro-region"),
            ({"bulletins": [{**BULLETIN, "regions": []}]}, "no micro-region"),
            ({"bulletins": ["bulletin"]}, "not an object"),
            ([], "not an object"),
        ],
    )
    def test_broken(self, data: object, match: str) -> None:
        """Test that a file without a micro-region of Piedmont is an error."""
        with pytest.raises(ArpaPiemonteParseError, match=match):
            parse_avalanche_bulletin(data)

    def test_danger_without_ratings(self) -> None:
        """Test that a bulletin without ratings has an UNKNOWN danger."""
        region = RegionBulletin("IT-21-TO-03", None, None, None, None, (), (), None)

        assert region.danger is AvalancheDanger.UNKNOWN
        assert region.danger.scale is None
        assert AvalancheBulletin((region,)).of_region("IT-21-TO-03") is region
