import socket
import unittest
from unittest.mock import MagicMock, patch

from transport import (
    ConnectionTarget,
    IPv6TCPTransport,
    create_target,
    normalize_ipv6_host,
)


class NormalizeIPv6HostTests(unittest.TestCase):
    def test_plain_ipv6(self):
        self.assertEqual(
            normalize_ipv6_host("fe80::1"),
            "fe80::1",
        )

    def test_ipv6_with_zone(self):
        self.assertEqual(
            normalize_ipv6_host("fe80::1%en8"),
            "fe80::1",
        )

    def test_bracketed_ipv6_with_zone(self):
        self.assertEqual(
            normalize_ipv6_host("[fe80::1%en8]"),
            "fe80::1",
        )

    def test_invalid_ipv6(self):
        with self.assertRaises(ValueError):
            normalize_ipv6_host("esto-no-es-ipv6")


class CreateTargetTests(unittest.TestCase):
    @patch("transport.socket.if_nametoindex", return_value=26)
    def test_create_target(self, mocked_index):
        target = create_target(
            "fe80::1%en8",
            24105,
            "en8",
        )

        self.assertEqual(target.host, "fe80::1")
        self.assertEqual(target.port, 24105)
        self.assertEqual(target.interface, "en8")
        self.assertEqual(target.interface_index, 26)
        self.assertEqual(target.source, "manual")

        mocked_index.assert_called_once_with("en8")

    def test_invalid_port(self):
        with self.assertRaises(ValueError):
            create_target("fe80::1", 70000, "en8")


class IPv6TCPTransportTests(unittest.TestCase):
    def setUp(self):
        self.target = ConnectionTarget(
            host="fe80::1",
            port=24105,
            interface="en8",
            interface_index=26,
            source="test",
        )

    @patch("transport.socket.socket")
    def test_connect_uses_ipv6_scope_id(self, mocked_socket_class):
        mocked_socket = MagicMock()
        mocked_socket_class.return_value = mocked_socket

        transport = IPv6TCPTransport(
            self.target,
            connect_timeout=3.0,
        )
        transport.connect()

        mocked_socket_class.assert_called_once_with(
            socket.AF_INET6,
            socket.SOCK_STREAM,
        )
        mocked_socket.setsockopt.assert_called_once_with(
            socket.IPPROTO_IPV6,
            socket.IPV6_V6ONLY,
            1,
        )
        mocked_socket.settimeout.assert_called_once_with(3.0)
        mocked_socket.connect.assert_called_once_with(
            ("fe80::1", 24105, 0, 26)
        )

    @patch("transport.socket.socket")
    def test_send_all(self, mocked_socket_class):
        mocked_socket = MagicMock()
        mocked_socket_class.return_value = mocked_socket

        transport = IPv6TCPTransport(self.target)
        transport.connect()
        transport.send_all(b"\x01\x02\x03")

        mocked_socket.sendall.assert_called_once_with(
            b"\x01\x02\x03"
        )

    @patch("transport.socket.socket")
    def test_receive_timeout_returns_empty_bytes(
        self,
        mocked_socket_class,
    ):
        mocked_socket = MagicMock()
        mocked_socket.recv.side_effect = socket.timeout
        mocked_socket_class.return_value = mocked_socket

        transport = IPv6TCPTransport(self.target)
        transport.connect()

        result = transport.receive(timeout=2.0)

        self.assertEqual(result, b"")

    @patch("transport.socket.socket")
    def test_close_is_idempotent(self, mocked_socket_class):
        mocked_socket = MagicMock()
        mocked_socket_class.return_value = mocked_socket

        transport = IPv6TCPTransport(self.target)
        transport.connect()

        transport.close()
        transport.close()

        mocked_socket.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()