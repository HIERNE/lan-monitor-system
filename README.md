Hệ thống giám sát máy tính trong mạng LAN

Server Core (thành viên 3) nhận nhiều Agent qua TCP, tách JSON theo dấu xuống dòng và giữ ánh xạ client_id → socket.

Cài đặt
bash
pip install -r requirements.txt

requirements.txt cần có psutil>=5.9 (Agent dùng để đọc CPU, RAM, ổ đĩa, mạng).

Chạy TCP Server

Từ thư mục gốc dự án:

bash
python -m backend.server.main

Cấu hình nằm trong .env (mẫu: .env.example). Mặc định lắng nghe 0.0.0.0:9000. Agent trong LAN kết nối bằng IP máy chạy server, không dùng 0.0.0.0.

Hợp đồng với các thành viên khác

Agent (TV1, TV2) gửi UTF-8, mỗi thông điệp một dòng. Dưới đây là bộ tối thiểu theo hợp đồng của Server; Agent gửi thêm các trường tài nguyên (CPU, RAM, ổ đĩa, IP, MAC, uptime...). Đặc tả đầy đủ từng trường, ví dụ và các điểm còn cần chốt nằm trong protocol/messages.md.

json
{"type": "monitor", "data": {"client_id": "agent-pc-001", "hostname": "PC-01"}}
{"type": "heartbeat", "data": {"client_id": "agent-pc-001"}}
{"type": "command_result", "data": {"client_id": "agent-pc-001", "command_id": "cmd-1", "status": "SUCCESS"}}

Quy ước chung:

status viết HOA (SUCCESS, FAILED).
Lệnh Server gửi xuống Agent dùng khóa parameter (không phải params).
received_at do Server tự gán, Agent không gửi.

TV4 nhận dữ liệu đã kiểm tra bằng runtime.clients.set_event_handler(...). Các hàm cần cài: on_monitor, on_heartbeat, on_command_result, on_client_connected, on_client_disconnected, on_client_timeout. received_at là giờ UTC của server, dùng để ghi last_seen.

TV4 gửi lệnh tới Agent đang Online bằng runtime.commands.send_command(client_id=..., command_id=..., command_type="PING_TEST", parameter={}). Bản giữa kỳ chỉ cho phép PING_TEST.

Agent thu thập dữ liệu (TV1)

Chạy thử riêng phần thu thập và đóng gói gói tin, không cần Server:

bash
python -m backend.agent.system_info --count 3 --interval 2 --server-host <IP máy chạy Server>

--server-host giúp Agent chọn đúng card mạng trong LAN. Các file chính:

File	Nội dung
backend/agent/system_info.py	Thu thập CPU, RAM, ổ đĩa, IP/MAC, hệ điều hành, uptime; collector.monitor_packet() trả về bytes để sock.sendall
backend/models/message.py	Tạo, kiểm tra, mã hóa, giải mã thông điệp phía Agent
backend/models/client_model.py, metrics_model.py, command_model.py	Các lớp Model
docs/ipo_tv1_hau.md	Mô tả IPO từng module
Kiểm tra phần Server Core
bash
python -m unittest backend.tests.unit.test_message_parser backend.tests.integration.test_tcp_connection
Kiểm tra phần Agent (TV1)
bash
python -m unittest backend.tests.unit.test_message_protocol backend.tests.unit.test_system_info backend.tests.unit.test_models backend.tests.integration.test_agent_packets_tcp
Chạy toàn bộ test
bash
python -m unittest discover -v
