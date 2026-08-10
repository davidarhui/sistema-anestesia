#!/usr/bin/env python3
"""
Philips IntelliVue MX450/MX500 discovery listener (IPv6 / UDP 24005).

Research / development use only.
This program is passive: it does not send commands to the monitor and does not
change any monitor setting.

Tested target environment:
- macOS
- Direct Ethernet link on interface en8
- IntelliVue announcement from UDP/24005 to ff02::1/24005
"""

from __future__ import annotations

import argparse
import re
import socket
import struct
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


DISCOVERY_PORT = 24005


@dataclass(frozen=True)
class Endpoint:
    application_protocol: int
    transport_protocol: int
    port: int
    options: int


def hex_dump(data: bytes, width: int = 16) -> str:
    lines: list[str] = []
    for offset in range(0, len(data), width):
        chunk = data[offset:offset + width]
        hex_part = " ".join(f"{byte:02x}" for byte in chunk)
        ascii_part = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
        lines.append(f"{offset:04x}  {hex_part:<{width * 3}}  {ascii_part}")
    return "\n".join(lines)


def printable_strings(data: bytes, minimum: int = 4) -> list[str]:
    pattern = rb"[\x20-\x7e]{" + str(minimum).encode() + rb",}"
    return [match.decode("ascii", errors="replace") for match in re.findall(pattern, data)]


def mac_text(raw: bytes) -> str:
    return ":".join(f"{byte:02x}" for byte in raw)


def find_tag(data: bytes, tag: int) -> list[tuple[int, bytes]]:
    """
    Locate simple Philips-style 16-bit tag + 16-bit length fields.
    Returns all syntactically valid occurrences.
    """
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
    """
    Parse tag F101, observed as:
        count: 16-bit
        total_length: 16-bit
        repeated entries:
            application protocol: 16-bit
            transport protocol:   16-bit
            port:                 16-bit
            options:              16-bit
    """
    endpoints: list[Endpoint] = []

    for _, value in find_tag(data, 0xF101):
        if len(value) < 4:
            continue

        count, declared_length = struct.unpack_from(">HH", value, 0)
        entries_blob = value[4:]

        if declared_length > len(entries_blob):
            continue

        entries_blob = entries_blob[:declared_length]
        available = len(entries_blob) // 8
        number_to_read = min(count, available)

        for position in range(number_to_read):
            fields = struct.unpack_from(">HHHH", entries_blob, position * 8)
            endpoints.append(Endpoint(*fields))

    return endpoints


def parse_ipv6_tag(data: bytes) -> list[str]:
    addresses: list[str] = []
    for _, value in find_tag(data, 0xF35E):
        if len(value) >= 16:
            try:
                addresses.append(socket.inet_ntop(socket.AF_INET6, value[:16]))
            except OSError:
                pass
    return addresses


def parse_mac_tags(data: bytes) -> list[str]:
    candidates: list[str] = []

    # F100 was observed to contain a 14-byte value beginning with the 6-byte MAC.
    for _, value in find_tag(data, 0xF100):
        if len(value) >= 6:
            candidates.append(mac_text(value[:6]))

    # F27C contains a nested structure in the observed packet; retain any
    # Philips OUI occurrence as a fallback.
    for match in re.finditer(rb"\x00\x09\xfb...", data, flags=re.DOTALL):
        candidates.append(mac_text(match.group(0)))

    return list(dict.fromkeys(candidates))


def extract_length_prefixed_ascii(data: bytes) -> list[str]:
    """
    Best-effort extraction of strings encoded as:
        16-bit byte length + string bytes
    Philips packets also contain padding, so this is intentionally conservative.
    """
    strings: list[str] = []

    for index in range(0, len(data) - 4):
        length = struct.unpack_from(">H", data, index)[0]
        if not 4 <= length <= 64:
            continue

        end = index + 2 + length
        if end > len(data):
            continue

        candidate = data[index + 2:end].rstrip(b"\x00")
        if candidate and all(32 <= byte <= 126 for byte in candidate):
            text = candidate.decode("ascii", errors="replace")
            if text not in strings:
                strings.append(text)

    return strings


def print_packet(data: bytes, sender: tuple, show_hex: bool) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    sender_ip, sender_port, flowinfo, scope_id = sender

    print("\n" + "=" * 76)
    print(f"[{timestamp}] Anuncio IntelliVue recibido")
    print(f"Origen:     [{sender_ip}%{scope_id}]:{sender_port}")
    print(f"Payload:    {len(data)} bytes")

    ipv6_addresses = parse_ipv6_tag(data)
    macs = parse_mac_tags(data)
    endpoints = parse_protocol_support(data)

    if ipv6_addresses:
        print("IPv6 anunciada:")
        for address in ipv6_addresses:
            print(f"  - {address}")

    if macs:
        print("MAC encontrada:")
        for address in macs:
            print(f"  - {address}")

    if endpoints:
        print("Endpoints anunciados (valores decimales y hexadecimales):")
        for endpoint in endpoints:
            print(
                "  - app={app} (0x{app:04x}), transporte={trans} "
                "(0x{trans:04x}), puerto={port}, opciones=0x{opts:04x}".format(
                    app=endpoint.application_protocol,
                    trans=endpoint.transport_protocol,
                    port=endpoint.port,
                    opts=endpoint.options,
                )
            )

    strings = extract_length_prefixed_ascii(data)
    if not strings:
        strings = printable_strings(data)

    if strings:
        print("Cadenas identificables:")
        for text in strings:
            print(f"  - {text}")

    if show_hex:
        print("\nHex dump del payload:")
        print(hex_dump(data))


def build_socket(interface: str) -> socket.socket:
    try:
        interface_index = socket.if_nametoindex(interface)
    except OSError as exc:
        raise RuntimeError(f"No existe la interfaz {interface!r}: {exc}") from exc

    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # On macOS, binding to all IPv6 addresses and the discovery port is enough
    # to receive the ff02::1 all-nodes datagram. The multicast-interface setting
    # makes the intended link explicit.
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, interface_index)
    sock.bind(("::", DISCOVERY_PORT))

    return sock


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Escucha pasivamente anuncios Philips IntelliVue por IPv6/UDP 24005."
    )
    parser.add_argument(
        "--interface",
        default="en8",
        help="Interfaz Ethernet de macOS (predeterminado: en8).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Número de anuncios que se capturarán (predeterminado: 1).",
    )
    parser.add_argument(
        "--hex",
        action="store_true",
        help="Muestra además el payload completo en hexadecimal.",
    )
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count debe ser al menos 1")

    try:
        sock = build_socket(args.interface)
    except (OSError, RuntimeError) as exc:
        print(f"Error al preparar el socket: {exc}", file=sys.stderr)
        return 1

    print(
        f"Escuchando anuncios IntelliVue en [{args.interface}] UDP/{DISCOVERY_PORT}.\n"
        "El monitor suele anunciarse aproximadamente cada 60–65 segundos.\n"
        "Ctrl+C para cancelar."
    )

    received = 0
    try:
        while received < args.count:
            data, sender = sock.recvfrom(65535)
            print_packet(data, sender, args.hex)
            received += 1
    except KeyboardInterrupt:
        print("\nCaptura cancelada.")
    except OSError as exc:
        print(f"\nError de red: {exc}", file=sys.stderr)
        return 1
    finally:
        sock.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
