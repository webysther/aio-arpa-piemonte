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

PIEMONTE_NETWORK: Final = "PIE"
"""Network of the Piedmont stations (``id_network``)."""

ATTRIBUTION: Final = "Fonte: Arpa Piemonte - www.arpa.piemonte.it"
"""Credit the data needs (CC BY 4.0, https://www.arpa.piemonte.it/note-legali)."""

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

REPOSITORY_URL: Final = "https://github.com/webysther/aio-arpa-piemonte"
"""Home of aioarpapiemonte, named in its User-Agent."""
