"""
Kiểm thử tích hợp (TV1): gói tin của Agent đi qua TCP socket THẬT (loopback)
và phía nhận tách theo "\\n", giải mã đúng.

Dùng một "Server tối giản" ngay trong file test, nên không phụ thuộc phần
Server của Hiển. Chạy: python -m unittest discover -v
"""
import socket
import threading
import time
import unittest

from backend.agent.system_info import SystemInfoCollector
from backend.models import message as m
from backend.tests.sample_data import sample_monitor_data


class _MiniServer:
    """Nhận một kết nối: đệm byte, tách theo \\n, giải mã từng dòng."""

    def __init__(self) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))  # cổng 0: hệ điều hành tự chọn cổng trống
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.received = []   # thông điệp hợp lệ
        self.errors = []     # thông điệp bị từ chối
        self.leftover = b""  # byte còn dư (thông điệp chưa đủ)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self.listener.settimeout(5)
        try:
            conn, _ = self.listener.accept()
        except OSError:
            return
        conn.settimeout(5)
        buffer = b""
        with conn:
            while True:
                try:
                    chunk = conn.recv(4096)
                except (socket.timeout, OSError):
                    break
                if not chunk:  # Agent đã đóng kết nối
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        self.received.append(m.decode_message(line))
                    except m.ProtocolError as exc:
                        self.errors.append(str(exc))
        self.leftover = buffer

    def finish(self) -> None:
        self._thread.join(timeout=10)
        self.listener.close()


class AgentPacketsOverTcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = _MiniServer()
        self.client = socket.create_connection(("127.0.0.1", self.server.port), timeout=5)
        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def tearDown(self) -> None:
        self.client.close()
        self.server.finish()

    def _close_and_wait(self) -> None:
        self.client.close()
        self.server.finish()

    def test_monitor_and_heartbeat_arrive(self):
        collector = SystemInfoCollector()
        self.client.sendall(collector.monitor_packet())
        self.client.sendall(m.encode_message(m.build_heartbeat(collector.client_id)))
        self._close_and_wait()

        self.assertEqual([x["type"] for x in self.server.received],
                         [m.MSG_MONITOR, m.MSG_HEARTBEAT])
        self.assertEqual(self.server.received[0]["data"]["client_id"], collector.client_id)
        self.assertEqual(self.server.errors, [])

    def test_message_split_across_several_sends(self):
        packet = m.encode_message(m.build_monitor(sample_monitor_data()))
        third = len(packet) // 3
        for part in (packet[:third], packet[third:2 * third], packet[2 * third:]):
            self.client.sendall(part)
            time.sleep(0.05)  # để mỗi phần có cơ hội đến Server như một lần recv riêng
        self._close_and_wait()

        self.assertEqual(len(self.server.received), 1)
        self.assertEqual(self.server.received[0]["data"]["hostname"], "PC-LAB-01")
        self.assertEqual(self.server.errors, [])

    def test_several_messages_in_one_send(self):
        batch = b"".join(m.encode_message(m.build_heartbeat(f"CL-{i}")) for i in range(5))
        self.client.sendall(batch)
        self._close_and_wait()

        self.assertEqual([x["data"]["client_id"] for x in self.server.received],
                         [f"CL-{i}" for i in range(5)])

    def test_bad_message_does_not_stop_the_stream(self):
        self.client.sendall(b"{khong phai json}\n")
        self.client.sendall(b'{"type":"monitor"}\n')  # thiếu data
        self.client.sendall(m.encode_message(m.build_heartbeat("CL-OK")))
        self._close_and_wait()

        self.assertEqual(len(self.server.errors), 2)
        self.assertEqual(len(self.server.received), 1)
        self.assertEqual(self.server.received[0]["data"]["client_id"], "CL-OK")

    def test_incomplete_message_is_not_delivered(self):
        packet = m.encode_message(m.build_heartbeat("CL-HALF"))
        self.client.sendall(packet[:-5])  # thiếu phần cuối và dấu \n
        self._close_and_wait()

        self.assertEqual(self.server.received, [])
        self.assertEqual(self.server.leftover, packet[:-5])

    def test_vietnamese_text_over_tcp(self):
        data = sample_monitor_data()
        data["hostname"] = "MÁY-PHÒNG-THỰC-HÀNH"
        self.client.sendall(m.encode_message(m.build_monitor(data)))
        self._close_and_wait()

        self.assertEqual(self.server.received[0]["data"]["hostname"], "MÁY-PHÒNG-THỰC-HÀNH")


if __name__ == "__main__":
    unittest.main()
