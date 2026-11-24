"""Unit tests cho CommandHandler (TV2 - Trần Minh Khâm).
Kiểm tra xử lý các loại lệnh PING_TEST, GET_CONFIG, SHUTDOWN, RESTART, SCREEN và lệnh không hỗ trợ.
"""

import json
import unittest
from unittest.mock import MagicMock

from backend.agent.command_handler import CommandHandler
from backend.models import message as msg_proto


class DummyCollector:
    def collect_monitor_data(self):
        return {
            "client_id": "test-client-123",
            "hostname": "TEST-PC",
            "ip_address": "192.168.1.50",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "os_name": "Windows 11",
            "cpu_name": "Intel Core i7",
            "cpu_cores": 8,
            "ram_total": 16000000000,
            "disk_total": 512000000000,
        }


class CommandHandlerTests(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.client_id = "test-client-123"
        self.collector = DummyCollector()
        self.handler = CommandHandler(
            client=self.mock_client,
            client_id=self.client_id,
            collector=self.collector,
        )

    def test_handle_ping_test(self):
        cmd = {
            "type": "command",
            "data": {
                "command_id": "cmd-001",
                "command_type": "PING_TEST",
                "parameter": {"echo": "hello"},
            },
        }
        res = self.handler.handle_command(cmd)
        self.assertIsNotNone(res)
        self.assertEqual(res["type"], msg_proto.MSG_COMMAND_RESULT)
        self.assertEqual(res["data"]["command_id"], "cmd-001")
        self.assertEqual(res["data"]["status"], msg_proto.STATUS_SUCCESS)
        self.assertEqual(res["data"]["result_message"], "hello")
        self.assertEqual(res["data"]["exit_code"], 0)
        self.mock_client.send_raw.assert_called_once()

    def test_handle_get_config(self):
        cmd = {
            "type": "command",
            "data": {
                "command_id": "cmd-002",
                "command_type": "GET_CONFIG",
                "parameter": {},
            },
        }
        res = self.handler.handle_command(cmd)
        self.assertIsNotNone(res)
        self.assertEqual(res["data"]["status"], msg_proto.STATUS_SUCCESS)
        self.assertEqual(res["data"]["exit_code"], 0)
        config_data = json.loads(res["data"]["result_message"])
        self.assertEqual(config_data["hostname"], "TEST-PC")
        self.assertEqual(config_data["ip_address"], "192.168.1.50")

    def test_handle_simulation_commands(self):
        for cmd_type in ["SHUTDOWN", "RESTART", "SCREEN"]:
            cmd = {
                "type": "command",
                "data": {
                    "command_id": f"cmd-{cmd_type}",
                    "command_type": cmd_type,
                    "parameter": {},
                },
            }
            res = self.handler.handle_command(cmd)
            self.assertIsNotNone(res)
            self.assertEqual(res["data"]["status"], msg_proto.STATUS_SUCCESS)
            self.assertEqual(res["data"]["exit_code"], 0)
            self.assertIn("Mô phỏng", res["data"]["result_message"])

    def test_handle_unsupported_command(self):
        cmd = {
            "type": "command",
            "data": {
                "command_id": "cmd-bad",
                "command_type": "UNKNOWN_ACTION",
                "parameter": {},
            },
        }
        res = self.handler.handle_command(cmd)
        self.assertIsNotNone(res)
        self.assertEqual(res["data"]["status"], msg_proto.STATUS_FAILED)
        self.assertEqual(res["data"]["exit_code"], 1)

    def test_ignore_invalid_command(self):
        cmd = {"type": "command", "data": {}}
        res = self.handler.handle_command(cmd)
        self.assertIsNone(res)
        self.mock_client.send_raw.assert_not_called()


if __name__ == "__main__":
    unittest.main()
