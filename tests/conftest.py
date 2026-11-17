"""Fixtures of the aioarpapiemonte tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import trustme

from aioarpapiemonte import ArpaPiemonteClient

from .server import FakeArpa

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import aiohttp


@pytest.fixture(scope="session")
def ca() -> trustme.CA:
    """Return the certificate authority of the local server."""
    return trustme.CA()


@pytest.fixture
async def arpa(ca: trustme.CA) -> AsyncIterator[FakeArpa]:
    """Run a local server answering for the hosts of Arpa Piemonte."""
    server = FakeArpa(ca)
    await server.start()
    yield server
    await server.close()


@pytest.fixture
async def session(arpa: FakeArpa) -> AsyncIterator[aiohttp.ClientSession]:
    """Return an aiohttp session reaching the local server."""
    async with arpa.client_session() as client_session:
        yield client_session


@pytest.fixture
def client(session: aiohttp.ClientSession) -> ArpaPiemonteClient:
    """Return a client using the injected session."""
    return ArpaPiemonteClient(session)
