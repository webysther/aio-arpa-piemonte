# Changelog

All notable changes to aioarpapiemonte are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html): before 1.0, a
minor version may change the API.

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

[0.1.1]: https://github.com/webysther/aio-arpa-piemonte/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/webysther/aio-arpa-piemonte/releases/tag/v0.1.0
