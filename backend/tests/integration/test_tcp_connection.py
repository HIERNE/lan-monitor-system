import json
import socket
import threading
import time
import unittest

from backend.server.client_manager import ServerEventHandler
from backend.server.main import build_runtime
from backend.server.tcp_server import ServerConfig


class RecordingHandler(ServerEventHandler):
    def __init__(self) -> None:
        self.events = []
        self._condition = threading.Condition()

    def _add(self, name, event):
        with self._condition:
            self.events.append((name, event))
            self._condition.notify_all()

    def on_client_connected(self, event):
        self._add("connected", event)

    def on_client_disconnected(self, event):
        self._add("disconnected", event)

    def on_client_timeout(self, event):
        self._add("timeout", event)

    def on_monitor(self, event):
        self._add("monitor", event)

    def on_heartbeat(self, event):
        self._add("heartbeat", event)

    def on_command_result(self, event):
        self._add("command_result", event)

    def wait_for(self, name, client_id=None, count=1, timeout=2):
        deadline = time.time() + timeout
        with self._condition:
            while time.time() < deadline:
                found = 0
                matched = None
                for event_name, event in self.events:
                    if event_name != name:
                        continue
                    owner = event.get("client_id") or event.get("data", {}).get("client_id")
                    if client_id is None or owner == client_id:
                        found += 1
                        matched = event
                if found >= count:
                    return matched
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)
        raise AssertionError(f"không thấy sự kiện {name} cho {client_id}")


class TcpServerTests(unittest.TestCase):
    def start_server(self, **overrides):
        values = dict(
            host="127.0.0.1",
            port=0,
            backlog=16,
            max_clients=5,
            max_message_bytes=4096,
            recv_bytes=8,
            heartbeat_timeout_sec=30,
            agent_token="",
        )
        values.update(overrides)
        self.handler = RecordingHandler()
        self.runtime = build_runtime(ServerConfig(**values), self.handler)
        self.runtime.server.start_background()
        self.addCleanup(self.runtime.server.stop)
        deadline = time.time() + 2
        while self.runtime.server.bound_port == 0 and time.time() < deadline:
            time.sleep(0.01)
        return self.runtime.server.bound_port

    def connect(self, port):
        sock = socket.create_connection(("127.0.0.1", port), timeout=2)
        self.addCleanup(self._close, sock)
        return sock

    @staticmethod
    def _close(sock):
        try:
            sock.close()
        except OSError:
            pass

    def test_partial_recv_and_multiple_json(self):
        port = self.start_server()
        agent = self.connect(port)
        line = json.dumps({"type": "heartbeat", "data": {"client_id": "pc-01"}}) + "\n"
        raw = (line + line).encode("utf-8")
        agent.sendall(raw[:5])
        time.sleep(0.05)
        agent.sendall(raw[5:])
        self.handler.wait_for("heartbeat", "pc-01", count=2)

    def test_bad_json_does_not_drop_the_agent(self):
        port = self.start_server()
        agent = self.connect(port)
        agent.sendall(b'{"type":\n')
        good = json.dumps({"type": "heartbeat", "data": {"client_id": "pc-01"}}) + "\n"
        agent.sendall(good.encode("utf-8"))
        self.handler.wait_for("heartbeat", "pc-01")

    def test_command_reaches_only_the_online_client(self):
        port = self.start_server()
        first = self.connect(port)
        second = self.connect(port)
        first.sendall(self._monitor("pc-01"))
        second.sendall(self._monitor("pc-02"))
        self.handler.wait_for("monitor", "pc-01")
        self.handler.wait_for("monitor", "pc-02")

        sent = self.runtime.commands.send_command(
            client_id="pc-01",
            command_id="cmd-1",
            command_type="PING_TEST",
            parameter={},
        )
        self.assertEqual(sent["status"], "SENT")
        first.settimeout(2)
        received = self._read_message(first)
        self.assertEqual(received["type"], "command")
        self.assertEqual(received["data"]["client_id"], "pc-01")
        self.assertEqual(received["data"]["command_type"], "PING_TEST")

        second.settimeout(0.3)
        with self.assertRaises(socket.timeout):
            second.recv(256)

        missing = self.runtime.commands.send_command(
            client_id="pc-99",
            command_id="cmd-2",
            command_type="PING_TEST",
        )
        self.assertEqual(missing["status"], "FAILED")
        blocked = self.runtime.commands.send_command(
            client_id="pc-01",
            command_id="cmd-3",
            command_type="SHUTDOWN",
        )
        self.assertEqual(blocked["status"], "REJECTED")

    def test_abrupt_disconnect_releases_the_client(self):
        port = self.start_server()
        agent = self.connect(port)
        agent.sendall(self._monitor("pc-01"))
        self.handler.wait_for("monitor", "pc-01")
        agent.close()
        self.handler.wait_for("disconnected", "pc-01")
        result = self.runtime.commands.send_command(
            client_id="pc-01",
            command_id="cmd-4",
            command_type="PING_TEST",
        )
        self.assertEqual(result["status"], "FAILED")

    def test_silent_client_times_out_but_socket_can_recover(self):
        port = self.start_server(heartbeat_timeout_sec=0.4)
        agent = self.connect(port)
        agent.sendall(json.dumps({"type": "heartbeat", "data": {"client_id": "pc-01"}}).encode() + b"\n")
        self.handler.wait_for("heartbeat", "pc-01")
        self.handler.wait_for("timeout", "pc-01", timeout=2)
        failed = self.runtime.commands.send_command(
            client_id="pc-01",
            command_id="cmd-5",
            command_type="PING_TEST",
        )
        self.assertEqual(failed["status"], "FAILED")
        agent.sendall(json.dumps({"type": "heartbeat", "data": {"client_id": "pc-01"}}).encode() + b"\n")
        self.handler.wait_for("heartbeat", "pc-01", count=2)
        recovered = self.runtime.commands.send_command(
            client_id="pc-01",
            command_id="cmd-6",
            command_type="PING_TEST",
        )
        self.assertEqual(recovered["status"], "SENT")

    def test_second_connection_is_refused_at_the_limit(self):
        port = self.start_server(max_clients=1)
        first = self.connect(port)
        first.sendall(self._monitor("pc-01"))
        self.handler.wait_for("monitor", "pc-01")
        second = self.connect(port)
        second.settimeout(1)
        self.assertEqual(second.recv(32), b"")
        self.assertEqual(self.runtime.connections.connected_count(), 1)

    @staticmethod
    def _monitor(client_id):
        payload = {
            "type": "monitor",
            "data": {"client_id": client_id, "hostname": client_id, "cpu_usage": 10},
        }
        return (json.dumps(payload) + "\n").encode("utf-8")

    @staticmethod
    def _read_message(sock):
        data = b""
        while b"\n" not in data:
            piece = sock.recv(256)
            if not piece:
                break
            data += piece
        return json.loads(data.decode("utf-8").strip())


if __name__ == "__main__":
    unittest.main()
