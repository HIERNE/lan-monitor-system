"""Unit tests cho TcpClient (TV2 - Trần Minh Khâm).
Kiểm tra kết nối TCP socket, gửi nhận, đệm newline và giải mã gói tin.
"""

import socket
import threading
import time
import unittest

from backend.agent.tcp_client import TcpClient
from backend.models import message as msg_proto


class _EchoServer:
    """Server giả lập phục vụ kiểm thử TcpClient."""

    def __init__(self) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.received = []
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self.listener.settimeout(3.0)
        try:
            conn, _ = self.listener.accept()
        except OSError:
            return
        conn.settimeout(3.0)
        buffer = b""
        with conn:
            while True:
                try:
                    chunk = conn.recv(4096)
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        self.received.append(line)
                        # Gửi lại một lệnh command kiểm thử
                        resp = msg_proto.encode_message(
                            msg_proto.build_command(
                                command_id="test-cmd-echo",
                                client_id="client-test",
                                command_type="PING_TEST",
                            )
                        )
                        conn.sendall(resp)

    def close(self) -> None:
        try:
            self.listener.close()
        except OSError:
            pass
        self._thread.join(timeout=3.0)


class TcpClientTests(unittest.TestCase):
    def setUp(self):
        self.server = _EchoServer()
        self.client = TcpClient(host="127.0.0.1", port=self.server.port, timeout=2.0)

    def tearDown(self):
        self.client.stop()
        self.server.close()

    def test_connect_and_send(self):
        connected = self.client.connect()
        self.assertTrue(connected)
        self.assertTrue(self.client.is_connected)

        msg = msg_proto.build_heartbeat("client-test-01")
        sent = self.client.send_message(msg)
        self.assertTrue(sent)

        time.sleep(0.2)
        self.assertGreaterEqual(len(self.server.received), 1)

    def test_receive_command_callback(self):
        received_commands = []

        def on_cmd(cmd):
            received_commands.append(cmd)

        self.client.set_on_command_callback(on_cmd)
        self.client.connect()
        self.client.start_background_workers()

        # Gửi 1 message để kích hoạt server echo phản hồi lại command
        msg = msg_proto.build_heartbeat("client-test-01")
        self.client.send_message(msg)

        # Chờ tối đa 2s để nhận phản hồi từ background receiver thread
        for _ in range(20):
            if received_commands:
                break
            time.sleep(0.1)

        self.assertGreaterEqual(len(received_commands), 1)
        self.assertEqual(received_commands[0]["type"], "command")
        self.assertEqual(received_commands[0]["data"]["command_type"], "PING_TEST")


if __name__ == "__main__":
    unittest.main()
