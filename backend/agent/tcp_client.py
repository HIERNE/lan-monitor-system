"""MOD-1.1.3, MOD-1.1.4, MOD-1.4.4, MOD-1.5.3, MOD-1.5.4:
Module quản lý kết nối TCP Client, gửi dữ liệu phân tách bằng newline,
lắng nghe lệnh từ Server và tự động kết nối lại (Reconnect).

Phụ trách: TV2 - Trần Minh Khâm
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from typing import Callable, Optional

from backend.models import message as msg_proto

log = logging.getLogger(__name__)


class TcpClient:
    """Quản lý kết nối TCP Socket tới Server Core."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9000,
        timeout: float = 5.0,
        reconnect_interval: float = 5.0,
        max_message_bytes: int = 65536,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.timeout = float(timeout)
        self.reconnect_interval = float(reconnect_interval)
        self.max_message_bytes = int(max_message_bytes)

        self._sock: Optional[socket.socket] = None
        self._connected = False
        self._send_lock = threading.Lock()
        self._stop_event = threading.Event()

        self._on_command_callback: Optional[Callable[[dict], None]] = None
        self._on_status_callback: Optional[Callable[[bool, str], None]] = None

        self._receiver_thread: Optional[threading.Thread] = None
        self._reconnect_thread: Optional[threading.Thread] = None

    @property
    def is_connected(self) -> bool:
        return self._connected and self._sock is not None

    def set_on_command_callback(self, callback: Callable[[dict], None]) -> None:
        """Đăng ký hàm xử lý khi nhận lệnh (command) từ Server."""
        self._on_command_callback = callback

    def set_on_status_callback(self, callback: Callable[[bool, str], None]) -> None:
        """Đăng ký hàm cập nhật trạng thái kết nối (dùng cho Tray UI)."""
        self._on_status_callback = callback

    def _notify_status(self, connected: bool, message: str) -> None:
        if self._on_status_callback:
            try:
                self._on_status_callback(connected, message)
            except Exception as exc:  # noqa: BLE001
                log.warning("Lỗi trong status callback: %s", exc)

    def connect(self) -> bool:
        """MOD-1.1.4: Thiết lập kết nối TCP tới Server."""
        with self._send_lock:
            self._close_socket()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.settimeout(self.timeout)
                log.info("Đang kết nối tới Server tại %s:%d...", self.host, self.port)
                sock.connect((self.host, self.port))
                self._sock = sock
                self._connected = True
                log.info("Kết nối TCP tới Server thành công: %s:%d", self.host, self.port)
                self._notify_status(True, f"Đã kết nối: {self.host}:{self.port}")
                return True
            except (OSError, socket.error) as exc:
                self._connected = False
                log.warning("Không thể kết nối tới Server (%s:%d): %s", self.host, self.port, exc)
                self._notify_status(False, f"Mất kết nối: {exc}")
                return False

    def disconnect(self) -> None:
        """MOD-1.5.3: Xử lý ngắt kết nối an toàn."""
        with self._send_lock:
            self._connected = False
            self._close_socket()
        self._notify_status(False, "Chưa kết nối")

    def _close_socket(self) -> None:
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def send_raw(self, data: bytes) -> bool:
        """MOD-1.4.4: Gửi luồng byte (đã kèm newline) qua socket."""
        if not data:
            return True
        with self._send_lock:
            if not self._connected or self._sock is None:
                log.debug("Bỏ qua gửi dữ liệu vì socket chưa kết nối.")
                return False
            try:
                self._sock.sendall(data)
                return True
            except (OSError, socket.error) as exc:
                log.warning("Lỗi gửi dữ liệu qua TCP: %s. Đóng socket.", exc)
                self._connected = False
                self._close_socket()
                self._notify_status(False, f"Lỗi gửi dữ liệu: {exc}")
                return False

    def send_message(self, msg: dict) -> bool:
        """Mã hóa dict thông điệp thành JSON UTF-8 kèm newline và gửi đi."""
        try:
            packet = msg_proto.encode_message(msg)
            return self.send_raw(packet)
        except msg_proto.ProtocolError as exc:
            log.error("Thông điệp không hợp lệ theo protocol: %s", exc)
            return False

    def start_background_workers(self) -> None:
        """Khởi động luồng nhận dữ liệu và luồng tự động kết nối lại."""
        self._stop_event.clear()
        if self._receiver_thread is None or not self._receiver_thread.is_alive():
            self._receiver_thread = threading.Thread(
                target=self._receive_loop,
                name="Agent-TcpReceiver",
                daemon=True,
            )
            self._receiver_thread.start()

        if self._reconnect_thread is None or not self._reconnect_thread.is_alive():
            self._reconnect_thread = threading.Thread(
                target=self._reconnect_loop,
                name="Agent-AutoReconnect",
                daemon=True,
            )
            self._reconnect_thread.start()

    def _receive_loop(self) -> None:
        """MOD-1.6.1: Vòng lặp nhận dữ liệu từ Server, đệm byte và tách theo newline."""
        buffer = bytearray()
        while not self._stop_event.is_set():
            if not self.is_connected:
                time.sleep(0.5)
                buffer.clear()
                continue

            sock = self._sock
            if sock is None:
                time.sleep(0.5)
                continue

            try:
                sock.settimeout(1.0)
                chunk = sock.recv(4096)
            except socket.timeout:
                continue
            except (OSError, socket.error) as exc:
                if not self._stop_event.is_set():
                    log.warning("Socket bị ngắt khi đang nhận: %s", exc)
                    self.disconnect()
                break

            if not chunk:
                log.info("Server đã đóng kết nối.")
                self.disconnect()
                continue

            buffer.extend(chunk)
            while True:
                newline_pos = buffer.find(b"\n")
                if newline_pos == -1:
                    if len(buffer) > self.max_message_bytes:
                        log.warning("Buffer vượt giới hạn %d byte. Xóa buffer.", self.max_message_bytes)
                        buffer.clear()
                    break

                raw_line = bytes(buffer[:newline_pos])
                del buffer[: newline_pos + 1]

                if raw_line.endswith(b"\r"):
                    raw_line = raw_line[:-1]

                if not raw_line.strip():
                    continue

                self._process_inbound_line(raw_line)

    def _process_inbound_line(self, line: bytes) -> None:
        """Giải mã và định tuyến gói tin nhận được."""
        try:
            msg = msg_proto.decode_message(line)
        except msg_proto.ProtocolError as exc:
            log.warning("Bỏ qua thông điệp không hợp lệ từ Server: %s", exc)
            return

        msg_type = msg.get("type")
        if msg_type == msg_proto.MSG_COMMAND:
            if self._on_command_callback:
                try:
                    self._on_command_callback(msg)
                except Exception as exc:  # noqa: BLE001
                    log.error("Lỗi khi xử lý callback command: %s", exc)
        else:
            log.debug("Nhận được thông điệp type=%s từ Server", msg_type)

    def _reconnect_loop(self) -> None:
        """MOD-1.5.4: Luồng tự động kết nối lại khi mất liên lạc với Server."""
        while not self._stop_event.is_set():
            if not self.is_connected:
                log.debug("Đang thử kết nối lại tới Server...")
                success = self.connect()
                if success:
                    log.info("Tự động kết nối lại thành công!")
            # Chờ reconnect_interval hoặc dừng khi stop_event được bật
            self._stop_event.wait(timeout=self.reconnect_interval)

    def stop(self) -> None:
        """Dừng toàn bộ kết nối và các luồng nền của TCP Client."""
        self._stop_event.set()
        self.disconnect()
        if self._receiver_thread and self._receiver_thread.is_alive():
            self._receiver_thread.join(timeout=2.0)
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=2.0)
        log.info("Đã dừng TcpClient an toàn.")
