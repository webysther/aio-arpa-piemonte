"""Conditional requests: what a host answered before, by URL."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _Entry[T]:
    """A parsed answer and the validators the host sent with it."""

    etag: str | None
    last_modified: str | None
    value: T


class ConditionalCache[T]:
    """The latest parsed answer of each URL, with its validators.

    The files of the Arpa website send an ``ETag`` and a ``Last-Modified``,
    and answer 304 when asked with either (measured on 2026-11-17).
    """

    def __init__(self, limit: int | None = None) -> None:
        """Initialize an empty cache, of at most ``limit`` URLs (the latest)."""
        self._entries: dict[str, _Entry[T]] = {}
        self._limit = limit

    def validators(self, url: str) -> dict[str, str]:
        """Return the headers that ask the host whether the URL changed."""
        entry = self._entries.get(url)
        if entry is None:
            return {}
        headers = {}
        if entry.etag is not None:
            headers["If-None-Match"] = entry.etag
        if entry.last_modified is not None:
            headers["If-Modified-Since"] = entry.last_modified
        return headers

    def get(self, url: str) -> T | None:
        """Return the latest parsed answer of a URL; None when there is none."""
        entry = self._entries.get(url)
        return None if entry is None else entry.value

    def store(
        self, url: str, value: T, *, etag: str | None, last_modified: str | None
    ) -> None:
        """Keep a parsed answer; without validators there is nothing to ask with."""
        self._entries.pop(url, None)
        if etag is None and last_modified is None:
            return
        self._entries[url] = _Entry(etag, last_modified, value)
        if self._limit is not None and len(self._entries) > self._limit:
            del self._entries[next(iter(self._entries))]
