# Phân Chia Công Việc & Cấu Trúc Dự Án - Nhóm 11

## Cấu Trúc Thư Mục
```
/
├── docs/               # Tài liệu thiết kế (UML, Flowchart, Report)
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
│   │   └── gui.py      # Giao diện người dùng (Tkinter/PyQt)
│   └── common/         # Mã dùng chung
│       ├── __init__.py
│       ├── protocol.py # Định nghĩa giao thức (Message format, JSON parsing)
│       └── utils.py    # Các hàm tiện ích (Mã hóa, Config)
├── tests/              # Unit tests
├── requirements.txt    # Các thư viện cần thiết
└── README.md           # Hướng dẫn chạy
```

## Phân Chia Công Việc (4 Người) - Tập Trung Backend

### Người 1: Infrastructure & Concurrency Specialist
*   **Mô tả**: Chịu trách nhiệm về tầng hạ tầng mạng và xử lý song hành của Server. Đảm bảo hệ thống ổn định khi có nhiều kết nối đồng thời.
*   **Nhiệm vụ chi tiết**:
    - Thiết lập kiến trục Socket Server hỗ trợ song song TCP Raw và WebSocket (Handshake, Frame parsing).
    - Xử lý Đa luồng (Multi-threading/AsyncIO): Quản lý Thread Pool, tránh tình trạng Race Condition.
    - Quản lý trạng thái kết nối (Connection Lifecycle): Accept, Keep-alive (Heartbeat), Timeout, và Graceful Shutdown.
    - Tối ưu hóa hiệu suất tầng mạng và quản lý bộ nhớ đệm (Buffer management).
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

### Phú: Integrated Services & Client Logic
*   **Mô tả**: Phát triển các dịch vụ mở rộng của Backend và tích hợp vào giao diện người dùng.
*   **Nhiệm vụ chi tiết**:
    - File Transfer Service: Xử lý truyền nhận file qua Socket (Chunking, Binary stream, Resumable transfer).
    - Data Export/Import: Module sao lưu và phục hồi lịch sử trò chuyện (JSON/CSV).
    - Client Networking Integration: Gắn kết Logic mạng của Hùng vào giao diện.
    - Giao diện người dùng (GUI/Web): Phát triển UI tối giản, tập trung vào việc hiển thị chính xác các phản hồi từ Backend.
    - Logging & Monitoring: Hệ thống ghi nhật ký hoạt động của Server để hỗ trợ debug.
*   **Files phụ trách**: `src/server/export_import.py`, `src/client/gui.py`, `src/client/main.py`.
