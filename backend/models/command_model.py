"""
backend/models/command_model.py - Một lệnh điều khiển và kết quả của nó.
Người phụ trách: TV1 (Hậu).

Tương ứng một dòng của bảng commands. Vòng đời trạng thái:
pending (mới tạo) -> sent (đã gửi cho Agent) -> success | failed | timeout.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, Optional

from backend.models import message

STATUS_PENDING = "pending"
STATUS_SENT = "sent"
STATUS_SUCCESS = message.STATUS_SUCCESS
STATUS_FAILED = message.STATUS_FAILED
STATUS_TIMEOUT = "timeout"
COMMAND_STATUSES = (STATUS_PENDING, STATUS_SENT, STATUS_SUCCESS, STATUS_FAILED, STATUS_TIMEOUT)


@dataclass
class CommandModel:
    command_id: str
    client_id: str
    command_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = STATUS_PENDING
    result_message: Optional[str] = None
    exit_code: Optional[int] = None
    created_at: str = field(default_factory=message.now_iso)
    sent_at: Optional[str] = None
    finished_at: Optional[str] = None

    @classmethod
    def new(cls, client_id: str, command_type: str,
            params: Optional[Dict[str, Any]] = None) -> "CommandModel":
        """Tạo lệnh mới (Server). Từ chối loại lệnh không có trong giao thức."""
        if command_type not in message.COMMAND_TYPES:
            raise message.ProtocolError(f"command_type không hợp lệ: {command_type!r}")
        return cls(command_id=message.new_command_id(), client_id=client_id,
                   command_type=command_type, params=dict(params or {}))

    def to_message(self) -> dict:
        """Thông điệp 'command' gửi xuống Agent; đánh dấu đã gửi."""
        self.status = STATUS_SENT
        self.sent_at = message.now_iso()
        return message.build_command(self.command_id, self.client_id, self.command_type,
                                     self.params, self.sent_at)

    def apply_result(self, result_data: Dict[str, Any]) -> None:
        """Cập nhật từ data của thông điệp 'command_result'."""
        if result_data.get("command_id") != self.command_id:
            raise message.ProtocolError("command_id của kết quả không khớp với lệnh")
        self.status = result_data["status"]
        self.result_message = result_data.get("result_message")
        self.exit_code = result_data.get("exit_code")
        self.finished_at = result_data.get("finished_at") or message.now_iso()

    def mark_timeout(self) -> None:
        self.status = STATUS_TIMEOUT
        self.finished_at = message.now_iso()

    @property
    def is_finished(self) -> bool:
        return self.status in (STATUS_SUCCESS, STATUS_FAILED, STATUS_TIMEOUT)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommandModel":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})
