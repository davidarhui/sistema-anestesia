from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Endpoint:
    application_protocol: int
    transport_protocol: int
    port: int
    options: int


@dataclass
class DeviceIdentity:
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    hardware_revision: str | None = None
    software_revision: str | None = None
    mac_addresses: list[str] = field(default_factory=list)
    ipv6_addresses: list[str] = field(default_factory=list)


@dataclass
class DiscoveryPacket:
    sender_ip: str
    sender_port: int
    scope_id: int
    payload: bytes
    identity: DeviceIdentity
    endpoints: list[Endpoint]
    strings: list[str]
