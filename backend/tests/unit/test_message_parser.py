import json
import unittest

from backend.server.message_parser import FrameBuffer, MessageTooLarge, ParseError, parse_message


def monitor(client_id="agent-pc-001", **extra):
    data = {
        "client_id": client_id,
        "hostname": "PC-01",
        "cpu_usage": 25.5,
        "ram_usage": 50,
        "disk_usage": 50,
    }
    data.update(extra)
    return {"type": "monitor", "data": data}


class FrameBufferTests(unittest.TestCase):
    def test_message_split_across_chunks(self):
        buffer = FrameBuffer(1024)
        raw = (json.dumps(monitor()) + "\n").encode("utf-8")
        self.assertEqual(buffer.feed(raw[:12]), [])
        frames = buffer.feed(raw[12:])
        self.assertEqual(len(frames), 1)
        parsed = parse_message(frames[0])
        self.assertEqual(parsed.data["client_id"], "agent-pc-001")

    def test_many_messages_in_one_chunk(self):
        buffer = FrameBuffer(4096)
        first = json.dumps({"type": "heartbeat", "data": {"client_id": "a"}})
        second = json.dumps({"type": "heartbeat", "data": {"client_id": "b"}})
        frames = buffer.feed(f"{first}\n{second}\n".encode("utf-8"))
        self.assertEqual(
            [parse_message(frame).data["client_id"] for frame in frames],
            ["a", "b"],
        )

    def test_crlf_and_blank_line(self):
        buffer = FrameBuffer(1024)
        payload = json.dumps({"type": "heartbeat", "data": {"client_id": "pc"}})
        frames = buffer.feed(f"\r\n{payload}\r\n".encode("utf-8"))
        self.assertEqual(len(frames), 1)
        self.assertNotIsInstance(parse_message(frames[0]), ParseError)

    def test_oversize_line_does_not_keep_growing(self):
        buffer = FrameBuffer(32)
        with self.assertRaises(MessageTooLarge):
            buffer.feed(b"x" * 40)
        self.assertEqual(buffer.pending_size(), 0)


class ParseMessageTests(unittest.TestCase):
    def test_reject_bad_json_shape(self):
        self.assertEqual(parse_message(b"{").code, "invalid_json")
        self.assertEqual(parse_message(b"[]").code, "invalid_schema")
        self.assertEqual(
            parse_message(b'{"type":"ping","data":{}}').code,
            "unsupported_type",
        )

    def test_monitor_requires_hostname_and_percent_range(self):
        missing = {"type": "monitor", "data": {"client_id": "a"}}
        self.assertEqual(parse_message(json.dumps(missing).encode()).code, "missing_field")
        high = monitor(cpu_usage=140)
        self.assertEqual(parse_message(json.dumps(high).encode()).code, "invalid_field")

    def test_command_result_status(self):
        ok = {
            "type": "command_result",
            "data": {
                "client_id": "a",
                "command_id": "cmd-1",
                "status": "SUCCESS",
                "result_message": "pong",
                "exit_code": 0,
            },
        }
        parsed = parse_message(json.dumps(ok).encode())
        self.assertEqual(parsed.message_type, "command_result")
        self.assertNotIn("token", parsed.data)

    def test_token_is_checked_and_removed(self):
        payload = monitor()
        payload["data"]["token"] = "secret"
        denied = parse_message(json.dumps(payload).encode(), agent_token="other")
        self.assertEqual(denied.code, "unauthorized")
        allowed = parse_message(json.dumps(payload).encode(), agent_token="secret")
        self.assertEqual(allowed.data["hostname"], "PC-01")
        self.assertNotIn("token", allowed.data)


if __name__ == "__main__":
    unittest.main()
