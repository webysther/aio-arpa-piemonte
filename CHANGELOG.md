# Changelog

All notable changes to aioarpapiemonte are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html): before 1.0, a
minor version may change the API.

## [0.2.0] - 2026-11-18

### Added

- The natural risks. `get_municipality_alerts()`: the alerts of a
  municipality from its widget, the level of each risk today and tomorrow, the
  danger now and the operational phase it declared, also by date
  (`level_on()`), since the bulletin of the day comes out around 13:00.
- `get_earthquakes()`: the earthquakes of the last 30 days, with their
  distance from a position (`Earthquake.distance_km()`).
- `get_heat_forecast()`: the heat-wave bulletin of a provincial capital
  (`HeatCity`, with `capital_of()` and `nearest()`).
- `get_avalanche_bulletin()`: the avalanche bulletins of AINEVA by
  micro-region, from EAWS, with `get_micro_region()` and `micro_region_at()`:
  the micro-region of a position, from the micro-regions of EAWS shipped with
  the package, and their names (`MICRO_REGION_NAMES`).
- `distance_km()`, between two positions.

## [0.1.1] - 2026-11-17

### Fixed

- The river of a station without a hydrometer in the api_realtime is `None`,
  as in the list of the website, instead of `"-"`.

## [0.1.0] - 2026-11-17

First release.

### Added

- `ArpaPiemonteClient`: the stations and the hourly readings of the files of
  the Arpa website, with their validation and the thresholds of the
  hydrometers, with conditional requests; the stations, records and status of
  the api_realtime.
- `sensor_id()`: the identifier of a station on the website, from the
  api_realtime.

[0.2.0]: https://github.com/webysther/aio-arpa-piemonte/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/webysther/aio-arpa-piemonte/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/webysther/aio-arpa-piemonte/releases/tag/v0.1.0
