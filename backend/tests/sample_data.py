"""Dữ liệu mẫu dùng chung cho các bộ kiểm thử."""

from typing import Dict


def sample_monitor_data() -> Dict[str, object]:
    """Tạo mẫu dữ liệu monitor hợp lệ theo protocol/messages.md."""
    return {
        "client_id": "AA:BB:CC:DD:EE:FF",
        "hostname": "PC-LAB-01",
        "ip_address": "192.168.1.21",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "network_name": "Ethernet",
        "os_name": "Windows 11 (10.0.22631)",
        "cpu_name": "Intel(R) Core(TM) i5",
        "cpu_cores": 6,
        "cpu_threads": 12,
        "cpu_usage": 12.5,
        "ram_total": 16000000000,
        "ram_used": 8000000000,
        "ram_free": 8000000000,
        "ram_usage": 50.0,
        "disk_total": 500000000000,
        "disk_used": 200000000000,
        "disk_free": 300000000000,
        "disk_usage": 40.0,
        "boot_time": "2026-11-18T01:00:00.000+00:00",
        "uptime_seconds": 3600,
        "collected_at": "2026-11-18T02:00:00.000+00:00",
    }
