import socket
import unittest
from unittest.mock import MagicMock, patch

from transport import ConnectionTarget
from udp_transport import IPv6UDPTransport


class IPv6UDPTransportTests(unittest.TestCase):
    def setUp(self):
        self.target = ConnectionTarget(
            host="fe80::1",
            port=24105,
            interface="en8",
            interface_index=26,
            source="test",
        )

    @patch("udp_transport.socket.socket")
    def test_open_creates_scoped_ipv6_udp_socket(
        self,
        mocked_socket_class,
    ):
        mocked_socket = MagicMock()
        mocked_socket_class.return_value = mocked_socket

        transport = IPv6UDPTransport(
            self.target,
            local_port=0,
        )
        transport.open()

        mocked_socket_class.assert_called_once_with(
            socket.AF_INET6,
            socket.SOCK_DGRAM,
        )
        mocked_socket.setsockopt.assert_called_once_with(
            socket.IPPROTO_IPV6,
            socket.IPV6_V6ONLY,
            1,
        )
        mocked_socket.bind.assert_called_once_with(
            ("::", 0, 0, 26)
        )

    @patch("udp_transport.socket.socket")
    def test_send_uses_target_scope(
        self,
        mocked_socket_class,
    ):
        mocked_socket = MagicMock()
        mocked_socket.sendto.return_value = 3
        mocked_socket_class.return_value = mocked_socket

        transport = IPv6UDPTransport(self.target)
        transport.open()

        sent = transport.send(b"\x01\x02\x03")

        self.assertEqual(sent, 3)
        mocked_socket.sendto.assert_called_once_with(
            b"\x01\x02\x03",
            ("fe80::1", 24105, 0, 26),
        )

    @patch("udp_transport.socket.socket")
    def test_receive_returns_datagram_and_sender(
        self,
        mocked_socket_class,
    ):
        mocked_socket = MagicMock()
        mocked_socket.recvfrom.return_value = (
            b"\x10\x20",
            ("fe80::1", 24105, 0, 26),
        )
        mocked_socket_class.return_value = mocked_socket

        transport = IPv6UDPTransport(self.target)
        transport.open()

        result = transport.receive(timeout=2.0)

        self.assertEqual(
            result,
            (
                b"\x10\x20",
                ("fe80::1", 24105, 0, 26),
            ),
        )

    @patch("udp_transport.socket.socket")
    def test_receive_timeout_returns_none(
        self,
        mocked_socket_class,
    ):
        mocked_socket = MagicMock()
        mocked_socket.recvfrom.side_effect = socket.timeout
        mocked_socket_class.return_value = mocked_socket

        transport = IPv6UDPTransport(self.target)
        transport.open()

        self.assertIsNone(
            transport.receive(timeout=2.0)
        )

    @patch("udp_transport.socket.socket")
    def test_close_is_idempotent(
        self,
        mocked_socket_class,
    ):
        mocked_socket = MagicMock()
        mocked_socket_class.return_value = mocked_socket

        transport = IPv6UDPTransport(self.target)
        transport.open()

        transport.close()
        transport.close()

        mocked_socket.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()