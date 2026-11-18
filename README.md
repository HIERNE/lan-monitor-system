# Hệ thống giám sát máy tính trong mạng LAN

Server Core (thành viên 3) nhận nhiều Agent qua TCP, tách JSON theo dấu xuống dòng và giữ ánh xạ `client_id → socket`.

## Chạy TCP Server

Từ thư mục gốc dự án:

```bash
python -m backend.server.main
```

Cấu hình nằm trong `.env` (mẫu: `.env.example`). Mặc định lắng nghe `0.0.0.0:9000`. Agent trong LAN kết nối bằng IP máy chạy server, không dùng `0.0.0.0`.

## Hợp đồng với các thành viên khác

Agent (TV1, TV2) gửi UTF-8, mỗi thông điệp một dòng:

```json
{"type": "monitor", "data": {"client_id": "agent-pc-001", "hostname": "PC-01"}}
{"type": "heartbeat", "data": {"client_id": "agent-pc-001"}}
{"type": "command_result", "data": {"client_id": "agent-pc-001", "command_id": "cmd-1", "status": "SUCCESS"}}
```

TV4 nhận dữ liệu đã kiểm tra bằng `runtime.clients.set_event_handler(...)`. Các hàm cần cài: `on_monitor`, `on_heartbeat`, `on_command_result`, `on_client_connected`, `on_client_disconnected`, `on_client_timeout`. `received_at` là giờ UTC của server, dùng để ghi `last_seen`.

TV4 gửi lệnh tới Agent đang Online bằng `runtime.commands.send_command(client_id=..., command_id=..., command_type="PING_TEST", parameter={})`. Bản giữa kỳ chỉ cho phép `PING_TEST`.

## Kiểm tra phần Server Core

```bash
python -m unittest backend.tests.unit.test_message_parser backend.tests.integration.test_tcp_connection
```
