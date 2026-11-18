"""Ánh xạ client_id → socket/session cho các Agent đang kết nối.

TV4 tạo lệnh nhưng không giữ socket. Lớp này là chỗ duy nhất biết
một client_id đang đi qua kết nối nào (MOD-2.2.4, MOD-2.6.3).
"""

from __future__ import annotations

import socket
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ClientSession:
    session_id: str
    sock: socket.socket
    peer_ip: str
    peer_port: int
    connected_at: datetime
    client_id: str | None = None
    last_seen: datetime | None = None
    status: str = "Connected"
    announced: bool = False
    closed: bool = False
    send_lock: threading.Lock = field(default_factory=threading.Lock)


class ConnectionManager:
    def __init__(self, max_clients: int) -> None:
        if max_clients <= 0:
            raise ValueError("max_clients phải lớn hơn 0")
        self.max_clients = max_clients
        self._lock = threading.Lock()
        self._sessions: dict[str, ClientSession] = {}
        self._by_client: dict[str, ClientSession] = {}

    def try_accept(
        self,
        sock: socket.socket,
        peer_ip: str,
        peer_port: int,
        connected_at: datetime,
    ) -> ClientSession | None:
        with self._lock:
            if len(self._sessions) >= self.max_clients:
                return None
            session = ClientSession(
                session_id=uuid.uuid4().hex[:12],
                sock=sock,
                peer_ip=peer_ip,
                peer_port=peer_port,
                connected_at=connected_at,
            )
            self._sessions[session.session_id] = session
            return session

    def attach_client(self, session: ClientSession, client_id: str) -> ClientSession | None:
        """Gắn client_id vào session. Kết nối cũ cùng client_id bị thay thế."""
        replaced: ClientSession | None = None
        with self._lock:
            previous = self._by_client.get(client_id)
            if previous is not None and previous is not session:
                previous.client_id = None
                previous.closed = True
                replaced = previous
            session.client_id = client_id
            self._by_client[client_id] = session
        if replaced is not None:
            _close_socket(replaced.sock)
        return replaced

    def get_by_client(self, client_id: str) -> ClientSession | None:
        with self._lock:
            session = self._by_client.get(client_id)
            if session is None or session.closed:
                return None
            return session

    def release(self, session: ClientSession) -> bool:
        """Gỡ session. True nếu đây vẫn là socket đang đại diện cho client_id."""
        with self._lock:
            self._sessions.pop(session.session_id, None)
            if not session.client_id:
                return False
            current = self._by_client.get(session.client_id)
            if current is session:
                self._by_client.pop(session.client_id, None)
                return True
            return False

    def list_sessions(self) -> list[ClientSession]:
        with self._lock:
            return list(self._sessions.values())

    def connected_count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def send_bytes(self, client_id: str, payload: bytes) -> None:
        session = self.get_by_client(client_id)
        if session is None:
            raise ClientUnavailable(client_id)
        with session.send_lock:
            if session.closed or session.status != "Online":
                raise ClientUnavailable(client_id)
            session.sock.sendall(payload)


class ClientUnavailable(Exception):
    def __init__(self, client_id: str) -> None:
        super().__init__(client_id)
        self.client_id = client_id


def _close_socket(sock: socket.socket) -> None:
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass
