"""Điểm chạy Server Core.

    python -m backend.server.main

TV4 gắn lưu MySQL bằng runtime.clients.set_event_handler(...)
và gửi lệnh bằng runtime.commands.send_command(...).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from backend.server.client_manager import ClientManager, ServerEventHandler
from backend.server.command_manager import CommandManager
from backend.server.connection_manager import ConnectionManager
from backend.server.tcp_server import ServerConfig, TcpServer

log = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ServerRuntime:
    config: ServerConfig
    connections: ConnectionManager
    clients: ClientManager
    commands: CommandManager
    server: TcpServer


def build_runtime(
    config: ServerConfig | None = None,
    handler: ServerEventHandler | None = None,
) -> ServerRuntime:
    selected = config or ServerConfig.from_env()
    connections = ConnectionManager(selected.max_clients)
    clients = ClientManager(
        connections,
        heartbeat_timeout_sec=selected.heartbeat_timeout_sec,
        handler=handler,
    )
    commands = CommandManager(connections)
    server = TcpServer(selected, connections, clients, commands)
    return ServerRuntime(selected, connections, clients, commands, server)


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    load_env_file(PROJECT_ROOT / ".env")
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    runtime = build_runtime()
    log.info(
        "Server Core lắng nghe %s:%s (tối đa %s Agent)",
        runtime.config.host,
        runtime.config.port,
        runtime.config.max_clients,
    )
    try:
        runtime.server.serve_forever()
    except KeyboardInterrupt:
        log.info("nhận tín hiệu dừng")
    finally:
        runtime.server.stop()


if __name__ == "__main__":
    main()
