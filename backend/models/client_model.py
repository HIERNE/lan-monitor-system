"""
backend/models/client_model.py - Thông tin hiện tại của một máy Client.
Người phụ trách: TV1 (Hậu).

Tương ứng một dòng của bảng clients (insert/update theo client_id).
status và last_seen do Server cập nhật (Heartbeat/timeout), Agent không gửi.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Dict, Optional

STATUS_ONLINE = "online"
STATUS_OFFLINE = "offline"


@dataclass
class ClientModel:
    client_id: str
    hostname: str
    ip_address: str
    mac_address: str
    os_name: str
    network_name: Optional[str] = None
    cpu_name: Optional[str] = None
    cpu_cores: Optional[int] = None
    cpu_threads: Optional[int] = None
    ram_total: Optional[int] = None
    disk_total: Optional[int] = None
    boot_time: Optional[str] = None
    status: str = STATUS_OFFLINE
    last_seen: Optional[str] = None

    @property
    def is_online(self) -> bool:
        return self.status == STATUS_ONLINE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientModel":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})

    @classmethod
    def from_monitor(cls, monitor_data: Dict[str, Any]) -> "ClientModel":
        """Tạo từ data của thông điệp 'monitor'; trạng thái mặc định là offline
        cho tới khi Server xác nhận (đặt status/last_seen)."""
        return cls.from_dict(monitor_data)

    def mark_seen(self, when_iso: str) -> None:
        """Server gọi khi nhận monitor/heartbeat."""
        self.status = STATUS_ONLINE
        self.last_seen = when_iso

    def mark_offline(self) -> None:
        """Server gọi khi quá thời gian timeout."""
        self.status = STATUS_OFFLINE
