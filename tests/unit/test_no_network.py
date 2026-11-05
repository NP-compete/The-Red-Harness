"""A unit test that reaches the network fails (E26-T5)."""

from __future__ import annotations

import socket

import pytest

from tests.unit.conftest import NetworkUsedInAUnitTest


class TestTheGuard:
    def test_leaving_the_machine_is_refused(self):
        with pytest.raises(NetworkUsedInAUnitTest, match="example.com"):
            socket.create_connection(("example.com", 80), timeout=2)

    def test_the_refusal_says_what_to_do_instead(self):
        with pytest.raises(NetworkUsedInAUnitTest, match="tests/integration"):
            socket.create_connection(("1.1.1.1", 53), timeout=2)

    def test_loopback_is_still_allowed(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        client = socket.socket()
        try:
            client.connect(server.getsockname())
        finally:
            client.close()
            server.close()

    def test_a_unix_socket_is_allowed(self):
        from tests.unit.conftest import _is_local

        assert _is_local("/tmp/some.sock")


class TestADatastoreIsNotLoopback:
    """TEST-1 says "no network **or a real datastore**"."""

    @pytest.mark.parametrize(
        ("port", "named"),
        [(5432, "postgres"), (6379, "redis"), (27017, "mongodb")],
    )
    def test_a_datastore_port_is_refused(self, port, named):
        with pytest.raises(NetworkUsedInAUnitTest, match=named):
            socket.create_connection(("127.0.0.1", port), timeout=1)

    def test_the_refusal_says_what_to_do_instead(self):
        with pytest.raises(NetworkUsedInAUnitTest, match="Use a fake"):
            socket.create_connection(("127.0.0.1", 5432), timeout=1)

    def test_an_ephemeral_port_is_still_allowed(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        client = socket.socket()
        try:
            client.connect(server.getsockname())
        finally:
            client.close()
            server.close()
