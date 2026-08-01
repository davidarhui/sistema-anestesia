#!/usr/bin/env python3
"""
Philips IntelliVue TCP connection probe (Phase 2: Association groundwork).

Research/development use only.

This script:
1. Listens for one IntelliVue discovery announcement on IPv6/UDP 24005.
2. Selects the announced TCP endpoint (normally port 24105).
3. Opens an IPv6 TCP connection through the requested interface.
4. Waits briefly to determine whether the monitor sends data first.
5. Does NOT yet transmit an Association Request or modify monitor settings.

It can also connect directly when --host is supplied.
"""

from __future__ import annotations

import argparse
import socket
import sys
from datetime import datetime
from typing import Optional

try:
    from philips_discovery_cli import (
        Endpoint,
        build_socket as build_discovery_socket,
        hex_dump,
        parse_ipv6_tag,
        parse_protocol_support,
    )
except ImportError as exc:
    raise SystemExit(
        "No se pudo importar philips_discovery_cli.py.\n"
        "Coloca association.py en la misma carpeta que philips_discovery_cli.py "
        "y vuelve a intentarlo."
    ) from exc


try:
    from transport import (
        ConnectionTarget,
        IPv6TCPTransport,
        create_target,
    )
except ImportError as exc:
    raise SystemExit(
        "No se pudo importar transport.py.\n"
        "Coloca transport.py en la misma carpeta que association.py "
        "y vuelve a intentarlo."
    ) from exc


DEFAULT_INTERFACE = "en8"
DEFAULT_DATA_EXPORT_PORT = 24105
DEFAULT_DISCOVERY_TIMEOUT = 75.0
DEFAULT_RECEIVE_TIMEOUT = 5.0

# En los anuncios observados:
#   transport_protocol=1 corresponde al endpoint TCP/24105.
DATA_EXPORT_TRANSPORT_PROTOCOL = 1


def select_data_export_endpoint(
    endpoints: list[Endpoint],
    preferred_port: int = DEFAULT_DATA_EXPORT_PORT,
) -> Optional[Endpoint]:
    """Choose the preferred announced TCP endpoint."""
    exact = [
        endpoint
        for endpoint in endpoints
        if endpoint.transport_protocol == DATA_EXPORT_TRANSPORT_PROTOCOL
        and endpoint.port == preferred_port
    ]
    if exact:
        # Prefer application protocol 1 when present.
        return sorted(
            exact,
            key=lambda endpoint: endpoint.application_protocol != 1,
        )[0]

    data_export_endpoints = [
        endpoint
        for endpoint in endpoints
        if endpoint.transport_protocol == DATA_EXPORT_TRANSPORT_PROTOCOL
    ]
    if data_export_endpoints:
        return sorted(
            tcp_endpoints,
            key=lambda endpoint: (
                endpoint.application_protocol != 1,
                endpoint.port,
            ),
        )[0]

    return None


def discover_target(
    interface: str,
    discovery_timeout: float,
    preferred_port: int,
) -> ConnectionTarget:
    """
    Wait for one discovery announcement and derive the TCP target from it.
    """
    try:
        interface_index = socket.if_nametoindex(interface)
    except OSError as exc:
        raise RuntimeError(f"No existe la interfaz {interface!r}: {exc}") from exc

    sock = build_discovery_socket(interface)
    sock.settimeout(discovery_timeout)

    print(
        f"Buscando un IntelliVue en [{interface}] UDP/24005...\n"
        f"Tiempo máximo de espera: {discovery_timeout:g} segundos."
    )

    try:
        data, sender = sock.recvfrom(65535)
    except socket.timeout as exc:
        raise TimeoutError(
            "No se recibió ningún anuncio IntelliVue dentro del tiempo previsto."
        ) from exc
    finally:
        sock.close()

    sender_ip, sender_port, _flowinfo, sender_scope_id = sender
    announced_ipv6 = parse_ipv6_tag(data)
    endpoints = parse_protocol_support(data)

    host = announced_ipv6[0] if announced_ipv6 else sender_ip
    endpoint = select_tcp_endpoint(endpoints, preferred_port)

    if endpoint is None:
        announced = ", ".join(
            f"transporte={item.transport_protocol}/puerto={item.port}"
            for item in endpoints
        ) or "ninguno"
        raise RuntimeError(
            "El anuncio no contiene un endpoint TCP utilizable. "
            f"Endpoints encontrados: {announced}"
        )

    # For a link-local destination, use the receiving interface's scope.
    scope_id = sender_scope_id or interface_index

    print("\nAnuncio recibido:")
    print(f"  Origen UDP: [{sender_ip}%{scope_id}]:{sender_port}")
    print(f"  IPv6 objetivo: {host}%{interface}")
    print(
        "  Endpoint elegido: "
        f"app={endpoint.application_protocol} "
        f"transporte={endpoint.transport_protocol} "
        f"puerto={endpoint.port}"
    )

    return create_target(
        host=host,
        port=endpoint.port,
        interface=interface,
        scope_id=scope_id,
        source="discovery",
    )


def direct_target(
        host: str,
        port: int,
        interface: str,
    ) -> ConnectionTarget:
        return create_target(
            host=host,
            port=port,
            interface=interface,
            source="manual",
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Descubre un Philips IntelliVue, abre TCP/24105 y comprueba "
            "si el monitor transmite datos antes de recibir una Association Request."
        )
    )
    parser.add_argument(
        "--interface",
        default=DEFAULT_INTERFACE,
        help=f"Interfaz Ethernet de macOS (predeterminado: {DEFAULT_INTERFACE}).",
    )
    parser.add_argument(
        "--host",
        metavar="IPV6",
        help=(
            "Omite el descubrimiento y usa directamente esta IPv6. "
            "Puede incluir %%en8."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_TCP_PORT,
        help=(
            f"Puerto TCP preferido o manual "
            f"(predeterminado: {DEFAULT_TCP_PORT})."
        ),
    )
    parser.add_argument(
        "--discovery-timeout",
        type=float,
        default=DEFAULT_DISCOVERY_TIMEOUT,
        help=(
            "Máximo de segundos para esperar el anuncio "
            f"(predeterminado: {DEFAULT_DISCOVERY_TIMEOUT:g})."
        ),
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=5.0,
        help="Máximo de segundos para establecer TCP (predeterminado: 5).",
    )
    parser.add_argument(
        "--receive-timeout",
        type=float,
        default=DEFAULT_RECEIVE_TIMEOUT,
        help=(
            "Segundos para esperar datos espontáneos después de conectar "
            f"(predeterminado: {DEFAULT_RECEIVE_TIMEOUT:g})."
        ),
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=65535,
        help="Máximo de bytes para la prueba de recepción (predeterminado: 65535).",
    )
    args = parser.parse_args()

    if not 1 <= args.port <= 65535:
        parser.error("--port debe estar entre 1 y 65535")
    if args.discovery_timeout <= 0:
        parser.error("--discovery-timeout debe ser mayor que cero")
    if args.connect_timeout <= 0:
        parser.error("--connect-timeout debe ser mayor que cero")
    if args.receive_timeout <= 0:
        parser.error("--receive-timeout debe ser mayor que cero")
    if args.max_bytes < 1:
        parser.error("--max-bytes debe ser al menos 1")

    try:
        if args.host:
            target = direct_target(args.host, args.port, args.interface)
            print("Usando destino proporcionado manualmente:")
            print(f"  IPv6: {target.host}%{target.interface}")
            print(f"  TCP:  {target.port}")
        else:
            target = discover_target(
                interface=args.interface,
                discovery_timeout=args.discovery_timeout,
                preferred_port=args.port,
            )

        print(
            f"\nConectando a "
            f"[{target.host}%{target.interface}]:{target.port}..."
        )

        started_at = datetime.now().astimezone()

        transport = IPv6TCPTransport(
            target,
            connect_timeout=args.connect_timeout,
        )

        try:
            transport.connect()

            peer = transport.socket.getpeername()
            local = transport.socket.getsockname()

            print("Conexión TCP establecida.")
            print(
                f"  Local:  [{local[0]}%{local[3]}]:{local[1]}"
            )
            print(
                f"  Remoto: [{peer[0]}%{peer[3]}]:{peer[1]}"
            )
            print(f"  Hora:   {started_at.isoformat(timespec='seconds')}")

            print(
                f"\nEsperando datos espontáneos durante "
                f"{args.receive_timeout:g} segundos..."
            )

            data = transport.receive(
                timeout=args.receive_timeout,
                max_bytes=args.max_bytes,
            )

            if data:
                print(f"\nSe recibieron {len(data)} bytes:")
                print(hex_dump(data))
            else:
                print(
                    "\nNo se recibieron datos espontáneos.\n"
                    "Resultado esperado si el monitor aguarda primero "
                    "una Association Request."
                )
        finally:
            transport.close()
            print("\nConexión cerrada limpiamente.")

    except KeyboardInterrupt:
        print("\nOperación cancelada.")
        return 130
    except TimeoutError as exc:
        print(f"\nTiempo de espera agotado: {exc}", file=sys.stderr)
        return 2
    except ConnectionRefusedError as exc:
        print(
            f"\nEl monitor rechazó la conexión TCP: {exc}",
            file=sys.stderr,
        )
        return 3
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
