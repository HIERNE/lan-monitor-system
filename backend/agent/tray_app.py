"""MOD-1.1.2 và nhóm 1.2 (MOD-1.2.1 đến MOD-1.2.5):
Giao diện khay hệ thống (System Tray) cho Client Agent trên Windows.

Phụ trách: TV2 - Trần Minh Khâm
"""

from __future__ import annotations

import ctypes
import logging
import platform
import threading
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

# Thử import pystray và Pillow (hỗ trợ graceful fallback nếu chưa cài thư viện GUI)
try:
    from PIL import Image, ImageDraw
    import pystray
    HAS_GUI = True
except ImportError:
    HAS_GUI = False
    log.warning("Chưa cài pystray hoặc Pillow. Agent sẽ chạy ở chế độ nền (CLI mode).")


class TrayApp:
    """Quản lý biểu tượng khay hệ thống và menu thao tác Agent."""

    def __init__(
        self,
        client_id: str,
        hostname: str,
        server_address: str,
        is_connected_fn: Callable[[], bool],
        on_reconnect_fn: Callable[[], None],
        on_exit_fn: Callable[[], None],
        collector: Optional[Any] = None,
    ) -> None:
        self.client_id = client_id
        self.hostname = hostname
        self.server_address = server_address
        self.is_connected_fn = is_connected_fn
        self.on_reconnect_fn = on_reconnect_fn
        self.on_exit_fn = on_exit_fn
        self.collector = collector

        self._icon: Optional[pystray.Icon] = None if HAS_GUI else None
        self._stop_event = threading.Event()
        self.status_text = "Khởi tạo..."

    def _create_icon_image(self, connected: bool) -> Any:
        """Tạo icon 64x64 hình tròn: Xanh lá khi Online, Đỏ khi Offline."""
        if not HAS_GUI:
            return None
        width, height = 64, 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        color = (40, 167, 69) if connected else (220, 53, 69)
        draw.ellipse((4, 4, width - 4, height - 4), fill=color, outline=(255, 255, 255), width=3)
        return image

    def update_status(self, connected: bool, message: str) -> None:
        """Cập nhật trạng thái hiển thị trên khay hệ thống."""
        self.status_text = message
        if HAS_GUI and self._icon is not None:
            try:
                self._icon.icon = self._create_icon_image(connected)
                status_label = "Online" if connected else "Offline"
                self._icon.title = f"LAN Monitor Agent [{status_label}]\n{message}"
            except Exception as exc:  # noqa: BLE001
                log.debug("Lỗi cập nhật icon tray: %s", exc)

    def _show_info_dialog(self) -> None:
        """MOD-1.2.3: Hiển thị hộp thoại xem thông tin Agent."""
        ip = "N/A"
        mac = "N/A"
        if self.collector:
            try:
                data = self.collector.collect_monitor_data()
                ip = data.get("ip_address", "N/A")
                mac = data.get("mac_address", "N/A")
            except Exception:
                pass

        state = "Đã kết nối" if self.is_connected_fn() else "Mất kết nối"
        content = (
            f"--- THÔNG TIN AGENT ---\n"
            f"Client ID: {self.client_id}\n"
            f"Hostname: {self.hostname}\n"
            f"Địa chỉ IP: {ip}\n"
            f"Địa chỉ MAC: {mac}\n"
            f"Server: {self.server_address}\n"
            f"Trạng thái: {state}\n"
            f"Chi tiết: {self.status_text}"
        )
        log.info("\n%s", content)

        if platform.system() == "Windows":
            try:
                ctypes.windll.user32.MessageBoxW(0, content, "LAN Monitor - Thông tin Agent", 0x40)
            except Exception as exc:  # noqa: BLE001
                log.debug("Không thể mở Windows MessageBox: %s", exc)

    def _lock_workstation(self) -> None:
        """MOD-1.2.4: Thực hiện lệnh khóa màn hình máy tính."""
        log.info("Thực hiện lệnh Khóa màn hình (Lock Workstation).")
        if platform.system() == "Windows":
            try:
                ctypes.windll.user32.LockWorkStation()
            except Exception as exc:  # noqa: BLE001
                log.warning("Lỗi khi gọi Windows LockWorkStation: %s", exc)
        else:
            log.info("Chức năng khóa màn hình chỉ khả dụng trên Windows.")

    def _build_menu(self) -> pystray.Menu:
        """Xây dựng menu ngữ cảnh chuột phải."""
        return pystray.Menu(
            pystray.MenuItem(
                lambda text: f"Trạng thái: {'Đã kết nối' if self.is_connected_fn() else 'Mất kết nối'}",
                None,
                enabled=False,
            ),
            pystray.MenuItem("Xem thông tin Agent (MOD-1.2.3)", lambda: self._show_info_dialog()),
            pystray.MenuItem("Thử kết nối lại ngay (MOD-1.2.2)", lambda: self.on_reconnect_fn()),
            pystray.MenuItem("Khóa máy tính (MOD-1.2.4)", lambda: self._lock_workstation()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Thoát Agent (MOD-1.2.5)", lambda: self.stop()),
        )

    def run(self) -> None:
        """MOD-1.1.2: Chạy vòng lặp sự kiện của System Tray."""
        if not HAS_GUI:
            log.info("Chạy Agent ở chế độ Console (CLI) do không có pystray/Pillow.")
            self._stop_event.wait()
            return

        icon_image = self._create_icon_image(self.is_connected_fn())
        self._icon = pystray.Icon(
            name="lan_monitor_agent",
            icon=icon_image,
            title="LAN Monitor Agent",
            menu=self._build_menu(),
        )
        log.info("Khởi động System Tray Icon...")
        try:
            self._icon.run()
        except Exception as exc:  # noqa: BLE001
            log.warning("Lỗi vòng lặp System Tray: %s. Chuyển sang chờ tín hiệu.", exc)
            self._stop_event.wait()

    def stop(self) -> None:
        """MOD-1.2.5: Đóng Tray và kích hoạt thoát chương trình."""
        log.info("Đang đóng giao diện System Tray...")
        self._stop_event.set()
        if HAS_GUI and self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
        # Gọi callback thoát toàn bộ ứng dụng
        self.on_exit_fn()
