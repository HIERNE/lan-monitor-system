# BÁO CÁO PHÂN TÍCH VÀ ĐẶC TẢ MODULE (IPO) - THÀNH VIÊN 2
**Sinh viên thực hiện:** Trần Minh Khâm  
**Mã phân hệ:** GRP-01 (Truyền tải dữ liệu), GRP-04 (Điều khiển từ xa), GRP-05 (Client Agent System Tray)  
**Vai trò:** TV2 – Agent Communication & System Tray  

---

## 1. TỔNG QUAN PHÂN HỆ VÀ TRÁCH NHIỆM
Thành viên 2 phụ trách toàn bộ kênh giao tiếp TCP Client giữa máy trạm (Agent) và Server trung tâm, gửi gói tin `monitor` và `heartbeat`, duy trì kết nối (Auto Reconnect), tiếp nhận và thực thi các lệnh điều khiển (`command` / `command_result`), và giao diện khay hệ thống (System Tray) trên Windows.

---

## 2. ĐẶC TẢ CHI TIẾT CÁC MODULE (IPO)

### 2.1. Nhóm khởi động và kết nối TCP Socket
#### MOD-1.1.3: Khởi tạo TCP Socket
* **Input:** Cấu hình `SERVER_HOST`, `SERVER_PORT`, timeout, tùy chọn socket.
* **Process:** Tạo socket `socket.AF_INET, socket.SOCK_STREAM`, cấu hình `TCP_NODELAY`, thiết lập thời gian timeout.
* **Output:** Đối tượng socket TCP sẵn sàng kết nối.
* **Ngoại lệ:** Bắt lỗi tạo socket không hợp lệ hoặc địa chỉ cấu hình sai.

#### MOD-1.1.4: Kết nối tới Server
* **Input:** Socket đã khởi tạo; IP và Port của Server.
* **Process:** Gọi `sock.connect((host, port))`. Ghi nhận thời điểm kết nối thành công; cập nhật trạng thái `Connected`.
* **Output:** Kết nối TCP được thiết lập; thông báo tới Tray UI.
* **Ngoại lệ:** Bắt `socket.error`, `ConnectionRefusedError`, chuyển sang trạng thái chờ reconnect.

---

### 2.2. Nhóm chuyển tải dữ liệu và duy trì kết nối
#### MOD-1.4.4: Gửi cấu trúc dữ liệu qua TCP Socket
* **Input:** Luồng byte JSON đã kèm ký tự phân cách newline `\n`.
* **Process:** Sử dụng `sock.sendall(data)` với cơ chế đồng bộ `threading.Lock`.
* **Output:** Dữ liệu được đưa vào luồng TCP tới Server; trả về `True`/`False`.
* **Ngoại lệ:** Bắt `BrokenPipeError`, `ConnectionResetError`, tự động đóng socket hỏng và kích hoạt cờ mất kết nối.

#### MOD-1.5.2: Gửi Heartbeat
* **Input:** `client_id`, chu kỳ `HEARTBEAT_INTERVAL_SEC` (5s), `agent_token`.
* **Process:** Định kỳ tạo message `{"type": "heartbeat", "data": {"client_id": ..., "sent_at": ...}}`, encode UTF-8 + `\n` và gửi qua socket.
* **Output:** Gói tin heartbeat gửi tới Server để duy trì trạng thái Online.
* **Ngoại lệ:** Bỏ qua nếu socket chưa kết nối; ghi log lỗi nếu encode thất bại.

#### MOD-1.5.3: Xử lý mất kết nối
* **Input:** Sự kiện ngắt kết nối (socket error, timeout, Server đóng kết nối).
* **Process:** Đánh dấu trạng thái `Disconnected`, đóng tài nguyên socket an toàn, thông báo tới giao diện Tray.
* **Output:** Socket được giải phóng; chuyển giao sang luồng Auto Reconnect.

#### MOD-1.5.4: Tự động Reconnect
* **Input:** Trạng thái `Disconnected`, `RECONNECT_INTERVAL_SEC` (5s).
* **Process:** Luồng nền lặp định kỳ thử `connect()` lại tới Server cho đến khi thành công hoặc người dùng thoát Agent.
* **Output:** Socket mới được thiết lập lại tự động mà không làm sập Agent.

---

### 2.3. Nhóm nhận và thực thi lệnh
#### MOD-1.6.1: Nhận Command từ Server
* **Input:** Byte stream từ socket TCP Server gửi xuống.
* **Process:** Đệm byte (`buffer`), tách từng message kết thúc bằng `\n`, giải mã UTF-8.
* **Output:** Chuỗi JSON thô của từng thông điệp.

#### MOD-1.6.2 & MOD-1.6.3: Phân tích & Xác định loại Command
* **Input:** Chuỗi JSON chứa `command_id`, `command_type`, `parameter`.
* **Process:** Đối chiếu với allowlist: `PING_TEST`, `GET_CONFIG`, `SHUTDOWN`, `RESTART`, `SCREEN`.
* **Output:** Định tuyến tới hàm xử lý tương ứng. Lệnh ngoài allowlist trả về trạng thái `FAILED`.

#### MOD-1.6.4 -> MOD-1.6.7: Thực thi và gửi Command Result
* **Input:** Loại lệnh và tham số thực thi.
* **Process:**
  * `PING_TEST`: Trả về `result_message="pong"`, `status="SUCCESS"`, `exit_code=0`.
  * `GET_CONFIG`: Thu thập thông tin cấu hình từ TV1, trả về chuỗi JSON cấu hình máy.
  * `SHUTDOWN` / `RESTART` / `SCREEN`: Thực hiện mô phỏng an toàn (Demo mode).
* **Output:** Tạo gói `command_result` theo protocol và gửi ngược về Server qua TCP.

---

### 2.4. Nhóm giao diện khay hệ thống (System Tray)
#### MOD-1.1.2 & MOD-1.2.1 -> MOD-1.2.5: Quản lý System Tray
* **Khởi tạo Icon (MOD-1.1.2):** Dùng `pystray` + `Pillow` tạo icon khay hệ thống (Màu xanh: Online, Màu đỏ: Offline).
* **Hiện/Ẩn thông tin (MOD-1.2.3):** Menu chuột phải xem thông tin máy tính (Hostname, IP, MAC, Client ID, Trạng thái).
* **Thử kết nối lại (MOD-1.2.2):** Cho phép người dùng bấm kết nối lại thủ công ngay lập tức.
* **Khóa máy (MOD-1.2.4):** Gọi hàm khóa màn hình Windows an toàn (`LockWorkStation`).
* **Thoát an toàn (MOD-1.2.5):** Dừng toàn bộ worker, đóng socket trước khi thoát chương trình.
