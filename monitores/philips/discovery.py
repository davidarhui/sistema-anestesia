from __future__ import annotations

import socket
import struct
from collections.abc import Iterator

from .models import DiscoveryPacket
from .protocol import DISCOVERY_PORT, parse_discovery_packet


MULTICAST_GROUP = "ff02::1"


class DiscoveryListener:
    """
    Escucha pasivamente anuncios IntelliVue por IPv6/UDP 24005.

    En macOS es necesario unirse explícitamente al grupo multicast ff02::1
    en la interfaz física correcta.
    """

    def __init__(self, interface: str = "en8", port: int = DISCOVERY_PORT):
        self.interface = interface
        self.port = port
        self._socket: socket.socket | None = None
        self._interface_index: int | None = None

    def open(self) -> None:
        if self._socket is not None:
            return

        interface_index = socket.if_nametoindex(self.interface)

        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        sock.bind(("::", self.port))

        multicast_address = socket.inet_pton(socket.AF_INET6, MULTICAST_GROUP)
        membership = struct.pack("=16sI", multicast_address, interface_index)
        sock.setsockopt(
            socket.IPPROTO_IPV6,
            socket.IPV6_JOIN_GROUP,
            membership,
        )

        sock.setsockopt(
            socket.IPPROTO_IPV6,
            socket.IPV6_MULTICAST_IF,
            interface_index,
        )

        self._interface_index = interface_index
        self._socket = sock

    def close(self) -> None:
        if self._socket is None:
            return

        if self._interface_index is not None:
            try:
                multicast_address = socket.inet_pton(socket.AF_INET6, MULTICAST_GROUP)
                membership = struct.pack(
                    "=16sI",
                    multicast_address,
                    self._interface_index,
                )
                self._socket.setsockopt(
                    socket.IPPROTO_IPV6,
                    socket.IPV6_LEAVE_GROUP,
                    membership,
                )
            except OSError:
                pass

        self._socket.close()
        self._socket = None
        self._interface_index = None

    def receive(self) -> DiscoveryPacket:
        if self._socket is None:
            self.open()

        assert self._socket is not None
        payload, sender = self._socket.recvfrom(65535)
        return parse_discovery_packet(payload, sender)

    def packets(self) -> Iterator[DiscoveryPacket]:
        self.open()
        while True:
            yield self.receive()

    def __enter__(self) -> "DiscoveryListener":
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
