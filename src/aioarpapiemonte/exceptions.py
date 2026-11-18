"""Exceptions raised by aioarpapiemonte."""

from __future__ import annotations


class ArpaPiemonteError(Exception):
    """Base class of the aioarpapiemonte errors."""


class ArpaPiemonteConnectionError(ArpaPiemonteError):
    """Arpa Piemonte could not be reached: network error, HTTP error or timeout."""


class ArpaPiemonteParseError(ArpaPiemonteError):
    """Arpa Piemonte answered data that is not valid JSON or has another format."""


class ArpaPiemonteNotFoundError(ArpaPiemonteError):
    """The file does not exist (HTTP 404).

    A station does not publish every quantity it has a sensor for: the wind
    speed of a station can be ``vels`` instead of ``velv``. An avalanche
    bulletin does not exist out of season. Retrying the same request does not
    help.
    """
