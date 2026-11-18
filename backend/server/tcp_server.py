"""MOD-2.1: tạo socket, bind, listen và accept nhiều Agent bằng thread."""

from __future__ import annotations

import logging
import os
import socket
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from backend.server.client_handler import ClientHandler
from backend.server.client_manager import ClientManager
from backend.server.command_manager import CommandManager
from backend.server.connection_manager import ConnectionManager

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 9000
    backlog: int = 128
    max_clients: int = 50
    max_message_bytes: int = 65_536
    recv_bytes: int = 4096
    heartbeat_timeout_sec: float = 30.0
    agent_token: str = ""

    @staticmethod
    def from_env(env: dict[str, str] | None = None) -> "ServerConfig":
        source = os.environ if env is None else env
        return ServerConfig(
            host=source.get("TCP_HOST", "0.0.0.0").strip() or "0.0.0.0",
            port=_port(source.get("TCP_PORT", "9000")),
            backlog=_positive_int(source.get("TCP_BACKLOG", "128"), "TCP_BACKLOG"),
            max_clients=_positive_int(source.get("MAX_CLIENTS", "50"), "MAX_CLIENTS"),
            max_message_bytes=_positive_int(
                source.get("MAX_MESSAGE_BYTES", "65536"),
                "MAX_MESSAGE_BYTES",
            ),
            recv_bytes=_positive_int(source.get("RECV_BYTES", "4096"), "RECV_BYTES"),
            heartbeat_timeout_sec=_positive_float(
                source.get("HEARTBEAT_TIMEOUT_SEC", "30"),
                "HEARTBEAT_TIMEOUT_SEC",
            ),
            agent_token=source.get("AGENT_TOKEN", "").strip(),
        )


class TcpServer:
    def __init__(
        self,
        config: ServerConfig,
        connections: ConnectionManager,
        clients: ClientManager,
        commands: CommandManager,
    ) -> None:
        self.config = config
        self.connections = connections
        self.clients = clients
        self.commands = commands
        self.bound_port = config.port
        self._listener: socket.socket | None = None
        self._stop = threading.Event()
        self._timeout_thread: threading.Thread | None = None
        self._accept_thread: threading.Thread | None = None

    def serve_forever(self) -> None:
        self._open_listener()
        self._start_timeout_worker()
        try:
            self._accept_loop()
        finally:
            self.stop()

    def start_background(self) -> None:
        self._open_listener()
        self._start_timeout_worker()
        self._accept_thread = threading.Thread(
            target=self._accept_loop,
            name="tcp-accept",
            daemon=True,
        )
        self._accept_thread.start()

    def stop(self) -> None:
        self._stop.set()
        listener = self._listener
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
        for session in self.connections.list_sessions():
            try:
                session.sock.close()
            except OSError:
                pass
        if self._timeout_thread is not None:
            self._timeout_thread.join(timeout=2)
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=2)

    def _open_listener(self) -> None:
        if self._listener is not None:
            return
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((self.config.host, self.config.port))
            listener.listen(self.config.backlog)
        except OSError:
            listener.close()
            raise
        listener.settimeout(1.0)
        self._listener = listener
        self.bound_port = listener.getsockname()[1]
        log.info("đang lắng nghe %s:%s", self.config.host, self.bound_port)

    def _accept_loop(self) -> None:
        assert self._listener is not None
        while not self._stop.is_set():
            try:
                conn, addr = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                if self._stop.is_set():
                    break
                log.exception("accept lỗi")
                continue
            peer_ip = addr[0]
            peer_port = int(addr[1]) if len(addr) > 1 else 0
            session = self.connections.try_accept(
                conn,
                peer_ip,
                peer_port,
                datetime.now(timezone.utc),
            )
            if session is None:
                log.warning("từ chối %s:%s vì đã đạt MAX_CLIENTS", peer_ip, peer_port)
                conn.close()
                continue
            worker = threading.Thread(
                target=self._run_client,
                args=(session,),
                name=f"agent-{session.session_id}",
                daemon=True,
            )
            worker.start()

    def _run_client(self, session) -> None:
        handler = ClientHandler(
            session,
            self.connections,
            self.clients,
            recv_bytes=self.config.recv_bytes,
            max_message_bytes=self.config.max_message_bytes,
            agent_token=self.config.agent_token,
            stop_event=self._stop,
        )
        try:
            handler.run()
        except Exception:
            log.exception("worker %s dừng vì lỗi", session.session_id)

    def _start_timeout_worker(self) -> None:
        if self._timeout_thread is not None:
            return
        self._timeout_thread = threading.Thread(
            target=self._timeout_loop,
            name="client-timeout",
            daemon=True,
        )
        self._timeout_thread.start()

    def _timeout_loop(self) -> None:
        interval = min(5.0, max(0.2, self.config.heartbeat_timeout_sec / 2))
        while not self._stop.wait(interval):
            try:
                self.clients.scan_timeouts()
            except Exception:
                log.exception("quét timeout lỗi")


def _port(raw: str) -> int:
    try:
        port = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("TCP_PORT phải là số nguyên") from exc
    if not 1 <= port <= 65535 and port != 0:
        raise ValueError("TCP_PORT phải trong khoảng 1–65535")
    return port


def _positive_int(raw: str, name: str) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} phải là số nguyên") from exc
    if value <= 0:
        raise ValueError(f"{name} phải lớn hơn 0")
    return value


def _positive_float(raw: str, name: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} phải là số") from exc
    if value <= 0:
        raise ValueError(f"{name} phải lớn hơn 0")
    return value
