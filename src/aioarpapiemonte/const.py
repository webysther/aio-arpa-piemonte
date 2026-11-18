"""Constants of aioarpapiemonte."""

from __future__ import annotations

from typing import Final

GEOJSON_BASE_URL: Final = "https://www.arpa.piemonte.it/rischi_naturali/data/tr/"
"""The real-time files of the Arpa website, read by its station pages.

Documented in the "Guida alla lettura dei dati in tempo reale" (v1.0,
2024-10-03): hourly values in UTC, validated automatically, written again
every 15 minutes.
"""

REALTIME_BASE_URL: Final = "https://utility.arpa.piemonte.it/api_realtime/"
"""The api_realtime of Arpa Piemonte (OpenAPI at ``openapi.json``)."""

STATION_PAGE_URL: Final = (
    "https://www.arpa.piemonte.it/rischi_naturali/snippets_arpa_graphs/"
    "dettaglio_stazione/?id={sensor_id}&param={param}"
)
"""The public page of a station on the Arpa website, to link the source."""

RISKS_BASE_URL: Final = "https://www.arpa.piemonte.it/rischi_naturali/"
"""The natural-risk products of the Arpa website: its widgets and earthquakes.

Each widget asks to credit the source and to keep the layout of the widget
of Arpa (``nota_implementazione_widget``): the widget of a municipality,
unless only its bell, the highest alert, is used. The widgets and the list of
earthquakes send an ``ETag`` and a ``Last-Modified``, and are written again
about every 10 minutes (measured on 2026-11-17 and 18).
"""

EAWS_BULLETINS_URL: Final = "https://static.avalanche.report/eaws_bulletins/"
"""The avalanche bulletins of the members of EAWS in CAAML v6, by day.

AINEVA publishes the bulletin of Piedmont (``IT-21``) from December to May,
at about 16:00 UTC for the next day; out of season the file of a day answers
404 (2026-11-17). The files send an ``ETag`` and a ``Last-Modified``. Their
licence is not stated.
"""

PIEMONTE_EAWS_REGION: Final = "IT-21"
"""Piedmont in EAWS: its micro-regions are ``IT-21-<province>-<number>``."""

PIEMONTE_NETWORK: Final = "PIE"
"""Network of the Piedmont stations (``id_network``)."""

ATTRIBUTION: Final = "Fonte: Arpa Piemonte - www.arpa.piemonte.it"
"""Credit the data needs (CC BY 4.0, https://www.arpa.piemonte.it/note-legali)."""

AVALANCHE_ATTRIBUTION: Final = "Fonte: AINEVA Piemonte - bollettini.aineva.it"
"""Credit of the avalanche bulletins: their provider, as each bulletin names it."""

DEFAULT_REQUEST_TIMEOUT: Final = 15.0
"""Seconds to wait for an answer.

Measured on 2026-11-17: the files of the website answered in 0.08 s at the
median (0.13 s for the 617 KB station list, sent uncompressed), and the
api_realtime in 0.6 s for a page of 10,000 records.
"""

DATA_PIE_PAGE_SIZE: Final = 10_000
"""Records per page of the api_realtime, its maximum.

The last 3 days of a station are about 74 records: one page.
"""

MAX_PAGES: Final = 10
"""Pages read at most from the api_realtime, against a server that never ends.

The 3 days of the whole network are 27,750 records (measured on 2026-11-17):
3 pages.
"""

AVALANCHE_BULLETINS_KEPT: Final = 2
"""Avalanche bulletins kept to ask whether they changed: today's and
tomorrow's, published the day before. The bulletin of a past day is not asked
again."""

REPOSITORY_URL: Final = "https://github.com/webysther/aio-arpa-piemonte"
"""Home of aioarpapiemonte, named in its User-Agent."""
