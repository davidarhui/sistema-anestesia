#!/usr/bin/env python3
"""Privileged macOS DHCP helper for USS Anestesia.

Runs only the already-tested DHCPService as root.  The GUI starts this helper
through macOS' native authorization dialog.  A normal user-owned stop file is
used for graceful shutdown, so disconnecting does not require a second
administrator prompt.

The helper also watches the Registro process PID and exits automatically if the
GUI crashes or is closed unexpectedly.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def parent_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-dir", required=True)
    parser.add_argument("--interface", default="en8")
    parser.add_argument("--server-ip", default="192.168.50.1")
    parser.add_argument("--client-ip", default="192.168.50.2")
    parser.add_argument("--client-mac", default=None)
    parser.add_argument("--subnet", default="255.255.255.0")
    parser.add_argument("--lease", type=int, default=3600)
    parser.add_argument("--stop-file", required=True)
    parser.add_argument("--ready-file", required=True)
    parser.add_argument("--error-file", required=True)
    parser.add_argument("--parent-pid", type=int, required=True)
    args = parser.parse_args()

    sdk_dir = Path(args.sdk_dir).expanduser().resolve()
    sys.path.insert(0, str(sdk_dir))

    stop_file = Path(args.stop_file)
    ready_file = Path(args.ready_file)
    error_file = Path(args.error_file)

    for path in (ready_file, error_file):
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    try:
        from philips_intellivue.dhcp_server import DHCPServerConfig
        from philips_intellivue.dhcp_service import DHCPService

        config = DHCPServerConfig(
            interface=args.interface,
            server_ip=args.server_ip,
            client_ip=args.client_ip,
            client_mac=args.client_mac,
            subnet_mask=args.subnet,
            lease_seconds=args.lease,
        )

        service = DHCPService(config)
        service.start()
        ready_file.write_text("ready\n", encoding="utf-8")

        while True:
            if stop_file.exists():
                break
            if not parent_alive(args.parent_pid):
                break
            time.sleep(0.25)

        service.stop()
        return 0

    except Exception as exc:
        try:
            error_file.write_text(
                f"{type(exc).__name__}: {exc}\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
