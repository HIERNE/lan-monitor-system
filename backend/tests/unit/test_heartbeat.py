"""Unit tests cho HeartbeatWorker (TV2 - Trần Minh Khâm).
"""

import unittest
from unittest.mock import MagicMock

from backend.agent.heartbeat import HeartbeatWorker
from backend.models import message as msg_proto


class HeartbeatWorkerTests(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_client.is_connected = True
        self.mock_client.send_raw.return_value = True

    def test_send_heartbeat_payload(self):
        worker = HeartbeatWorker(
            client=self.mock_client,
            client_id="test-client-heartbeat",
            interval_sec=1.0,
            agent_token="secret-token-123",
        )
        success = worker.send_heartbeat()
        self.assertTrue(success)
        self.mock_client.send_raw.assert_called_once()

        sent_bytes = self.mock_client.send_raw.call_args[0][0]
        self.assertTrue(sent_bytes.endswith(b"\n"))

        decoded = msg_proto.decode_message(sent_bytes)
        self.assertEqual(decoded["type"], msg_proto.MSG_HEARTBEAT)
        self.assertEqual(decoded["data"]["client_id"], "test-client-heartbeat")
        self.assertEqual(decoded["data"]["token"], "secret-token-123")


if __name__ == "__main__":
    unittest.main()
