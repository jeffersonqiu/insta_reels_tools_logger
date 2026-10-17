"""Fail tests that try to contact external services instead of using mocks."""

import socket

import pytest


@pytest.fixture(autouse=True)
def block_external_connections(monkeypatch):
    # TestClient uses an in-process ASGI transport. Keep Unix sockets available
    # for the event loop, but forbid outbound IPv4/IPv6 connections.
    for method_name in ("connect", "connect_ex"):
        original = getattr(socket.socket, method_name)

        def guarded(sock, address, _original=original):
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                raise AssertionError(f"External connections must be mocked: {address!r}")
            return _original(sock, address)

        monkeypatch.setattr(socket.socket, method_name, guarded)
