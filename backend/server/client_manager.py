"""Điều phối message đã validate sang TV4 và theo dõi Online/Offline trong bộ nhớ.

MySQL, repository và API thuộc TV4. Server Core chỉ gọi các hàm dưới đây
sau khi message hợp lệ. TV4 gán handler của mình bằng set_event_handler().

last_seen dùng đồng hồ Server (UTC), không dùng đồng hồ Agent.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone

from backend.server.connection_manager import ClientSession, ConnectionManager
from backend.server.message_parser import ParsedMessage

log = logging.getLogger(__name__)


class ServerEventHandler:
    """Hợp đồng bàn giao cho TV4. Mọi phương thức đều được gọi từ thread của Agent."""

    def on_client_connected(self, event: dict) -> None:
        return None

    def on_client_disconnected(self, event: dict) -> None:
        return None

    def on_client_timeout(self, event: dict) -> None:
        return None

    def on_monitor(self, event: dict) -> None:
        return None

    def on_heartbeat(self, event: dict) -> None:
        return None

    def on_command_result(self, event: dict) -> None:
        return None


class LoggingEventHandler(ServerEventHandler):
    def on_client_connected(self, event: dict) -> None:
        log.info("client connected %s", event.get("client_id"))

    def on_client_disconnected(self, event: dict) -> None:
        log.info("client disconnected %s", event.get("client_id"))

    def on_client_timeout(self, event: dict) -> None:
        log.info("client timeout %s", event.get("client_id"))

    def on_monitor(self, event: dict) -> None:
        log.info("monitor %s", event.get("data", {}).get("client_id"))

    def on_heartbeat(self, event: dict) -> None:
        log.info("heartbeat %s", event.get("data", {}).get("client_id"))

    def on_command_result(self, event: dict) -> None:
        data = event.get("data", {})
        log.info("command_result %s %s", data.get("command_id"), data.get("status"))


class ClientManager:
    def __init__(
        self,
        connections: ConnectionManager,
        heartbeat_timeout_sec: float,
        handler: ServerEventHandler | None = None,
    ) -> None:
        if heartbeat_timeout_sec <= 0:
            raise ValueError("heartbeat_timeout_sec phải lớn hơn 0")
        self.connections = connections
        self.heartbeat_timeout_sec = heartbeat_timeout_sec
        self._handler: ServerEventHandler = handler or LoggingEventHandler()
        self._handler_lock = threading.Lock()

    def set_event_handler(self, handler: ServerEventHandler) -> None:
        with self._handler_lock:
            self._handler = handler

    def handle_message(self, session: ClientSession, message: ParsedMessage) -> None:
        if session.closed:
            return
        now = _utcnow()
        client_id = message.data["client_id"]
        self.connections.attach_client(session, client_id)
        if session.closed:
            return

        with session.send_lock:
            session.last_seen = now
            session.status = "Online"
        event = {
            "type": message.message_type,
            "data": message.data,
            "received_at": _iso(now),
            "peer_ip": session.peer_ip,
            "peer_port": session.peer_port,
        }
        if not session.announced:
            session.announced = True
            self._emit(
                "on_client_connected",
                {
                    "client_id": client_id,
                    "peer_ip": session.peer_ip,
                    "peer_port": session.peer_port,
                    "connected_at": _iso(session.connected_at),
                    "received_at": _iso(now),
                },
            )
        self._emit(f"on_{message.message_type}", event)

    def handle_disconnect(self, session: ClientSession, was_active: bool) -> None:
        if not was_active or not session.client_id:
            return
        session.status = "Offline"
        now = _utcnow()
        self._emit(
            "on_client_disconnected",
            {
                "client_id": session.client_id,
                "peer_ip": session.peer_ip,
                "peer_port": session.peer_port,
                "last_seen": _iso(session.last_seen) if session.last_seen else None,
                "received_at": _iso(now),
                "reason": "disconnect",
            },
        )

    def scan_timeouts(self, now: datetime | None = None) -> None:
        """MOD-2.4.3: quá HEARTBEAT_TIMEOUT_SEC thì báo Offline, không đóng socket ngay."""
        current = now or _utcnow()
        limit = timedelta(seconds=self.heartbeat_timeout_sec)
        expired = []
        for session in self.connections.list_sessions():
            with session.send_lock:
                if session.closed or session.status != "Online" or session.last_seen is None:
                    continue
                if current - session.last_seen <= limit:
                    continue
                session.status = "Offline"
                expired.append(
                    {
                        "client_id": session.client_id,
                        "peer_ip": session.peer_ip,
                        "peer_port": session.peer_port,
                        "last_seen": _iso(session.last_seen),
                        "received_at": _iso(current),
                        "reason": "timeout",
                    }
                )
        for event in expired:
            self._emit("on_client_timeout", event)

    def _emit(self, method_name: str, event: dict) -> None:
        with self._handler_lock:
            handler = self._handler
        method = getattr(handler, method_name)
        try:
            method(event)
        except Exception:
            log.exception("event handler %s lỗi; server vẫn tiếp tục", method_name)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
