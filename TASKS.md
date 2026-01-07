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

## Phân Chia Công Việc (4 Người)

### Người 1: Server Core & Architecture (Trưởng nhóm kỹ thuật)
*   **Nhiệm vụ**:
    *   Thiết lập kiến trúc Socket Server (TCP/IP).
    *   ích hợp WebSocket để hỗ trợ kết nối từ Web Browser.
    *   Quản lý danh sách kết nối Client (Accept, Disconnect).
    *   Xử lý đa luồng (Threading) để phục vụ nhiều Client cùng lúc.
    *   Thực hiện chức năng Broadcast (Gửi tin nhắn cho tất cả).
*   **Files phụ trách**: `src/server/main.py`, `src/server/server.py`, `src/server/websocket_handler.py`.

### Hùng: Protocol Design & Client Networking
*   **Nhiệm vụ**:
    *   Thiết kế giao diện Websocket
    *   Thiết kế giao thức giao tiếp (Protocol): Định dạng tin nhắn (JSON), các loại tin (LOGIN, MESSAGE, PRIVATE, LOGOUT).
    *   Xử lý đóng gói và giải mã dữ liệu (Serialization/Deserialization).
    *   Viết logic mạng cho Client (Kết nối đến Server, lắng nghe tin nhắn đến).
    *   **Mới**: Nghiên cứu WebSocket Protocol (Handshake, Frame) để hỗ trợ Người 1.
*   **Files phụ trách**: `src/common/protocol.py`, `src/client/client.py`.

### Phú: User Interface (GUI)
*   **Nhiệm vụ**:
        Tạo giao diện web
    *   Thiết kế giao diện người dùng (Login form, Chat room, User list).
    *   Tích hợp logic mạng của Người 2 vào giao diện (Binding events).
    *   Hiển thị tin nhắn thời gian thực lên màn hình.
*   **Files phụ trách**: `src/client/gui.py`, `src/client/main.py`.

### Ngọc: Database & Advanced Features
*   **Nhiệm vụ**:
    *   Thiết lập Database (SQLite/MySQL) để lưu thông tin User và Lịch sử chat.
    *   Thực hiện chức năng Đăng ký/Đăng nhập (Authentication).
    *   (Nâng cao) Mã hóa tin nhắn (SSL/TLS hoặc AES) hoặc Truyền file.
*   **Files phụ trách**: `src/server/db.py`, `src/common/utils.py`.
