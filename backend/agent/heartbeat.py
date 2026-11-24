"""MOD-1.5.2: Gửi Heartbeat định kỳ tới Server để duy trì trạng thái Online.

Phụ trách: TV2 - Trần Minh Khâm
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from backend.agent.tcp_client import TcpClient
from backend.models import message as msg_proto

log = logging.getLogger(__name__)


class HeartbeatWorker:
    """Tác vụ nền định kỳ gửi gói tin heartbeat tới Server."""

    def __init__(
        self,
        client: TcpClient,
        client_id: str,
        interval_sec: float = 5.0,
        agent_token: str = "",
    ) -> None:
        self.client = client
        self.client_id = client_id
        self.interval_sec = max(1.0, float(interval_sec))
        self.agent_token = agent_token

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Khởi động luồng gửi heartbeat định kỳ."""
        self._stop_event.clear()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._run_loop,
                name="Agent-HeartbeatWorker",
                daemon=True,
            )
            self._thread.start()
            log.info("HeartbeatWorker đã khởi động (chu kỳ: %.1f giây).", self.interval_sec)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            # Chờ đúng chu kỳ trước khi gửi hoặc kết thúc ngay khi stop_event được set
            if self._stop_event.wait(timeout=self.interval_sec):
                break

            if not self.client.is_connected:
                continue

            self.send_heartbeat()

    def send_heartbeat(self) -> bool:
        """Tạo và gửi gói tin heartbeat qua TCP Client."""
        msg = msg_proto.build_heartbeat(self.client_id)
        if self.agent_token:
            msg["data"]["token"] = self.agent_token

        try:
            packet = msg_proto.encode_message(msg)
            success = self.client.send_raw(packet)
            if success:
                log.debug("Đã gửi heartbeat cho client_id=%s", self.client_id)
            return success
        except msg_proto.ProtocolError as exc:
            log.error("Lỗi khi tạo gói tin heartbeat: %s", exc)
            return False

    def stop(self) -> None:
        """Dừng tác vụ heartbeat."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        log.info("HeartbeatWorker đã dừng.")
