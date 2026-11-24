from __future__ import annotations

import os
import platform
import re
import socket
import subprocess
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict, Optional, Tuple

import psutil

from backend.models import message
from backend.models.client_model import ClientModel
from backend.models.metrics_model import MetricsModel

_MAC_RE = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


def _percent(part: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round(max(0.0, min(100.0, part * 100.0 / total)), 1)


# ==========================================================================
# 1.3.1  CPU
# ==========================================================================
@lru_cache(maxsize=1)
def get_cpu_name() -> Optional[str]:
    """MOD-1.3.1.1: tên CPU; None nếu hệ điều hành không cung cấp."""
    system = platform.system()
    try:
        if system == "Windows":
            import winreg  # chỉ có trên Windows
            key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return " ".join(str(name).split()) or None
        if system == "Linux":
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip() or None
        if system == "Darwin":
            out = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                 capture_output=True, text=True, timeout=3)
            if out.stdout.strip():
                return out.stdout.strip()
    except Exception:  # noqa: BLE001 - thu thập là "best effort", không được làm sập Agent
        pass
    return platform.processor() or None


def get_cpu_cores() -> Optional[int]:
    """MOD-1.3.1.2: số lõi vật lý (không có thì lấy số luồng logic)."""
    return psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True)


def get_cpu_threads() -> Optional[int]:
    """Số luồng logic."""
    return psutil.cpu_count(logical=True)


def get_cpu_usage(interval: Optional[float] = None) -> float:
    """MOD-1.3.1.3: % CPU đang dùng.

    interval=None: tính từ lần gọi trước (không chặn) - phù hợp gọi mỗi 5 giây.
    Lần gọi đầu tiên sau khi khởi động tiến trình trả về 0.0, nên
    SystemInfoCollector đã "mồi" sẵn trong __init__.
    """
    return round(max(0.0, min(100.0, psutil.cpu_percent(interval=interval))), 1)


# ==========================================================================
# 1.3.2  RAM  (một lần chụp -> các giá trị nhất quán với nhau)
# ==========================================================================
def get_ram_info() -> Dict[str, float]:
    """total/used/free (byte) và usage (%). free = bộ nhớ khả dụng (available),
    used = total - free để cùng một định nghĩa trên mọi hệ điều hành."""
    vm = psutil.virtual_memory()
    total = int(vm.total)
    free = int(vm.available)
    used = max(0, total - free)
    return {"total": total, "used": used, "free": free, "usage": _percent(used, total)}


def get_ram_total() -> int:
    """MOD-1.3.2.1"""
    return int(get_ram_info()["total"])


def get_ram_used() -> int:
    """MOD-1.3.2.2"""
    return int(get_ram_info()["used"])


def get_ram_free() -> int:
    """MOD-1.3.2.3"""
    return int(get_ram_info()["free"])


# ==========================================================================
# 1.3.3  Ổ đĩa  (ổ hệ thống: SystemDrive trên Windows, "/" trên Linux/macOS)
# ==========================================================================
def get_disk_path() -> str:
    if platform.system() == "Windows":
        return os.environ.get("SystemDrive", "C:") + "\\"
    return "/"


def get_disk_info(path: Optional[str] = None) -> Dict[str, float]:
    du = psutil.disk_usage(path or get_disk_path())
    total = int(du.total)
    free = int(du.free)
    used = max(0, total - free)
    return {"total": total, "used": used, "free": free, "usage": _percent(used, total)}


def get_disk_total(path: Optional[str] = None) -> int:
    """MOD-1.3.3.1"""
    return int(get_disk_info(path)["total"])


def get_disk_used(path: Optional[str] = None) -> int:
    """MOD-1.3.3.2"""
    return int(get_disk_info(path)["used"])


def get_disk_free(path: Optional[str] = None) -> int:
    """MOD-1.3.3.3"""
    return int(get_disk_info(path)["free"])


# ==========================================================================
# 1.3.4  Mạng
# ==========================================================================
def get_hostname() -> str:
    return socket.gethostname()


def get_ip(target_host: str = "8.8.8.8", target_port: int = 80) -> str:
    """MOD-1.3.4.1: IP của card mạng đang dùng để đi tới target_host.

    Dùng UDP connect (KHÔNG gửi gói nào) để hệ điều hành chọn card mạng.
    Trong LAN không có Internet, hãy truyền IP của Server vào target_host.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(1.0)
        sock.connect((target_host, target_port))
        return sock.getsockname()[0]
    except OSError:
        pass
    finally:
        sock.close()
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def _normalize_mac(raw: str) -> Optional[str]:
    mac = raw.strip().replace("-", ":").upper()
    return mac if _MAC_RE.match(mac) else None


def _mac_from_node() -> str:
    node = uuid.getnode()
    return ":".join(f"{(node >> shift) & 0xFF:02X}" for shift in range(40, -1, -8))


def _find_interface(ip: str) -> Tuple[Optional[str], Optional[str]]:
    """(tên card mạng, MAC) của card đang giữ địa chỉ ip."""
    try:
        for name, addrs in psutil.net_if_addrs().items():
            if any(a.family == socket.AF_INET and a.address == ip for a in addrs):
                mac = None
                for a in addrs:
                    if a.family == psutil.AF_LINK:
                        mac = _normalize_mac(a.address)
                return name, mac
    except Exception:  # noqa: BLE001
        pass
    return None, None


def get_mac(ip: Optional[str] = None) -> str:
    """MOD-1.3.4.2: MAC dạng AA:BB:CC:DD:EE:FF của card đang dùng."""
    _, mac = _find_interface(ip or get_ip())
    return mac or _mac_from_node()


def get_network_name(ip: Optional[str] = None) -> Optional[str]:
    """MOD-1.3.4.3: tên/ID card mạng (ví dụ 'Wi-Fi', 'Ethernet', 'eth0')."""
    name, _ = _find_interface(ip or get_ip())
    return name


# ==========================================================================
# 1.3.5  Hệ điều hành
# ==========================================================================
def get_os_name() -> str:
    """MOD-1.3.5.1: ví dụ 'Windows 11 (10.0.22631)'."""
    system = platform.system()
    if system == "Windows":
        version = platform.version()  # ví dụ 10.0.22631
        try:
            build = int(version.split(".")[-1])
        except ValueError:
            build = 0
        release = "11" if build >= 22000 else platform.release()
        return f"Windows {release} ({version})"
    return f"{system} {platform.release()}".strip()


def get_boot_time_iso() -> str:
    return datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc).isoformat(timespec="milliseconds")


def get_uptime_seconds() -> int:
    """MOD-1.3.5.2: số giây từ lúc máy khởi động."""
    return max(0, int(time.time() - psutil.boot_time()))


# ==========================================================================
# Lớp tổng hợp cho Controller (Khâm) gọi
# ==========================================================================
class SystemInfoCollector:
    """Gom mọi thông số thành 1 dict đúng schema 'monitor' trong protocol/messages.md."""

    def __init__(self, server_host: Optional[str] = None, server_port: int = 80):
        # server_host: IP/hostname của Server -> chọn đúng card mạng trong LAN.
        self.server_host = server_host or "8.8.8.8"
        self.server_port = server_port
        self._client_id: Optional[str] = None
        psutil.cpu_percent(interval=None)  # "mồi" để lần đo CPU đầu tiên có nghĩa

    def _ip(self) -> str:
        return get_ip(self.server_host, self.server_port)

    @property
    def client_id(self) -> str:
        """FR-01: định danh máy, tính một lần rồi giữ nguyên suốt vòng đời tiến trình.
        Bản thử nghiệm lấy theo MAC (có thể nâng cấp sang UUID lưu bền vững)."""
        if self._client_id is None:
            self._client_id = get_mac(self._ip())
        return self._client_id

    def collect_device_info(self) -> Dict[str, object]:
        """Thông tin cấu hình thiết bị (dùng cho lệnh GET_CONFIG - MOD-1.6.7)."""
        ip = self._ip()
        name, mac = _find_interface(ip)
        return {
            "client_id": self.client_id,
            "hostname": get_hostname(),
            "ip_address": ip,
            "mac_address": mac or _mac_from_node(),
            "network_name": name,
            "os_name": get_os_name(),
            "cpu_name": get_cpu_name(),
            "cpu_cores": get_cpu_cores(),
            "cpu_threads": get_cpu_threads(),
            "ram_total": get_ram_total(),
            "disk_total": get_disk_total(),
        }

    def collect_monitor_data(self) -> Dict[str, object]:
        """Dữ liệu cho thông điệp 'monitor' (FR-01, FR-02, FR-03)."""
        ip = self._ip()
        net_name, mac = _find_interface(ip)
        ram = get_ram_info()
        disk = get_disk_info()
        return {
            "client_id": self.client_id,
            "hostname": get_hostname(),
            "ip_address": ip,
            "mac_address": mac or _mac_from_node(),
            "network_name": net_name,
            "os_name": get_os_name(),
            "cpu_name": get_cpu_name(),
            "cpu_cores": get_cpu_cores(),
            "cpu_threads": get_cpu_threads(),
            "cpu_usage": get_cpu_usage(),
            "ram_total": ram["total"],
            "ram_used": ram["used"],
            "ram_free": ram["free"],
            "ram_usage": ram["usage"],
            "disk_total": disk["total"],
            "disk_used": disk["used"],
            "disk_free": disk["free"],
            "disk_usage": disk["usage"],
            "boot_time": get_boot_time_iso(),
            "uptime_seconds": get_uptime_seconds(),
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        }

    # ---- dạng đối tượng Model (dùng cho Admin/Server khi cần) ----
    def collect_client(self) -> ClientModel:
        return ClientModel.from_monitor(self.collect_monitor_data())

    def collect_metrics(self) -> MetricsModel:
        return MetricsModel.from_monitor(self.collect_monitor_data())

    # ---- gói tin sẵn sàng gửi (MOD-1.4.1 -> 1.4.3) ----
    def build_monitor_message(self) -> dict:
        return message.build_monitor(self.collect_monitor_data())

    def monitor_packet(self) -> bytes:
        """bytes đã kèm "\\n": tcp_client.py chỉ việc sock.sendall(collector.monitor_packet())."""
        return message.encode_message(self.build_monitor_message())


# ==========================================================================
# Chạy thử độc lập (không cần Server):
#   python -m backend.agent.system_info --count 3 --interval 2 --server-host 192.168.1.10
# ==========================================================================
def _demo() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Demo thu thập dữ liệu và đóng gói JSON")
    parser.add_argument("--count", type=int, default=2, help="số lần thu thập")
    parser.add_argument("--interval", type=float, default=2.0, help="giây giữa các lần")
    parser.add_argument("--server-host", default=None, help="IP Server (để chọn đúng card mạng)")
    args = parser.parse_args()

    collector = SystemInfoCollector(server_host=args.server_host)
    time.sleep(1.0)  # để lần đo CPU đầu tiên có nghĩa
    for i in range(1, args.count + 1):
        print(f"\n===== Lần {i}: dữ liệu thu thập =====")
        print(json.dumps(collector.collect_monitor_data(), ensure_ascii=False, indent=2))
        packet = collector.monitor_packet()
        decoded = message.decode_message(packet)  # kiểm tra Server giải mã lại được
        ends_with_newline = packet.endswith(b"\n")
        print(f"\n-> gói monitor: {len(packet)} byte, kết thúc bằng \\n: {ends_with_newline}, "
              f"type={decoded['type']}")
        if i < args.count:
            time.sleep(args.interval)


if __name__ == "__main__":
    _demo()
