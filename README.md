# Nhom11_UngDungChatReal-Time

Ứng dụng chat real-time hỗ trợ giao tiếp tức thời giữa nhiều người dùng, chạy được trên web (HTML/JS demo). Hệ thống sử dụng Socket.IO/WebSocket, hỗ trợ chat công khai, riêng tư, truyền file, quản lý nhóm, đồng bộ lịch sử chat qua export/import.

---

## 1. Tổng Quan
- **Ngôn ngữ:** Python 3.8+, HTML/JS (web demo)
- **Backend:** Flask, Flask-SocketIO, Eventlet
- **Database:** SQLite (mặc định), hỗ trợ PostgreSQL
- **Giao tiếp:** Socket.IO/WebSocket, JSON

## 2. Cài Đặt

```bash
pip install -r requirements.txt
```
Yêu cầu Python >= 3.8

## 3. Hướng Dẫn Chạy

### Chạy Server 
```bash
cd src/server
python main.py
```

### Chạy Web Client (demo)
Mở file `index.html` trong trình duyệt web.


> **Lưu ý**: Có thể mở nhiều tab để chat với nhau.



## 3. Tính Năng Chính

- **Hệ thống Bạn Bè**:
    - Gửi lời mời kết bạn (Tab "Khám phá").
    - Chấp nhận lời mời (Tab "Khám phá" hoặc sidebar).
    - Hiển thị trạng thái Online/Offline của bạn bè.
- **Chat**:
    - Chat riêng tư (chỉ với bạn bè).
    - Chat nhóm.
    - Gửi file đính kèm.
    - Emoji picker.
    - Thông báo tin nhắn chưa đọc.
