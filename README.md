# Nhom11_UngDungChatReal-Time

Ứng dụng chat real-time với giao diện web và desktop.

## Cài Đặt

1. Cài đặt Python 3.8+
2. Cài đặt dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Chạy Chương Trình

### Chạy Server
```bash
cd src/server
python main.py
```

### Chạy Client Desktop
```bash
cd src/client
python main.py
```

### Truy Cập Web Client
Mở file `docs/webclient.html` trong trình duyệt web.

## Đồng Bộ Lịch Sử Chat Giữa Các Máy

Vì database được lưu cục bộ (SQLite), lịch sử chat sẽ không tự động đồng bộ giữa các máy. Để chuyển lịch sử chat:

### Xuất Lịch Sử Từ Máy A
```bash
cd src/server
python export_import.py export chat_history.json
```

### Chuyển File `chat_history.json` Sang Máy B

### Nhập Lịch Sử Vào Máy B
```bash
cd src/server
python export_import.py import chat_history.json
```

**Lưu ý**: Chỉ import khi server đang tắt để tránh xung đột dữ liệu.

## Cấu Trúc Dự Án

- `src/server/`: Mã nguồn server
- `src/client/`: Mã nguồn client desktop
- `src/common/`: Mã dùng chung
- `docs/`: Tài liệu và web client
- `tests/`: Test cases

## Tính Năng

- Chat công khai và riêng tư
- Đăng ký/đăng nhập người dùng
- Lưu trữ lịch sử chat
- Giao diện web và desktop
- Hỗ trợ WebSocket