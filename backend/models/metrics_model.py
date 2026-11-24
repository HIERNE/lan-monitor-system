"""
backend/models/metrics_model.py - Mẫu thông số tài nguyên tại một thời điểm.
Người phụ trách: TV1 (Hậu).

Tương ứng một dòng của bảng client_metrics (dữ liệu lịch sử, chỉ thêm mới).
Đơn vị: dung lượng = byte, phần trăm = 0..100, thời gian = ISO-8601 UTC.
Model chỉ giữ dữ liệu; không truy cập CSDL, không biết gì về socket/giao diện.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Dict


@dataclass
class MetricsModel:
    client_id: str
    collected_at: str
    cpu_usage: float
    ram_total: int
    ram_used: int
    ram_free: int
    ram_usage: float
    disk_total: int
    disk_used: int
    disk_free: int
    disk_usage: float
    uptime_seconds: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricsModel":
        """Lấy đúng các trường của Model, bỏ qua trường thừa."""
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})

    @classmethod
    def from_monitor(cls, monitor_data: Dict[str, Any]) -> "MetricsModel":
        """Tạo từ data của thông điệp 'monitor' (xem protocol/messages.md)."""
        return cls.from_dict(monitor_data)
