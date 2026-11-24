"""MOD-1.6.1 đến MOD-1.6.7:
Module tiếp nhận, phân tích, thực thi lệnh từ Server và gửi phản hồi kết quả (command_result).

Phụ trách: TV2 - Trần Minh Khâm
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from backend.agent.tcp_client import TcpClient
from backend.models import message as msg_proto

log = logging.getLogger(__name__)


class CommandHandler:
    """Tiếp nhận và thực thi các lệnh điều khiển từ Server."""

    def __init__(
        self,
        client: TcpClient,
        client_id: str,
        collector: Optional[Any] = None,
    ) -> None:
        self.client = client
        self.client_id = client_id
        self.collector = collector

    def handle_command(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """MOD-1.6.1 & MOD-1.6.2: Phân tích thông điệp command và thực thi."""
        data = msg.get("data", {})
        command_id = data.get("command_id")
        command_type = data.get("command_type")
        parameter = data.get("parameter", {})

        if not command_id or not command_type:
            log.warning("Bỏ qua lệnh thiếu command_id hoặc command_type: %s", msg)
            return None

        log.info("Nhận được lệnh từ Server: command_id=%s, type=%s, param=%s", command_id, command_type, parameter)

        # MOD-1.6.3: Phân loại và thực thi
        status, result_message, exit_code = self.dispatch_command(command_type, parameter)

        # Tạo gói tin phản hồi command_result
        result_msg = msg_proto.build_command_result(
            command_id=command_id,
            client_id=self.client_id,
            status=status,
            result_message=result_message,
            exit_code=exit_code,
        )

        # Gửi kết quả về Server
        try:
            packet = msg_proto.encode_message(result_msg)
            self.client.send_raw(packet)
            log.info("Đã gửi phản hồi lệnh %s: status=%s, exit_code=%s", command_id, status, exit_code)
        except Exception as exc:  # noqa: BLE001
            log.error("Không thể gửi phản hồi command_result: %s", exc)

        return result_msg

    def dispatch_command(self, command_type: str, parameter: Dict[str, Any]) -> tuple[str, str, int]:
        """Điều phối thực thi theo loại lệnh."""
        if command_type == msg_proto.CMD_PING_TEST:
            return self._handle_ping_test(parameter)
        elif command_type == msg_proto.CMD_GET_CONFIG:
            return self._handle_get_config(parameter)
        elif command_type == msg_proto.CMD_SHUTDOWN:
            return self._handle_shutdown(parameter)
        elif command_type == msg_proto.CMD_RESTART:
            return self._handle_restart(parameter)
        elif command_type == msg_proto.CMD_SCREEN:
            return self._handle_screen(parameter)
        else:
            log.warning("Loại lệnh không hỗ trợ hoặc ngoài allowlist: %s", command_type)
            return (
                msg_proto.STATUS_FAILED,
                f"Lệnh không được hỗ trợ trong phiên bản hiện tại: {command_type}",
                1,
            )

    def _handle_ping_test(self, parameter: Dict[str, Any]) -> tuple[str, str, int]:
        """Lệnh PING_TEST: Kiểm tra độ trễ và sự sống của Agent."""
        echo = parameter.get("echo", "pong")
        return (msg_proto.STATUS_SUCCESS, str(echo), 0)

    def _handle_get_config(self, parameter: Dict[str, Any]) -> tuple[str, str, int]:
        """MOD-1.6.7: Trả về thông tin cấu hình phần cứng/hệ điều hành."""
        if self.collector is not None:
            try:
                info = self.collector.collect_monitor_data()
                summary = {
                    "hostname": info.get("hostname"),
                    "ip_address": info.get("ip_address"),
                    "mac_address": info.get("mac_address"),
                    "os_name": info.get("os_name"),
                    "cpu_name": info.get("cpu_name"),
                    "cpu_cores": info.get("cpu_cores"),
                    "ram_total": info.get("ram_total"),
                    "disk_total": info.get("disk_total"),
                }
                return (msg_proto.STATUS_SUCCESS, json.dumps(summary, ensure_ascii=False), 0)
            except Exception as exc:  # noqa: BLE001
                return (msg_proto.STATUS_FAILED, f"Lỗi lấy cấu hình máy: {exc}", 1)
        return (msg_proto.STATUS_SUCCESS, "Cấu hình sẵn sàng (chưa liên kết collector)", 0)

    def _handle_shutdown(self, parameter: Dict[str, Any]) -> tuple[str, str, int]:
        """MOD-1.6.4: Lệnh Shutdown (mô phỏng an toàn trong bản demo/giữa kỳ)."""
        log.warning("Nhận lệnh SHUTDOWN (Chế độ mô phỏng an toàn - không tắt máy thật).")
        return (
            msg_proto.STATUS_SUCCESS,
            "Mô phỏng: Lệnh tắt máy đã được tiếp nhận an toàn (Demo mode - không tác động phần cứng)",
            0,
        )

    def _handle_restart(self, parameter: Dict[str, Any]) -> tuple[str, str, int]:
        """MOD-1.6.5: Lệnh Restart (mô phỏng an toàn trong bản demo/giữa kỳ)."""
        log.warning("Nhận lệnh RESTART (Chế độ mô phỏng an toàn - không khởi động lại máy thật).")
        return (
            msg_proto.STATUS_SUCCESS,
            "Mô phỏng: Lệnh khởi động lại đã được tiếp nhận an toàn (Demo mode - không tác động phần cứng)",
            0,
        )

    def _handle_screen(self, parameter: Dict[str, Any]) -> tuple[str, str, int]:
        """MOD-1.6.6: Lệnh Screen (mô phỏng/thông báo bảo mật)."""
        log.info("Nhận lệnh SCREEN.")
        return (
            msg_proto.STATUS_SUCCESS,
            "Mô phỏng: Chụp ảnh màn hình đã được xử lý (Demo mode)",
            0,
        )
