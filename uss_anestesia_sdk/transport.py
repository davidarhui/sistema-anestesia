#!/usr/bin/env python3
"""
IPv6 TCP transport for Philips IntelliVue communication.

This module is responsible only for:
- Validating IPv6 addresses.
- Opening a scoped IPv6 TCP connection.
- Sending complete byte sequences.
- Receiving data with a timeout.

It does not interpret IntelliVue protocol messages.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionTarget:
    """Destination information for a scoped IPv6 TCP connection."""

    host: str
    port: int
    interface: str
    interface_index: int
    source: str


def normalize_ipv6_host(host: str) -> str:
    """
    Normalize an IPv6 address.

    Accepted examples:
        fe80::209:fbff:fe88:c595
        fe80::209:fbff:fe88:c595%en8
        [fe80::209:fbff:fe88:c595%en8]

    Returns the address without brackets or zone identifier.
    """
    value = host.strip()

    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]

    if "%" in value:
        value, _zone = value.rsplit("%", 1)

    try:
        socket.inet_pton(socket.AF_INET6, value)
    except OSError as exc:
        raise ValueError(f"Dirección IPv6 inválida: {host!r}") from exc

    return value


def interface_index(interface: str) -> int:
    """Return the operating-system index for a network interface."""
    try:
        return socket.if_nametoindex(interface)
    except OSError as exc:
        raise RuntimeError(
            f"No existe la interfaz {interface!r}: {exc}"
        ) from exc


def create_target(
    host: str,
    port: int,
    interface: str,
    *,
    source: str = "manual",
    scope_id: int | None = None,
) -> ConnectionTarget:
    """Build and validate a connection target."""
    if not 1 <= port <= 65535:
        raise ValueError("El puerto debe estar entre 1 y 65535")

    resolved_interface_index = interface_index(interface)

    return ConnectionTarget(
        host=normalize_ipv6_host(host),
        port=port,
        interface=interface,
        interface_index=scope_id or resolved_interface_index,
        source=source,
    )


class IPv6TCPTransport:
    """
    Small synchronous TCP transport.

    The transport owns the socket and can be used as a context manager:

        with IPv6TCPTransport(target) as transport:
            transport.send_all(packet)
            response = transport.receive()
    """

    def __init__(
        self,
        target: ConnectionTarget,
        *,
        connect_timeout: float = 5.0,
    ) -> None:
        if connect_timeout <= 0:
            raise ValueError("connect_timeout debe ser mayor que cero")

        self.target = target
        self.connect_timeout = connect_timeout
        self._socket: socket.socket | None = None

    @property
    def connected(self) -> bool:
        return self._socket is not None

    @property
    def socket(self) -> socket.socket:
        if self._socket is None:
            raise RuntimeError("El transporte TCP no está conectado")
        return self._socket

    def connect(self) -> None:
        """Open the scoped IPv6 TCP connection."""
        if self._socket is not None:
            raise RuntimeError("El transporte TCP ya está conectado")

        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.settimeout(self.connect_timeout)

        destination = (
            self.target.host,
            self.target.port,
            0,
            self.target.interface_index,
        )

        try:
            sock.connect(destination)
        except Exception:
            sock.close()
            raise

        self._socket = sock

    def send_all(self, data: bytes) -> None:
        """Send all bytes or raise an exception."""
        if not isinstance(data, bytes):
            raise TypeError("data debe ser bytes")

        if not data:
            raise ValueError("No se puede enviar un paquete vacío")

        self.socket.sendall(data)

    def receive(
        self,
        *,
        timeout: float,
        max_bytes: int = 65535,
    ) -> bytes:
        """
        Receive one TCP chunk.

        Returns b"" when the timeout expires or when the peer closes
        the connection.
        """
        if timeout <= 0:
            raise ValueError("timeout debe ser mayor que cero")

        if max_bytes < 1:
            raise ValueError("max_bytes debe ser al menos 1")

        self.socket.settimeout(timeout)

        try:
            return self.socket.recv(max_bytes)
        except socket.timeout:
            return b""

    def close(self) -> None:
        """Close the socket cleanly."""
        sock = self._socket
        self._socket = None

        if sock is None:
            return

        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            sock.close()

    def __enter__(self) -> "IPv6TCPTransport":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()