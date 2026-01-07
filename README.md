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

### Bước 1: Xuất Lịch Sử Từ Máy A
```bash
cd src/server
python export_import.py export chat_history.json
```

**Kết quả**: File `chat_history.json` sẽ được tạo chứa tất cả tin nhắn.

### Bước 2: Chuyển File Sang Máy B
- Copy file `chat_history.json` từ máy A sang máy B
- Đặt file vào thư mục `src/server/` trên máy B

### Bước 3: Nhập Lịch Sử Vào Máy B
```bash
cd src/server
python export_import.py import chat_history.json
```

**Kết quả**: Tất cả tin nhắn sẽ được thêm vào database của máy B.

### Ví Dụ Chi Tiết

**Trên Máy A (có lịch sử chat):**
```bash
# Terminal trên máy A
D:\ChatMobile\Nhom11_UngDungChatReal-Time\src\server> python export_import.py export chat_history.json
✅ Đã xuất thành công 25 tin nhắn vào chat_history.json
```

**Chuyển file `chat_history.json` sang Máy B**

**Trên Máy B (mới, chưa có lịch sử):**
```bash
# Terminal trên máy B
D:\ChatMobile\Nhom11_UngDungChatReal-Time\src\server> python export_import.py import chat_history.json
✅ Đã nhập thành công 25 tin nhắn từ chat_history.json
```

### Lưu Ý Quan Trọng
- **Chỉ import khi server đang tắt** để tránh xung đột dữ liệu
- File JSON chứa thông tin nhạy cảm (nội dung tin nhắn), bảo mật khi chuyển file
- Import sử dụng `INSERT OR IGNORE`, không ghi đè tin nhắn đã tồn tại
- Có thể export/import nhiều lần, tin nhắn trùng lặp sẽ bị bỏ qua

### Kiểm Tra Sau Khi Import
Sau khi import, bạn có thể kiểm tra bằng cách chạy test:
```bash
python test_db.py
```
Sẽ hiển thị số lượng tin nhắn trong database.

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