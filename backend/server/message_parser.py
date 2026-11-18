"""MOD-2.3.2 đến MOD-2.3.5: buffer, tách newline, parse và validate JSON.

Agent gửi UTF-8, mỗi thông điệp một dòng (DF-02):

    {"type": "monitor"|"heartbeat"|"command_result", "data": {...}}\\n

Một lần recv có thể chỉ là một phần dòng, hoặc chứa nhiều dòng.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


INBOUND_TYPES = frozenset({"monitor", "heartbeat", "command_result"})
COMMAND_RESULT_STATUS = frozenset({"PENDING", "SUCCESS", "FAILED", "REJECTED"})
PERCENT_FIELDS = ("cpu_usage", "ram_usage", "disk_usage")


@dataclass(frozen=True)
class ParsedMessage:
    message_type: str
    data: dict


@dataclass(frozen=True)
class ParseError:
    code: str
    detail: str


class MessageTooLarge(Exception):
    """Buffer hoặc một dòng vượt MAX_MESSAGE_BYTES."""


class FrameBuffer:
    """Buffer riêng của một socket. Giữ phần chưa có newline."""

    def __init__(self, max_message_bytes: int) -> None:
        if max_message_bytes <= 0:
            raise ValueError("max_message_bytes phải lớn hơn 0")
        self.max_message_bytes = max_message_bytes
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> list[bytes]:
        if not chunk:
            return []
        self._buffer.extend(chunk)
        frames: list[bytes] = []
        while True:
            newline_at = self._buffer.find(b"\n")
            if newline_at == -1:
                if len(self._buffer) > self.max_message_bytes:
                    self._buffer.clear()
                    raise MessageTooLarge("buffer vượt giới hạn trước khi có newline")
                break
            raw_line = bytes(self._buffer[:newline_at])
            del self._buffer[: newline_at + 1]
            if raw_line.endswith(b"\r"):
                raw_line = raw_line[:-1]
            if len(raw_line) > self.max_message_bytes:
                raise MessageTooLarge("một message vượt giới hạn")
            if raw_line.strip() == b"":
                continue
            frames.append(raw_line)
        return frames

    def pending_size(self) -> int:
        return len(self._buffer)


def parse_message(frame: bytes, *, agent_token: str = "") -> ParsedMessage | ParseError:
    """Giải mã một dòng đã đủ newline. Không thực thi nội dung JSON."""
    try:
        text = frame.decode("utf-8")
    except UnicodeDecodeError:
        return ParseError("invalid_utf8", "message không phải UTF-8")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return ParseError("invalid_json", "JSON không hợp lệ")

    if not isinstance(payload, dict):
        return ParseError("invalid_schema", "root phải là object")

    message_type = payload.get("type")
    data = payload.get("data")
    if not isinstance(message_type, str) or message_type not in INBOUND_TYPES:
        return ParseError("unsupported_type", "type không thuộc monitor, heartbeat, command_result")
    if not isinstance(data, dict):
        return ParseError("invalid_schema", "data phải là object")

    if agent_token:
        supplied = data.get("token")
        if not isinstance(supplied, str) or not _token_matches(supplied, agent_token):
            return ParseError("unauthorized", "token Agent không hợp lệ")

    normalized = {key: value for key, value in data.items() if key != "token"}
    error = _validate_data(message_type, normalized)
    if error is not None:
        return error
    return ParsedMessage(message_type=message_type, data=normalized)


def _validate_data(message_type: str, data: dict) -> ParseError | None:
    client_id = _clean_text(data.get("client_id"), 100)
    if client_id is None:
        return ParseError("missing_field", "data.client_id là bắt buộc")
    data["client_id"] = client_id

    if message_type == "monitor":
        hostname = _clean_text(data.get("hostname"), 255)
        if hostname is None:
            return ParseError("missing_field", "monitor cần data.hostname")
        data["hostname"] = hostname
        return _validate_monitor_numbers(data)

    if message_type == "command_result":
        command_id = _clean_text(data.get("command_id"), 64)
        status = data.get("status")
        if command_id is None:
            return ParseError("missing_field", "command_result cần data.command_id")
        if not isinstance(status, str) or status not in COMMAND_RESULT_STATUS:
            return ParseError("invalid_field", "status không thuộc PENDING, SUCCESS, FAILED, REJECTED")
        data["command_id"] = command_id
        if "exit_code" in data and not _is_int(data["exit_code"]):
            return ParseError("invalid_field", "exit_code phải là số nguyên")
        if "result_message" in data and data["result_message"] is not None:
            if not isinstance(data["result_message"], str):
                return ParseError("invalid_field", "result_message phải là chuỗi")
    return None


def _validate_monitor_numbers(data: dict) -> ParseError | None:
    for field in PERCENT_FIELDS:
        if field not in data or data[field] is None:
            continue
        if not _is_number(data[field]) or not 0 <= float(data[field]) <= 100:
            return ParseError("invalid_field", f"{field} phải nằm trong khoảng 0–100")

    integer_fields = ("cpu_cores", "uptime_seconds")
    for field in integer_fields:
        if field not in data or data[field] is None:
            continue
        if not _is_int(data[field]) or int(data[field]) < 0:
            return ParseError("invalid_field", f"{field} phải là số nguyên không âm")

    float_fields = (
        "ram_total_mb",
        "ram_used_mb",
        "ram_free_mb",
        "disk_total_gb",
        "disk_used_gb",
        "disk_free_gb",
    )
    for field in float_fields:
        if field not in data or data[field] is None:
            continue
        if not _is_number(data[field]) or float(data[field]) < 0:
            return ParseError("invalid_field", f"{field} phải là số không âm")
    return None


def _clean_text(value: object, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > max_length:
        return None
    if any(ord(char) < 32 for char in text):
        return None
    return text


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _token_matches(supplied: str, expected: str) -> bool:
    import hmac

    return hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))
