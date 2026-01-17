# Phân Chia Công Việc & Cấu Trúc Dự Án - Nhóm 11

## Cấu Trúc Thư Mục
```
/
├── docs/               # Tài liệu thiết kế (UML, Flowchart, Report)
    index.html
├── src/
│   ├── server/         # Mã nguồn Server
│   │   ├── __init__.py
│   │   ├── main.py     # Entry point của Server
│   │   ├── server.py   # Class Server chính (Socket, Threading)
│   │   └── db.py       # Xử lý cơ sở dữ liệu (Lưu user, lịch sử chat)
│   ├── client/         # Mã nguồn Client
│   │   ├── __init__.py
│   │   ├── main.py     # Entry point của Client
│   │   ├── client.py   # Logic mạng của Client (Gửi/Nhận tin)
│   │   
│   └── common/         # Mã dùng chung
│       ├── __init__.py
│       ├── protocol.py # Định nghĩa giao thức (Message format, JSON parsing)
│       └── utils.py    # Các hàm tiện ích (Mã hóa, Config)
├── tests/              # Unit tests
├── requirements.txt    # Các thư viện cần thiết
└── README.md           # Hướng dẫn chạy
```

## Phân Chia Công Việc (4 Người) - Tập Trung Backend

### Người 1: Infrastructure & SocketIO Specialist
*   **Mô tả**: Chịu trách nhiệm về tầng hạ tầng mạng, quản lý kết nối đồng thời và tích hợp Flask-SocketIO cho server. Đảm bảo hệ thống ổn định khi có nhiều client kết nối.
*   **Nhiệm vụ chi tiết**:
    - Thiết lập và tối ưu hóa server Flask-SocketIO (quản lý event, broadcast, phòng chat, file transfer, trạng thái kết nối).
    - Quản lý kết nối client, lifecycle (connect/disconnect), keep-alive, timeout, shutdown qua event của SocketIO..
    - Tối ưu hiệu suất tầng mạng, quản lý bộ nhớ đệm, xử lý file upload/download qua SocketIO.
*   **Files phụ trách**: `src/server/server.py`, `src/server/websocket_handler.py`, `src/server/main.py`.

### Hùng: Protocol Architect & Message Orchestrator
*   **Mô tả**: Thiết kế "ngôn ngữ chung" của hệ thống và điều phối luồng dữ liệu giữa các Client.
*   **Nhiệm vụ chi tiết**:
    - Thiết kế Giao thức truyền tin (Protocol Design): Định nghĩa cấu trúc gói tin JSON (Header, Payload, Checksum).
    - Tầng Serialization/Deserialization: Chuyển đổi dữ liệu và kiểm tra tính toàn vẹn (Validation).
    - Logic điều hướng tin nhắn (Message Orchestration): Xử lý Message Routing cho Chat đơn, Chat nhóm, và Broadcast.
    - Xử lý các trạng thái nghiệp vụ (State Machine): Online, Offline, Away, Typing.
*   **Files phụ trách**: `src/common/protocol.py`, `src/client/client.py`.

### Ngọc: Data Architect & Security Engineer
*   **Mô tả**: Quản lý tính bền vững của dữ liệu và đảm bảo an toàn thông tin cho toàn hệ thống.
*   **Nhiệm vụ chi tiết**:
    - Thiết kế Cơ sở dữ liệu (Database Schema): SQLite/PostgreSQL, quản lý quan hệ User-Friend-Group.
    - Tầng Data Access (DAO): Viết các truy vấn tối ưu, quản lý Transaction và Connection Pooling.
    - Authentication & Authorization: Xử lý Đăng ký/Đăng nhập, Mã hóa mật khẩu (BCrypt), quản lý Session/Token.
    - Security Features: Thực hiện mã hóa tin nhắn (AES/RSA) và chống các lỗi bảo vệ cơ bản (SQL Injection, XSS).
*   **Files phụ trách**: `src/server/db.py`, `src/common/utils.py`.

### Phú: Integrated Services & Web Client
*   **Mô tả**: Phát triển các dịch vụ mở rộng của Backend và hỗ trợ giao diện web.
*   **Nhiệm vụ chi tiết**:
    - File Transfer Service: Xử lý truyền nhận file qua Socket (Chunking, Binary stream, Resumable transfer).
    - Data Export/Import: Module sao lưu và phục hồi lịch sử trò chuyện (JSON/CSV).
    - Client Networking Integration: Gắn kết Logic mạng của Hùng vào giao diện web (webclient.html hoặc frontend khác).
    - Hỗ trợ phát triển giao diện web (nếu có), tập trung vào việc hiển thị chính xác các phản hồi từ Backend.
    - Logging & Monitoring: Hệ thống ghi nhật ký hoạt động của Server để hỗ trợ debug.
*   **Files phụ trách**: `src/server/export_import.py`, `src/client/main.py`, `docs/index.html`
