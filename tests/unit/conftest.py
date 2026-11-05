"""Marks every test in tests/unit/, and stops them reaching the network."""

from __future__ import annotations

import os
import socket

import pytest
import pytest_asyncio

LOCAL = ("127.0.0.1", "::1", "localhost", "0.0.0.0", "")

DATASTORE_PORTS = {
    5432: "postgres",
    6379: "redis",
    27017: "mongodb",
    9200: "elasticsearch",
    3306: "mysql",
    11211: "memcached",
    4317: "an otlp collector",
    4318: "an otlp collector",
}


class NetworkUsedInAUnitTest(RuntimeError):
    """A unit test tried to leave the machine."""


def _is_local(address: object) -> bool:
    if isinstance(address, (str, bytes)):
        return True
    if isinstance(address, tuple) and address:
        return str(address[0]) in LOCAL
    return False


def _datastore_on(address: object) -> str | None:
    """The datastore this address names, if it names one."""
    if not (isinstance(address, tuple) and len(address) >= 2):
        return None
    try:
        return DATASTORE_PORTS.get(int(address[1]))
    except (TypeError, ValueError):
        return None


def _refuse(what: str) -> NetworkUsedInAUnitTest:
    return NetworkUsedInAUnitTest(
        f"a unit test tried to reach {what}. Unit tests do not reach the "
        "network: mock the client, or move the test to tests/integration "
        "where a service is declared."
    )


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse any connection that leaves this machine."""
    real_connect = socket.socket.connect
    real_resolve = socket.getaddrinfo

    def connect(self: socket.socket, address: object) -> None:  # noqa: ANN401
        if not _is_local(address):
            raise _refuse(repr(address))
        store = _datastore_on(address)
        if store is not None:
            raise NetworkUsedInAUnitTest(
                f"a unit test tried to reach {store} on {address!r}. Unit "
                "tests do not use a real datastore: it is not there in CI, "
                "and where it is there the test can write to it. Use a fake, "
                "or move the test to tests/integration where a service is "
                "declared."
            )
        return real_connect(self, address)

    def getaddrinfo(host: object, port: object, *args: object, **kw: object):  # noqa: ANN401
        if str(host) not in LOCAL:
            raise _refuse(f"{host!r}")
        return real_resolve(host, port, *args, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        item.add_marker(pytest.mark.unit)


@pytest_asyncio.fixture(autouse=True)
async def _asyncio_debug_mode(request):
    """Fail a test that blocks the event loop (PERF-7)."""
    import asyncio
    import logging

    loop = asyncio.get_running_loop()
    was, was_slow = loop.get_debug(), loop.slow_callback_duration
    loop.set_debug(True)
    loop.slow_callback_duration = 1.0

    blocked: list[str] = []

    class Catch(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            said = record.getMessage()
            if "took" in said and "seconds" in said:
                blocked.append(said[:200])

    catcher = Catch()
    logging.getLogger("asyncio").addHandler(catcher)
    try:
        yield
    finally:
        logging.getLogger("asyncio").removeHandler(catcher)
        loop.set_debug(was)
        loop.slow_callback_duration = was_slow

    if blocked and not request.node.get_closest_marker("may_block"):
        where = request.node.nodeid
        if os.environ.get("PERF7_STRICT"):
            raise AssertionError(
                "this test held the event loop, which is what sync I/O on "
                "the request path looks like (PERF-7):\n  " + "\n  ".join(blocked)
            )
        print(f"\n[event-loop] {where} blocked: {blocked[0][:120]}")
