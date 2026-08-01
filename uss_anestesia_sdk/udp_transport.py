#!/usr/bin/env python3
"""
Scoped IPv6 UDP transport for Philips IntelliVue Data Export.
"""

from __future__ import annotations

import socket

from transport import ConnectionTarget


class IPv6UDPTransport:
    """Synchronous scoped IPv6 UDP transport."""

    def __init__(
        self,
        target: ConnectionTarget,
        *,
        local_port: int = 0,
    ) -> None:
        if not 0 <= local_port <= 65535:
            raise ValueError("local_port debe estar entre 0 y 65535")

        self.target = target
        self.local_port = local_port
        self._socket: socket.socket | None = None

    @property
    def opened(self) -> bool:
        return self._socket is not None

    @property
    def socket(self) -> socket.socket:
        if self._socket is None:
            raise RuntimeError("El transporte UDP no está abierto")
        return self._socket

    def open(self) -> None:
        if self._socket is not None:
            raise RuntimeError("El transporte UDP ya está abierto")

        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

        local_address = (
            "::",
            self.local_port,
            0,
            self.target.interface_index,
        )

        try:
            sock.bind(local_address)
        except Exception:
            sock.close()
            raise

        self._socket = sock

    def send(self, data: bytes) -> int:
        if not isinstance(data, bytes):
            raise TypeError("data debe ser bytes")

        if not data:
            raise ValueError("No se puede enviar un datagrama vacío")

        destination = (
            self.target.host,
            self.target.port,
            0,
            self.target.interface_index,
        )

        return self.socket.sendto(data, destination)

    def receive(
        self,
        *,
        timeout: float,
        max_bytes: int = 65535,
    ) -> tuple[bytes, tuple] | None:
        if timeout <= 0:
            raise ValueError("timeout debe ser mayor que cero")

        if max_bytes < 1:
            raise ValueError("max_bytes debe ser al menos 1")

        self.socket.settimeout(timeout)

        try:
            return self.socket.recvfrom(max_bytes)
        except socket.timeout:
            return None

    def close(self) -> None:
        sock = self._socket
        self._socket = None

        if sock is not None:
            sock.close()

    def __enter__(self) -> "IPv6UDPTransport":
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()