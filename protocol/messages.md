Giao thức Agent ↔ Server (protocol/messages.md)

Người soạn: TV1 (Hậu). Mã nguồn tham chiếu phía Agent: backend/models/message.py. Đã đối chiếu với phần "Hợp đồng với các thành viên khác" trong README.md (Server Core, TV3). Mọi thay đổi giao thức phải báo cả nhóm và cập nhật file này TRƯỚC khi sửa code.

1. Quy tắc chung
Mục	Quy ước
Kênh truyền	TCP Socket, Agent là bên chủ động kết nối tới Server
Địa chỉ Server	IP của máy chạy Server (không dùng 0.0.0.0), cổng mặc định 9000, cấu hình trong .env
Định dạng	Mỗi thông điệp là một đối tượng JSON: {"type": "...", "data": {...}}
Mã hóa	UTF-8
Phân cách	Mỗi thông điệp một dòng, kết thúc bằng ký tự xuống dòng \n. Không có \n thô bên trong JSON (xuống dòng trong chuỗi luôn được escape)
Kích thước tối đa	64 KB mỗi thông điệp
Thời gian	ISO-8601, UTC, mili giây, ví dụ 2026-11-18T02:00:00.000+00:00
Dung lượng	Byte (số nguyên không âm)
Phần trăm	Số thực 0 đến 100, làm tròn 1 chữ số
Giá trị trạng thái	Viết HOA: SUCCESS, FAILED
Trường thừa	Bên nhận bỏ qua trường không biết (để mở rộng mà không vỡ bản cũ)
Giá trị null	Chỉ các trường ghi "null được" trong bảng bên dưới
received_at	Do Server tự gán (giờ UTC lúc nhận) để ghi last_seen; Agent không gửi trường này

TCP là dòng byte: một lần recv có thể chứa nửa thông điệp hoặc nhiều thông điệp, nên phía nhận phải đệm rồi tách theo \n (Server Core đã làm bằng FrameBuffer).

2. Bốn loại thông điệp
type	Hướng	Khi nào gửi
monitor	Agent → Server	Định kỳ (mặc định 5 giây)
heartbeat	Agent → Server	Định kỳ (mặc định 5 giây) để chứng tỏ còn sống
command	Server → Agent	Khi Admin gửi lệnh (Server gọi runtime.commands.send_command(...))
command_result	Agent → Server	Sau khi Agent xử lý xong một command

Quy ước "bắt buộc" và "Agent gửi thêm": mỗi bảng dưới đây ghi rõ trường nào là bộ tối thiểu theo hợp đồng của Server (cột Bắt buộc: có) và trường nào Agent gửi thêm cho đủ dữ liệu giám sát (cột Bắt buộc: không, hoặc null được).

2.1. monitor: thông tin định danh, cấu hình và tài nguyên

Tối thiểu theo hợp đồng: client_id, hostname. Agent luôn gửi đủ toàn bộ các trường dưới đây.

Trường	Kiểu	Bắt buộc	Null được	Ý nghĩa
client_id	chuỗi khác rỗng	có	không	Định danh máy. Ví dụ trong README là agent-pc-001; bản Agent hiện lấy MAC của card mạng đang dùng
hostname	chuỗi	có	không	Tên máy
ip_address	chuỗi	không	không	IP trong LAN
mac_address	chuỗi	không	không	AA:BB:CC:DD:EE:FF
network_name	chuỗi	không	có	Tên card mạng (Wi-Fi, Ethernet, eth0...)
os_name	chuỗi	không	không	Ví dụ Windows 11 (10.0.22631)
cpu_name	chuỗi	không	có	Tên CPU, null nếu hệ điều hành không cung cấp
cpu_cores	số nguyên ≥ 0	không	có	Số lõi vật lý
cpu_threads	số nguyên ≥ 0	không	có	Số luồng logic
cpu_usage	%	không	không	CPU đang dùng
ram_total / ram_used / ram_free	số nguyên ≥ 0 (byte)	không	không	ram_free là bộ nhớ khả dụng; ram_used = ram_total - ram_free
ram_usage	%	không	không	ram_used / ram_total
disk_total / disk_used / disk_free	số nguyên ≥ 0 (byte)	không	không	Ổ hệ thống (ổ C: trên Windows, / trên Linux/macOS)
disk_usage	%	không	không	disk_used / disk_total
boot_time	ISO-8601	không	không	Thời điểm máy khởi động
uptime_seconds	số nguyên ≥ 0	không	không	Số giây từ lúc khởi động
collected_at	ISO-8601	không	không	Thời điểm thu thập mẫu (dùng làm mốc lịch sử)

Ràng buộc thêm: ram_used ≤ ram_total, disk_used ≤ disk_total.

json
{
  "type": "monitor",
  "data": {
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
    "collected_at": "2026-11-18T02:00:00.000+00:00"
  }
}
2.2. heartbeat

Tối thiểu theo hợp đồng: client_id. Agent gửi kèm sent_at.

Trường	Kiểu	Bắt buộc	Ý nghĩa
client_id	chuỗi khác rỗng	có	Máy gửi
sent_at	ISO-8601	không	Thời điểm gửi
json
{
  "type": "heartbeat",
  "data": {
    "client_id": "AA:BB:CC:DD:EE:FF",
    "sent_at": "2026-11-18T02:00:05.000+00:00"
  }
}
2.3. command (Server → Agent)

Server gửi bằng send_command(client_id=..., command_id=..., command_type="PING_TEST", parameter={}). Khóa tham số là parameter (không phải params).

Trường	Kiểu	Bắt buộc	Ý nghĩa
command_id	chuỗi khác rỗng	có	Mã lệnh duy nhất, dùng để ghép với kết quả (ví dụ cmd-1)
command_type	một trong PING_TEST, SHUTDOWN, RESTART, SCREEN, GET_CONFIG	có	Loại lệnh
client_id	chuỗi khác rỗng	không	Máy đích
parameter	đối tượng JSON (có thể rỗng {})	không	Tham số riêng của lệnh
sent_at	ISO-8601	không	Thời điểm Server gửi

Bản giữa kỳ chỉ cho phép PING_TEST (lệnh mô phỏng). SHUTDOWN, RESTART chỉ bật khi đã có xác thực, phân quyền và bước xác nhận.

json
{
  "type": "command",
  "data": {
    "command_id": "cmd-1",
    "client_id": "AA:BB:CC:DD:EE:FF",
    "command_type": "PING_TEST",
    "parameter": {},
    "sent_at": "2026-11-18T02:01:00.000+00:00"
  }
}
2.4. command_result (Agent → Server)

Tối thiểu theo hợp đồng: client_id, command_id, status. Agent gửi đủ các trường dưới đây.

Trường	Kiểu	Bắt buộc	Null được	Ý nghĩa
client_id	chuỗi khác rỗng	có	không	Máy trả lời
command_id	chuỗi khác rỗng	có	không	Mã lệnh đang trả lời
status	SUCCESS hoặc FAILED	có	không	Kết quả (viết hoa)
result_message	chuỗi (có thể rỗng)	không	không	Nội dung kết quả hoặc thông báo lỗi
exit_code	số nguyên	không	có	Mã thoát nếu có
finished_at	ISO-8601	không	không	Thời điểm xử lý xong
json
{
  "type": "command_result",
  "data": {
    "command_id": "cmd-1",
    "client_id": "AA:BB:CC:DD:EE:FF",
    "status": "SUCCESS",
    "result_message": "pong",
    "exit_code": 0,
    "finished_at": "2026-11-18T02:01:00.250+00:00"
  }
}
3. Cách dùng trong code
python
from backend.models import message

# Agent: tạo và gửi (đã kèm "\n")
sock.sendall(message.encode_message(message.build_heartbeat(client_id)))
# hoặc dùng sẵn: sock.sendall(collector.monitor_packet())

# Agent: đọc lệnh Server gửi xuống (đã tách từng dòng)
try:
    msg = message.decode_message(line)
except message.ProtocolError as exc:
    log.warning("Bỏ qua thông điệp sai: %s", exc)      # KHÔNG để sập Agent

message.py phục vụ Agent (tạo gói tin, đọc lệnh) và các test. Server Core có bộ tách/kiểm tra riêng (FrameBuffer, parser trong backend/server).

4. Gợi ý ánh xạ sang CSDL (Hiển quyết định cuối cùng)
Bảng	Lấy từ monitor
clients (thông tin hiện tại, insert/update theo client_id)	client_id, hostname, ip_address, mac_address, os_name, cpu_name, cpu_cores, cpu_threads, ram_total, disk_total, boot_time
client_metrics (lịch sử, chỉ thêm mới)	client_id, collected_at (hoặc received_at của Server), cpu_usage, ram_used, ram_free, ram_usage, disk_used, disk_free, disk_usage, uptime_seconds
commands	các trường của command và command_result
5. Điểm chưa chốt, cần đối chiếu với parser của Server (Hiển)

Các mục này chưa thể khẳng định chỉ từ README.md; cần mở file parser trong backend/server để kiểm tra rồi cập nhật bảng này.

#	Câu hỏi	Vì sao cần	Người xác nhận
1	Token: parser kiểm tra token (có test test_token_is_checked_and_removed). Token nằm ở đâu trong thông điệp (ngoài cùng hay trong data) và lấy từ cấu hình nào?	Agent hiện chưa gửi token, nên nếu Server bắt buộc thì Agent bị từ chối	Hiển
2	Tên trường phần trăm mà parser kiểm tra khoảng 0 đến 100 (có test test_monitor_requires_hostname_and_percent_range). Có phải cpu_usage, ram_usage, disk_usage không?	Nếu Server dùng tên khác, dữ liệu CPU/RAM/ổ đĩa sẽ không được kiểm tra hoặc không được lưu	Hiển
3	Server có từ chối trường thừa không? Agent gửi nhiều trường hơn ví dụ trong README	Nếu từ chối, monitor đầy đủ sẽ bị loại	Hiển
4	Định dạng thực tế của thông điệp command Server gửi xuống: khóa nào, có client_id, sent_at không?	Agent đọc lệnh bằng decode_message; bản hiện tại chỉ bắt buộc command_id và command_type	Hiển, Phước
5	client_id: README ví dụ agent-pc-001, Agent hiện dùng MAC. Chọn kiểu nào làm chuẩn?	Cần thống nhất để khóa clients ổn định	Cả nhóm
6	Giá trị status của FAILED: Server có chấp nhận đúng chuỗi FAILED không? README chỉ nêu SUCCESS	Tránh lệnh thất bại bị từ chối	Hiển
6. Hạn chế đã biết
client_id theo MAC chỉ là định danh thử nghiệm (MAC có thể đổi hoặc bị giả mạo). Có thể nâng cấp sang UUID lưu bền vững mà không đổi giao thức.
Chưa mã hóa (TLS): chỉ dùng trong LAN thử nghiệm.
