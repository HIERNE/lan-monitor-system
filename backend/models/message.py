"""
backend/models/message.py - Giao thức Agent <-> Server dùng chung.
Người soạn: TV1 (Hậu).  Tài liệu mô tả: protocol/messages.md

Quy ước:
  * Mỗi thông điệp là 1 đối tượng JSON {"type": ..., "data": {...}}.
  * Mã hóa UTF-8, kết thúc bằng ký tự xuống dòng "\\n" (TCP là byte stream,
    Server phải tự tách thông điệp theo "\\n").
  * Thời gian: ISO-8601, UTC. Dung lượng: byte. Phần trăm: 0..100.

Ánh xạ module:
  MOD-1.4.1  build_message / build_monitor / build_heartbeat / ...
  MOD-1.4.2  to_json
  MOD-1.4.3  add_delimiter (và encode_message = kiểm tra + 3 bước gộp lại)
  Phía Server (MOD-2.3.5, 2.3.6) dùng decode_message / validate_message.
"""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

# --------------------------------------------------------------------------
# Hằng số giao thức
# --------------------------------------------------------------------------
DELIMITER = "\n"
ENCODING = "utf-8"
MAX_MESSAGE_BYTES = 64 * 1024  # NFR-05: giới hạn kích thước 1 thông điệp

MSG_MONITOR = "monitor"
MSG_HEARTBEAT = "heartbeat"
MSG_COMMAND = "command"
MSG_COMMAND_RESULT = "command_result"
MESSAGE_TYPES = (MSG_MONITOR, MSG_HEARTBEAT, MSG_COMMAND, MSG_COMMAND_RESULT)

CMD_PING_TEST = "PING_TEST"      # lệnh mô phỏng, an toàn (giai đoạn giữa kỳ)
CMD_SHUTDOWN = "SHUTDOWN"
CMD_RESTART = "RESTART"
CMD_SCREEN = "SCREEN"
CMD_GET_CONFIG = "GET_CONFIG"    # MOD-1.6.7 gửi cấu hình thiết bị
COMMAND_TYPES = (CMD_PING_TEST, CMD_SHUTDOWN, CMD_RESTART, CMD_SCREEN, CMD_GET_CONFIG)

# Khớp hợp đồng trong README của nhóm: status viết HOA (ví dụ "SUCCESS").
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
RESULT_STATUSES = (STATUS_SUCCESS, STATUS_FAILED)


class ProtocolError(ValueError):
    """Thông điệp sai cấu trúc hoặc giá trị so với giao thức."""


# --------------------------------------------------------------------------
# Kiểm tra giá trị
# --------------------------------------------------------------------------
def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _is_iso(v: Any) -> bool:
    if not isinstance(v, str):
        return False
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


_ID, _STR, _UINT, _PCT, _ISO, _DICT, _INT = "id", "str", "uint", "percent", "iso", "dict", "int"
_CHECKS = {
    _ID: lambda v: isinstance(v, str) and v.strip() != "",
    _STR: lambda v: isinstance(v, str),
    _INT: _is_int,
    _UINT: lambda v: _is_int(v) and v >= 0,
    _PCT: lambda v: _is_num(v) and 0 <= v <= 100,
    _ISO: _is_iso,
    _DICT: lambda v: isinstance(v, dict),
}

# trường -> (kiểu, cho phép null)
MONITOR_FIELDS = {
    "client_id": (_ID, False),
    "hostname": (_STR, False),
    "ip_address": (_STR, False),
    "mac_address": (_STR, False),
    "network_name": (_STR, True),
    "os_name": (_STR, False),
    "cpu_name": (_STR, True),       # FR-02: "nếu hệ điều hành cung cấp"
    "cpu_cores": (_UINT, True),
    "cpu_threads": (_UINT, True),
    "cpu_usage": (_PCT, False),
    "ram_total": (_UINT, False),
    "ram_used": (_UINT, False),
    "ram_free": (_UINT, False),
    "ram_usage": (_PCT, False),
    "disk_total": (_UINT, False),
    "disk_used": (_UINT, False),
    "disk_free": (_UINT, False),
    "disk_usage": (_PCT, False),
    "boot_time": (_ISO, False),
    "uptime_seconds": (_UINT, False),
    "collected_at": (_ISO, False),
}
HEARTBEAT_FIELDS = {
    "client_id": (_ID, False),
    "sent_at": (_ISO, False),
}
COMMAND_FIELDS = {
    "command_id": (_ID, False),
    "client_id": (_ID, False),
    "command_type": (_STR, False),
    "parameter": (_DICT, False),   # tên khóa theo send_command(..., parameter={}) của Server
    "sent_at": (_ISO, False),
}
COMMAND_RESULT_FIELDS = {
    "command_id": (_ID, False),
    "client_id": (_ID, False),
    "status": (_STR, False),
    "result_message": (_STR, False),
    "exit_code": (_INT, True),
    "finished_at": (_ISO, False),
}
# Trường được phép vắng mặt (Server có thể chỉ gửi/nhận bộ tối thiểu theo README).
# Nếu có mặt thì vẫn bị kiểm tra kiểu/giá trị như bình thường.
_OPTIONAL = {
    MSG_HEARTBEAT: frozenset({"sent_at"}),
    MSG_COMMAND: frozenset({"client_id", "parameter", "sent_at"}),
    MSG_COMMAND_RESULT: frozenset({"result_message", "exit_code", "finished_at"}),
}
_SPECS = {
    MSG_MONITOR: MONITOR_FIELDS,
    MSG_HEARTBEAT: HEARTBEAT_FIELDS,
    MSG_COMMAND: COMMAND_FIELDS,
    MSG_COMMAND_RESULT: COMMAND_RESULT_FIELDS,
}


def _validate_fields(data: dict, spec: dict, where: str, optional=frozenset()) -> None:
    for name, (kind, nullable) in spec.items():
        if name not in data:
            if name in optional:
                continue
            raise ProtocolError(f"{where}: thiếu trường '{name}'")
        value = data[name]
        if value is None:
            if nullable:
                continue
            raise ProtocolError(f"{where}: trường '{name}' không được null")
        if not _CHECKS[kind](value):
            raise ProtocolError(f"{where}: trường '{name}' sai kiểu hoặc ngoài miền giá trị ({kind})")


def validate_message(message: Any) -> dict:
    """Kiểm tra type, data và các trường bắt buộc. Hợp lệ thì trả về chính message.

    Trường thừa trong data được chấp nhận (để mở rộng về sau mà không vỡ Server cũ).
    """
    if not isinstance(message, dict):
        raise ProtocolError("Thông điệp phải là một đối tượng JSON")
    msg_type = message.get("type")
    if not isinstance(msg_type, str) or msg_type not in MESSAGE_TYPES:
        raise ProtocolError(f"type không hợp lệ: {msg_type!r}")
    data = message.get("data")
    if not isinstance(data, dict):
        raise ProtocolError("'data' phải là một đối tượng JSON")

    _validate_fields(data, _SPECS[msg_type], msg_type, _OPTIONAL.get(msg_type, frozenset()))

    if msg_type == MSG_MONITOR:
        if data["ram_used"] > data["ram_total"]:
            raise ProtocolError("monitor: ram_used lớn hơn ram_total")
        if data["disk_used"] > data["disk_total"]:
            raise ProtocolError("monitor: disk_used lớn hơn disk_total")
    elif msg_type == MSG_COMMAND:
        if data["command_type"] not in COMMAND_TYPES:
            raise ProtocolError(f"command: command_type không hợp lệ: {data['command_type']!r}")
    elif msg_type == MSG_COMMAND_RESULT:
        if data["status"] not in RESULT_STATUSES:
            raise ProtocolError(f"command_result: status không hợp lệ: {data['status']!r}")
    return message


# --------------------------------------------------------------------------
# Tạo thông điệp  (MOD-1.4.1)
# --------------------------------------------------------------------------
def now_iso() -> str:
    """Thời gian hiện tại, UTC, ISO-8601, độ chính xác mili giây."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_command_id() -> str:
    return uuid.uuid4().hex


def build_message(msg_type: str, data: Dict[str, Any]) -> dict:
    return {"type": msg_type, "data": data}


def build_monitor(data: Dict[str, Any]) -> dict:
    return build_message(MSG_MONITOR, data)


def build_heartbeat(client_id: str, sent_at: Optional[str] = None) -> dict:
    return build_message(MSG_HEARTBEAT, {"client_id": client_id, "sent_at": sent_at or now_iso()})


def build_command(command_id: str, client_id: str, command_type: str,
                  parameter: Optional[Dict[str, Any]] = None, sent_at: Optional[str] = None) -> dict:
    return build_message(MSG_COMMAND, {
        "command_id": command_id,
        "client_id": client_id,
        "command_type": command_type,
        "parameter": parameter or {},
        "sent_at": sent_at or now_iso(),
    })


def build_command_result(command_id: str, client_id: str, status: str,
                         result_message: str = "", exit_code: Optional[int] = None,
                         finished_at: Optional[str] = None) -> dict:
    return build_message(MSG_COMMAND_RESULT, {
        "command_id": command_id,
        "client_id": client_id,
        "status": status,
        "result_message": result_message,
        "exit_code": exit_code,
        "finished_at": finished_at or now_iso(),
    })


# --------------------------------------------------------------------------
# Đóng gói / giải mã
# --------------------------------------------------------------------------
def to_json(message: dict) -> str:
    """MOD-1.4.2: dict -> chuỗi JSON gọn. Ký tự xuống dòng trong giá trị chuỗi
    luôn được escape thành \\n nên không bao giờ phá dấu phân cách."""
    return json.dumps(message, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def add_delimiter(json_text: str) -> str:
    """MOD-1.4.3: thêm ký tự phân cách thông điệp."""
    return json_text + DELIMITER


def encode_message(message: dict, validate: bool = True) -> bytes:
    """dict -> bytes sẵn sàng gửi qua socket (kiểm tra -> JSON -> thêm \\n -> UTF-8)."""
    if validate:
        validate_message(message)
    raw = add_delimiter(to_json(message)).encode(ENCODING)
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ProtocolError(f"Thông điệp quá lớn ({len(raw)} > {MAX_MESSAGE_BYTES} byte)")
    return raw


def decode_message(raw: Union[bytes, bytearray, str], validate: bool = True) -> dict:
    """Giải mã MỘT thông điệp (đã được Server tách theo \\n) -> dict.

    Mọi lỗi (quá lớn, sai UTF-8, JSON lỗi, sai cấu trúc) đều ném ProtocolError
    để Server bắt một chỗ và bỏ qua message sai mà không bị sập.
    """
    if isinstance(raw, (bytes, bytearray)):
        size = len(raw)
        try:
            text = bytes(raw).decode(ENCODING)
        except UnicodeDecodeError as exc:
            raise ProtocolError(f"Sai mã hóa UTF-8: {exc}") from exc
    elif isinstance(raw, str):
        text = raw
        size = len(raw.encode(ENCODING))
    else:
        raise ProtocolError("Đầu vào phải là bytes hoặc str")
    if size > MAX_MESSAGE_BYTES:
        raise ProtocolError(f"Thông điệp quá lớn ({size} > {MAX_MESSAGE_BYTES} byte)")

    text = text.strip()
    if not text:
        raise ProtocolError("Thông điệp rỗng")
    try:
        message = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"JSON lỗi: {exc}") from exc
    return validate_message(message) if validate else message
