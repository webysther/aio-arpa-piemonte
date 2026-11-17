# AGENTS.md: aioarpapiemonte

Guidance for AI coding agents and contributors working on this repository.
`CLAUDE.md` imports this file.

aioarpapiemonte is an async Python client (asyncio, aiohttp) for the official
real-time data of the stations of Arpa Piemonte: the files of the Arpa
website (hourly, with validation) and the api_realtime (documented, a few
hours later). It is fully typed, has no Home Assistant dependency and is
published to PyPI.

Its main user is the Home Assistant integration ARPA Piemonte
(`arpa_piemonte`), which pins an exact version and reads these sources when
[aiometeo3r](https://github.com/webysther/aio-meteo3r) (Meteo 3R, its primary
source) fails. Parsing and HTTP fixes of these sources belong here; Home
Assistant code and the fallback belong in the integration.

## Ground rules

- **Do not commit, amend, push, tag, publish or move branches** (`reset`,
  `branch -f`, `rebase`). Leave every change uncommitted in the working tree;
  the maintainer reviews and commits it. Read-only git commands are fine.
- Ask before anything that leaves the machine: releases, PRs, issues,
  comments.
- Reply in the language the person writes in. Code, comments, docstrings,
  docs, the changelog and commit messages are in English.
- Check instead of guessing: only the api_realtime is documented. Answer data
  questions by measuring the live files with a throwaway script outside the
  repository, politely (a few requests, with pauses), and write the
  measurement in the docstring of the constant it sets.

## Layout

```text
src/aioarpapiemonte/
  client.py      ArpaPiemonteClient: get_sensors(), get_series() (website);
                 get_realtime_stations(), get_realtime_data(),
                 get_realtime_status() (api_realtime)
  _http.py       ConditionalCache: the latest answer of each URL, with its
                 validators
  parsers.py     pure parsing of the decoded JSON, without I/O
  models.py      frozen dataclasses and enums; exceptions.py
  urls.py        URL builders and sensor_id(), the identifier of a station on
                 the website; const.py
tests/           pytest; tests/server.py is a local HTTPS server standing in
                 for the hosts of Arpa, answering 304 to conditional requests
```

The public API is what `aioarpapiemonte/__init__.py` exports in `__all__`,
plus the documented modules `parsers` and `urls`.

## Checks


```bash
python -m venv .venv && . .venv/bin/activate
pip install --editable . --group dev   # pip >= 25.1
ruff format --check . && ruff check .  # every rule ("ALL"), see pyproject.toml
mypy                                   # strict, src and tests
pytest --cov
npx prettier --check .                 # the YAML of the workflows
```

CI runs the same on Python 3.13 and 3.14. Warnings are errors in pytest. The
coverage gate is 95% with branches; keep it at 100%.

## Tests

- Never reach Arpa Piemonte: `tests/server.py` answers for its hosts over
  HTTPS (certificates from trustme).
- `tests/fixtures/real` holds unmodified files of Arpa Piemonte that guard
  the format: never edit them. Hand-made data is built in the tests.
- Never depend on the current date or time zone of the machine.

## Arpa Piemonte data

Facts that are easy to get wrong (measured on 2026-11-17, see the README):

- A station has two identifiers: its code in the network ("188") and its
  identifier on the website ("002105900"), made of the ISTAT code of its
  municipality when it was set up (it can be an old one) and its number.
  Only `pie_anag` links them (`sensor_id`).
- The files of the website are in UTC; the api_realtime gives an offset.
- The rain files of the website (`pluv`) are of 10 minutes, not of the hour.
- Wind and gust: m/s on the website, km/h in the api_realtime.
- The api_realtime answers `application/problem+json` even with a 200, and a
  query it cannot answer is a 200 whose fields are null.
- Readings marked invalid (A...) or missing (M...) on the website came without
  a value.
- `sensors.geojson` is 617 KB, uncompressed, and its ETag changes every
  cycle: read it to choose a station, not at every update.

## Versioning and releases

- Semantic Versioning: before 1.0 a minor version may change the API.
- To prepare a release, add a `## [X.Y.Z] - Unreleased` section to
  `CHANGELOG.md` ([Keep a Changelog](https://keepachangelog.com/en/1.1.0/)),
  written for the users of the library, with its compare link at the end of
  the file, and set `__version__` in `src/aioarpapiemonte/__init__.py` to `X.Y.Z`.
- The maintainer commits and runs `./publish.sh X.Y.Z [--dry-run]`: it dates
  the section, creates the GitHub release, and the release workflow tests,
  builds and publishes to PyPI (trusted publishing).

## Code style

- Readable, descriptive code over clever code: descriptive names, typed models
  and enums instead of raw dicts, small focused helpers, docstrings that say
  what and why.
- No magic numbers: a `Final` constant whose docstring says where its value
  comes from (see `HOST_RETRY_AFTER`).
- Parsing stays pure and I/O stays in the client.
- Every value of an enum has a numeric `code`; a released code never changes
  and is never reused.
- mypy strict, ruff with every rule. A `# noqa` or `# type: ignore[code]`
  needs a reason.
- Comments explain why, not what.
