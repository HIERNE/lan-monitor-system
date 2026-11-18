"""MOD-2.6.4 và MOD-2.6.5: tạo command JSON và gửi tới đúng Agent đang Online.

TV4 gọi send_command() sau khi đã lưu lệnh. Bản giữa kỳ chỉ cho phép
PING_TEST (FR-18). Không đưa lệnh shell tùy ý vào payload.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from backend.server.connection_manager import ClientUnavailable, ConnectionManager


ALLOWED_COMMAND_TYPES = frozenset({"PING_TEST"})


class CommandManager:
    def __init__(self, connections: ConnectionManager) -> None:
        self.connections = connections

    def send_command(
        self,
        *,
        client_id: str,
        command_id: str,
        command_type: str,
        parameter: dict | None = None,
    ) -> dict:
        if not isinstance(client_id, str) or not client_id.strip():
            return _result(client_id, command_id, command_type, "REJECTED", "client_id không hợp lệ")
        if not isinstance(command_id, str) or not command_id.strip() or len(command_id) > 64:
            return _result(client_id, command_id, command_type, "REJECTED", "command_id không hợp lệ")
        if command_type not in ALLOWED_COMMAND_TYPES:
            return _result(client_id, command_id, command_type, "REJECTED", "command_type không nằm trong allowlist")
        if parameter is None:
            parameter = {}
        if not isinstance(parameter, dict):
            return _result(client_id, command_id, command_type, "REJECTED", "parameter phải là object")

        sent_at = _iso(datetime.now(timezone.utc))
        payload = {
            "type": "command",
            "data": {
                "command_id": command_id,
                "command_type": command_type,
                "parameter": parameter,
                "client_id": client_id,
                "timestamp": sent_at,
            },
        }
        raw = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        try:
            self.connections.send_bytes(client_id, raw)
        except ClientUnavailable:
            return _result(client_id, command_id, command_type, "FAILED", "client offline hoặc chưa kết nối")
        except OSError as exc:
            return _result(client_id, command_id, command_type, "FAILED", f"lỗi socket: {exc}")
        return _result(client_id, command_id, command_type, "SENT", "đã gửi", sent_at)


def _result(
    client_id: object,
    command_id: object,
    command_type: object,
    status: str,
    detail: str,
    sent_at: str | None = None,
) -> dict:
    return {
        "client_id": client_id,
        "command_id": command_id,
        "command_type": command_type,
        "status": status,
        "detail": detail,
        "sent_at": sent_at,
    }


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
