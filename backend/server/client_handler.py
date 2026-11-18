"""MOD-2.3.1: vòng nhận của một Agent. Lỗi của một message không dừng các Agent khác."""

from __future__ import annotations

import logging
import socket
import threading

from backend.server.client_manager import ClientManager
from backend.server.connection_manager import ClientSession, ConnectionManager
from backend.server.message_parser import FrameBuffer, MessageTooLarge, ParseError, parse_message

log = logging.getLogger(__name__)


class ClientHandler:
    def __init__(
        self,
        session: ClientSession,
        connections: ConnectionManager,
        clients: ClientManager,
        *,
        recv_bytes: int,
        max_message_bytes: int,
        agent_token: str,
        stop_event: threading.Event,
    ) -> None:
        self.session = session
        self.connections = connections
        self.clients = clients
        self.recv_bytes = recv_bytes
        self.agent_token = agent_token
        self.stop_event = stop_event
        self.buffer = FrameBuffer(max_message_bytes)

    def run(self) -> None:
        peer = f"{self.session.peer_ip}:{self.session.peer_port}"
        log.info("nhận kết nối %s session=%s", peer, self.session.session_id)
        try:
            self.session.sock.settimeout(1.0)
            while not self.stop_event.is_set() and not self.session.closed:
                try:
                    chunk = self.session.sock.recv(self.recv_bytes)
                except socket.timeout:
                    continue
                except OSError as exc:
                    log.info("socket đóng %s: %s", peer, exc)
                    break
                if not chunk:
                    log.info("agent đóng kết nối %s", peer)
                    break
                self._consume(chunk, peer)
        finally:
            self.session.closed = True
            was_active = self.connections.release(self.session)
            self.clients.handle_disconnect(self.session, was_active)
            _close_quietly(self.session.sock)
            log.info("kết thúc session %s", self.session.session_id)

    def _consume(self, chunk: bytes, peer: str) -> None:
        try:
            frames = self.buffer.feed(chunk)
        except MessageTooLarge as exc:
            log.warning("bỏ message quá lớn từ %s: %s", peer, exc)
            return
        for frame in frames:
            if self.session.closed:
                return
            parsed = parse_message(frame, agent_token=self.agent_token)
            if isinstance(parsed, ParseError):
                log.warning("từ chối message từ %s: %s (%s)", peer, parsed.detail, parsed.code)
                continue
            self.clients.handle_message(self.session, parsed)


def _close_quietly(sock: socket.socket) -> None:
    try:
        sock.close()
    except OSError:
        pass
