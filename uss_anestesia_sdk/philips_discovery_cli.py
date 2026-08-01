#!/usr/bin/env python3
"""
Philips IntelliVue discovery listener (IPv6 / UDP 24005).

Research/development use only.
Passive capture: it does not send commands to the monitor or change settings.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import struct
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


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
    """Locate simple Philips-style 16-bit tag + 16-bit length fields."""
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
    Parse observed tag F101:
        count: 16-bit
        total_length: 16-bit
        repeated 8-byte entries:
            application protocol
            transport protocol
            port
            options
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
        number_to_read = min(count, len(entries_blob) // 8)

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

    for _, value in find_tag(data, 0xF100):
        if len(value) >= 6:
            candidates.append(mac_text(value[:6]))

    for match in re.finditer(rb"\x00\x09\xfb...", data, flags=re.DOTALL):
        candidates.append(mac_text(match.group(0)))

    return list(dict.fromkeys(candidates))


def extract_length_prefixed_ascii(data: bytes) -> list[str]:
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


def capture_metadata(data: bytes, sender: tuple, interface: str) -> dict:
    sender_ip, sender_port, flowinfo, scope_id = sender
    strings = extract_length_prefixed_ascii(data) or printable_strings(data)

    return {
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "interface": interface,
        "sender": {
            "ipv6": sender_ip,
            "port": sender_port,
            "flowinfo": flowinfo,
            "scope_id": scope_id,
        },
        "payload_length": len(data),
        "ipv6_addresses": parse_ipv6_tag(data),
        "mac_addresses": parse_mac_tags(data),
        "endpoints": [asdict(endpoint) for endpoint in parse_protocol_support(data)],
        "strings": strings,
        "sha256_note": "Use shasum -a 256 on the .bin file if a checksum is needed.",
    }


def save_capture(
    data: bytes,
    sender: tuple,
    interface: str,
    output: Path,
    overwrite: bool,
) -> tuple[Path, Path, Path]:
    """
    Save the exact payload plus a JSON metadata sidecar and a text hex dump.

    For --count > 1, appends _001, _002, etc. in main().
    """
    output = output.expanduser()

    if output.suffix.lower() != ".bin":
        output = output.with_suffix(".bin")

    output.parent.mkdir(parents=True, exist_ok=True)

    json_path = output.with_suffix(".json")
    hex_path = output.with_suffix(".hex.txt")

    existing = [path for path in (output, json_path, hex_path) if path.exists()]
    if existing and not overwrite:
        names = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"Ya existe(n): {names}. Usa --overwrite o elige otra ruta con --save."
        )

    # Atomic-ish writes: create temporary files, then replace final paths.
    bin_tmp = output.with_suffix(output.suffix + ".tmp")
    json_tmp = json_path.with_suffix(json_path.suffix + ".tmp")
    hex_tmp = hex_path.with_suffix(hex_path.suffix + ".tmp")

    try:
        bin_tmp.write_bytes(data)
        json_tmp.write_text(
            json.dumps(
                capture_metadata(data, sender, interface),
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        hex_tmp.write_text(hex_dump(data) + "\n", encoding="utf-8")

        bin_tmp.replace(output)
        json_tmp.replace(json_path)
        hex_tmp.replace(hex_path)
    finally:
        for temp in (bin_tmp, json_tmp, hex_tmp):
            if temp.exists():
                temp.unlink()

    return output, json_path, hex_path


def print_packet(data: bytes, sender: tuple, show_hex: bool) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    sender_ip, sender_port, _flowinfo, scope_id = sender

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
        print("Endpoints anunciados:")
        for endpoint in endpoints:
            print(
                "  - app={app} transporte={trans} puerto={port} "
                "opciones=0x{opts:04x}".format(
                    app=endpoint.application_protocol,
                    trans=endpoint.transport_protocol,
                    port=endpoint.port,
                    opts=endpoint.options,
                )
            )

    strings = extract_length_prefixed_ascii(data) or printable_strings(data)
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

    # En macOS ayuda cuando hay otros sockets escuchando el mismo puerto.
    if hasattr(socket, "SO_REUSEPORT"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    # Limita este socket a IPv6.
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

    # Escuchar UDP/24005 en todas las direcciones IPv6 locales.
    sock.bind(("::", DISCOVERY_PORT))

    # Unirse explícitamente a ff02::1 en la interfaz indicada.
    multicast_address = socket.inet_pton(socket.AF_INET6, "ff02::1")
    membership_request = (
        multicast_address
        + interface_index.to_bytes(4, byteorder=sys.byteorder)
    )

    sock.setsockopt(
        socket.IPPROTO_IPV6,
        socket.IPV6_JOIN_GROUP,
        membership_request,
    )

    return sock


def numbered_output(base: Path, position: int, count: int) -> Path:
    if count == 1:
        return base

    suffix = base.suffix or ".bin"
    stem = base.stem if base.suffix else base.name
    return base.with_name(f"{stem}_{position:03d}{suffix}")


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
        help="Muestra el payload completo en hexadecimal.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        metavar="RUTA.bin",
        help=(
            "Guarda el payload exacto. También crea RUTA.json y RUTA.hex.txt. "
            "Ejemplo: --save capturas/mx450_discovery.bin"
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permite reemplazar archivos de captura existentes.",
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
        "El anuncio puede tardar unos 60–65 segundos.\n"
        "Ctrl+C para cancelar."
    )

    received = 0
    try:
        while received < args.count:
            data, sender = sock.recvfrom(65535)
            received += 1
            print_packet(data, sender, args.hex)

            if args.save is not None:
                output = numbered_output(args.save, received, args.count)
                try:
                    bin_path, json_path, hex_path = save_capture(
                        data=data,
                        sender=sender,
                        interface=args.interface,
                        output=output,
                        overwrite=args.overwrite,
                    )
                except (OSError, FileExistsError) as exc:
                    print(f"\nNo se pudo guardar la captura: {exc}", file=sys.stderr)
                    return 1

                print("\nCaptura guardada:")
                print(f"  BIN exacto: {bin_path}")
                print(f"  Metadatos:  {json_path}")
                print(f"  Hex dump:   {hex_path}")

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
