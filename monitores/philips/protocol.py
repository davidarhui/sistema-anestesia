from __future__ import annotations

import re
import socket
import struct

from .models import DeviceIdentity, DiscoveryPacket, Endpoint

DISCOVERY_PORT = 24005


def find_tag(data: bytes, tag: int) -> list[tuple[int, bytes]]:
    needle = struct.pack(">H", tag)
    results: list[tuple[int, bytes]] = []
    start = 0

    while True:
        index = data.find(needle, start)
        if index < 0:
            break

        if index + 4 <= len(data):
            length = struct.unpack_from(">H", data, index + 2)[0]
            end = index + 4 + length
            if end <= len(data):
                results.append((index, data[index + 4:end]))

        start = index + 1

    return results


def parse_protocol_support(data: bytes) -> list[Endpoint]:
    endpoints: list[Endpoint] = []

    for _, value in find_tag(data, 0xF101):
        if len(value) < 4:
            continue

        count, declared_length = struct.unpack_from(">HH", value, 0)
        entries = value[4:4 + declared_length]

        for index in range(min(count, len(entries) // 8)):
            app, transport, port, options = struct.unpack_from(">HHHH", entries, index * 8)
            endpoints.append(Endpoint(app, transport, port, options))

    return endpoints


def parse_ipv6_addresses(data: bytes) -> list[str]:
    addresses: list[str] = []

    for _, value in find_tag(data, 0xF35E):
        if len(value) >= 16:
            try:
                address = socket.inet_ntop(socket.AF_INET6, value[:16])
            except OSError:
                continue
            if address not in addresses:
                addresses.append(address)

    return addresses


def parse_mac_addresses(data: bytes) -> list[str]:
    """
    Extrae únicamente la MAC del atributo F100.

    No se buscan secuencias OUI arbitrarias en todo el paquete porque la
    representación EUI-64 de IPv6 contiene bytes parecidos a una MAC y puede
    producir falsos positivos.
    """
    addresses: list[str] = []

    for _, value in find_tag(data, 0xF100):
        if len(value) >= 6:
            mac = ":".join(f"{byte:02x}" for byte in value[:6])
            if mac not in addresses:
                addresses.append(mac)

    return addresses


def extract_printable_strings(data: bytes, minimum: int = 4) -> list[str]:
    pattern = rb"[\x20-\x7e]{" + str(minimum).encode() + rb",}"
    values = [m.decode("ascii", errors="replace").strip("\x00").strip() for m in re.findall(pattern, data)]
    result: list[str] = []

    for value in values:
        if value and value not in result:
            result.append(value)

    return result


def infer_identity(strings: list[str], macs: list[str], ipv6: list[str]) -> DeviceIdentity:
    identity = DeviceIdentity(mac_addresses=macs, ipv6_addresses=ipv6)

    for value in strings:
        if value == "Philips":
            identity.manufacturer = value
        elif value.isdigit() and len(value) == 6 and identity.model is None:
            identity.model = value
        elif re.fullmatch(r"[A-Z]{2}[A-Z0-9]{6,}", value) and identity.serial_number is None:
            identity.serial_number = value
        elif value.startswith("S-") and identity.hardware_revision is None:
            identity.hardware_revision = value
        elif re.fullmatch(r"[A-Z]\.\d{2}\.\d{2}(?:\s*-\s*\d+)?", value):
            identity.software_revision = value

    return identity


def parse_discovery_packet(payload: bytes, sender: tuple) -> DiscoveryPacket:
    sender_ip, sender_port, _flowinfo, scope_id = sender
    strings = extract_printable_strings(payload)
    macs = parse_mac_addresses(payload)
    ipv6 = parse_ipv6_addresses(payload)

    return DiscoveryPacket(
        sender_ip=sender_ip,
        sender_port=sender_port,
        scope_id=scope_id,
        payload=payload,
        identity=infer_identity(strings, macs, ipv6),
        endpoints=parse_protocol_support(payload),
        strings=strings,
    )


def hex_dump(data: bytes, width: int = 16) -> str:
    lines: list[str] = []

    for offset in range(0, len(data), width):
        chunk = data[offset:offset + width]
        hex_part = " ".join(f"{byte:02x}" for byte in chunk)
        ascii_part = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
        lines.append(f"{offset:04x}  {hex_part:<{width * 3}}  {ascii_part}")

    return "\n".join(lines)
