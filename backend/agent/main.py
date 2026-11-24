"""MOD-1.1.1: Điểm khởi chạy chính của Client Agent.
Tích hợp:
  - TV1: SystemInfoCollector (thu thập thông tin hệ thống và đóng gói gói tin monitor)
  - TV2: TcpClient, HeartbeatWorker, CommandHandler, TrayApp
  - TV3: Kết nối tới TCP Server, duy trì định dạng chuẩn JSON newline-delimited

Phụ trách: TV2 - Trần Minh Khâm
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
import time
from typing import Optional

# Tải cấu hình từ .env nếu có
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend.agent.command_handler import CommandHandler
from backend.agent.heartbeat import HeartbeatWorker
from backend.agent.system_info import SystemInfoCollector, get_hostname
from backend.agent.tcp_client import TcpClient
from backend.agent.tray_app import TrayApp

log = logging.getLogger("backend.agent")


class AgentApp:
    """Ứng dụng Client Agent hoàn chỉnh."""

    def __init__(
        self,
        server_host: str = "127.0.0.1",
        server_port: int = 9000,
        monitor_interval: float = 5.0,
        heartbeat_interval: float = 5.0,
        reconnect_interval: float = 5.0,
        agent_token: str = "",
        enable_tray: bool = True,
    ) -> None:
        self.server_host = server_host
        self.server_port = server_port
        self.monitor_interval = max(1.0, float(monitor_interval))
        self.heartbeat_interval = max(1.0, float(heartbeat_interval))
        self.reconnect_interval = max(1.0, float(reconnect_interval))
        self.agent_token = agent_token
        self.enable_tray = enable_tray

        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

        log.info("Khởi tạo SystemInfoCollector (TV1)...")
        self.collector = SystemInfoCollector(server_host=self.server_host)
        self.client_id = self.collector.client_id
        self.hostname = get_hostname()

        log.info("Agent Client ID: %s | Hostname: %s", self.client_id, self.hostname)

        # Khởi tạo TCP Client
        self.tcp_client = TcpClient(
            host=self.server_host,
            port=self.server_port,
            timeout=5.0,
            reconnect_interval=self.reconnect_interval,
        )

        # Khởi tạo bộ xử lý lệnh
        self.command_handler = CommandHandler(
            client=self.tcp_client,
            client_id=self.client_id,
            collector=self.collector,
        )
        self.tcp_client.set_on_command_callback(self.command_handler.handle_command)

        # Khởi tạo bộ gửi Heartbeat
        self.heartbeat_worker = HeartbeatWorker(
            client=self.tcp_client,
            client_id=self.client_id,
            interval_sec=self.heartbeat_interval,
            agent_token=self.agent_token,
        )

        # Khởi tạo System Tray UI
        server_addr = f"{self.server_host}:{self.server_port}"
        self.tray = TrayApp(
            client_id=self.client_id,
            hostname=self.hostname,
            server_address=server_addr,
            is_connected_fn=lambda: self.tcp_client.is_connected,
            on_reconnect_fn=self.tcp_client.connect,
            on_exit_fn=self.stop,
            collector=self.collector,
        )
        self.tcp_client.set_on_status_callback(self.tray.update_status)

    def start(self) -> None:
        """Bắt đầu chạy Agent."""
        log.info("Bắt đầu khởi động các dịch vụ Agent...")
        self._stop_event.clear()

        # Bắt đầu worker của TCP Client (lắng nghe và tự động reconnect)
        self.tcp_client.start_background_workers()

        # Thử kết nối lần đầu
        self.tcp_client.connect()

        # Bắt đầu Heartbeat
        self.heartbeat_worker.start()

        # Bắt đầu gửi dữ liệu monitor định kỳ
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="Agent-MonitorSender",
            daemon=True,
        )
        self._monitor_thread.start()

        # Khởi động Tray UI trên Main Thread
        if self.enable_tray:
            self.tray.run()
        else:
            log.info("Agent đang chạy ở chế độ Console (CLI) không có Tray.")
            try:
                while not self._stop_event.is_set():
                    time.sleep(0.5)
            except KeyboardInterrupt:
                log.info("Nhận tín hiệu dừng từ bàn phím (Ctrl+C).")
                self.stop()

    def _monitor_loop(self) -> None:
        """Luồng gửi gói tin monitor định kỳ."""
        # Chờ 1 giây đầu tiên để các bộ đếm CPU sẵn sàng
        time.sleep(1.0)
        while not self._stop_event.is_set():
            if self.tcp_client.is_connected:
                try:
                    packet = self.collector.monitor_packet()
                    success = self.tcp_client.send_raw(packet)
                    if success:
                        log.debug("Đã gửi thành công gói tin monitor (%d bytes)", len(packet))
                except Exception as exc:  # noqa: BLE001
                    log.error("Lỗi khi thu thập hoặc gửi monitor: %s", exc)

            # Chờ đúng chu kỳ monitor
            if self._stop_event.wait(timeout=self.monitor_interval):
                break

    def stop(self) -> None:
        """MOD-1.2.5: Dừng toàn bộ Agent và giải phóng tài nguyên."""
        if self._stop_event.is_set():
            return
        log.info("Đang dừng ứng dụng Agent...")
        self._stop_event.set()

        # Dừng heartbeat
        self.heartbeat_worker.stop()

        # Dừng TCP Client
        self.tcp_client.stop()

        # Dừng luồng monitor
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)

        log.info("Ứng dụng Agent đã dừng hoàn toàn.")


def main() -> None:
    parser = argparse.ArgumentParser(description="LAN Monitor System - Client Agent")
    parser.add_argument(
        "--server-host",
        default=os.getenv("SERVER_HOST", "127.0.0.1"),
        help="Địa chỉ IP của TCP Server (mặc định: 127.0.0.1 hoặc lấy từ SERVER_HOST)",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=int(os.getenv("SERVER_PORT", "9000")),
        help="Cổng TCP Server (mặc định: 9000)",
    )
    parser.add_argument(
        "--monitor-interval",
        type=float,
        default=float(os.getenv("MONITOR_INTERVAL_SEC", "5.0")),
        help="Chu kỳ gửi monitor tính bằng giây (mặc định: 5.0)",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=float(os.getenv("HEARTBEAT_INTERVAL_SEC", "5.0")),
        help="Chu kỳ gửi heartbeat tính bằng giây (mặc định: 5.0)",
    )
    parser.add_argument(
        "--reconnect-interval",
        type=float,
        default=float(os.getenv("RECONNECT_INTERVAL_SEC", "5.0")),
        help="Khoảng thời gian chờ kết nối lại (mặc định: 5.0)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("AGENT_TOKEN", ""),
        help="Mã token xác thực nếu Server yêu cầu",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Chạy ngầm không mở biểu tượng System Tray (Console Mode)",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Mức ghi log (mặc định: INFO)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    )

    agent = AgentApp(
        server_host=args.server_host,
        server_port=args.server_port,
        monitor_interval=args.monitor_interval,
        heartbeat_interval=args.heartbeat_interval,
        reconnect_interval=args.reconnect_interval,
        agent_token=args.token,
        enable_tray=not args.no_tray,
    )

    # Đăng ký signal handler để dừng an toàn trên Unix/Windows
    def _sig_handler(sig, frame):
        log.info("Nhận tín hiệu kết thúc hệ thống (%s)...", sig)
        agent.stop()
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
    except Exception:
        pass

    agent.start()


if __name__ == "__main__":
    main()
