# Hướng Dẫn Export/Import Lịch Sử Chat

## Vấn Đề
Khi chạy ứng dụng chat trên máy khác, bạn sẽ không thấy lịch sử chat cũ vì database SQLite được lưu cục bộ trên mỗi máy.

## Giải Pháp
Sử dụng tính năng export/import để chuyển lịch sử chat giữa các máy.

## Hướng Dẫn Chi Tiết

### 1. Xuất Lịch Sử Chat Từ Máy Nguồn

**Bước 1:** Mở terminal và chuyển đến thư mục server
```bash
cd src/server
```

**Bước 2:** Chạy lệnh export
```bash
python export_import.py export chat_history.json
```

**Kết quả mong đợi:**
```
✅ Đã xuất thành công 25 tin nhắn vào chat_history.json
```

**Bước 3:** Kiểm tra file được tạo
- File `chat_history.json` sẽ xuất hiện trong thư mục `src/server/`
- File chứa tất cả tin nhắn với định dạng JSON

### 2. Chuyển File Sang Máy Đích

**Cách 1: USB/Email**
- Copy file `chat_history.json` từ máy nguồn
- Chuyển sang máy đích và đặt vào thư mục `src/server/`

**Cách 2: Cloud Storage**
- Upload file lên Google Drive, Dropbox, etc.
- Download xuống máy đích vào thư mục `src/server/`

### 3. Nhập Lịch Sử Chat Vào Máy Đích

**Quan trọng:** Đảm bảo server đang tắt trước khi import!

**Bước 1:** Mở terminal trên máy đích
```bash
cd src/server
```

**Bước 2:** Chạy lệnh import
```bash
python export_import.py import chat_history.json
```

**Kết quả mong đợi:**
```
✅ Đã nhập thành công 25 tin nhắn từ chat_history.json
```

### 4. Kiểm Tra Kết Quả

**Chạy test database:**
```bash
python test_db.py
```

**Kết quả:** Sẽ hiển thị số lượng tin nhắn trong database, bao gồm cả tin nhắn đã import.

## Ví Dụ Thực Tế

### Máy A (Windows - có lịch sử)
```
D:\Project\ChatApp\src\server> python export_import.py export chat_history.json
✅ Đã xuất thành công 15 tin nhắn vào chat_history.json
```

### Máy B (Linux - mới)
```
user@linux:~/ChatApp/src/server$ python export_import.py import chat_history.json
✅ Đã nhập thành công 15 tin nhắn từ chat_history.json
```

## Lưu Ý Quan Trọng

### ⚠️ An Toàn
- **Tắt server** trước khi import để tránh xung đột dữ liệu
- File JSON chứa nội dung tin nhắn - **bảo mật khi chuyển file**
- Không chia sẻ file với người không đáng tin cậy

### 🔄 Import Lại
- Có thể import nhiều lần
- Tin nhắn trùng lặp sẽ bị bỏ qua (không ghi đè)
- ID tin nhắn được giữ nguyên từ máy nguồn

### 📁 Cấu Trúc File JSON
```json
[
  {
    "id": 1,
    "sender": "ngoc0801",
    "receiver": null,
    "content": "Xin chào mọi người!",
    "message_type": "public",
    "timestamp": "2026-01-07 10:30:00"
  },
  {
    "id": 2,
    "sender": "hungcv0704",
    "receiver": "ngoc0801",
    "content": "Chào Ngọc!",
    "message_type": "private",
    "timestamp": "2026-01-07 10:31:00"
  }
]
```

### 🐛 Xử Lý Lỗi
Nếu gặp lỗi, kiểm tra:
- File `chat_history.json` có tồn tại không?
- Server có đang chạy không? (phải tắt)
- Đường dẫn thư mục có đúng không?

## Câu Hỏi Thường Gặp

**Q: Tại sao không tự động đồng bộ?**
A: Ứng dụng sử dụng database SQLite cục bộ để đơn giản hóa. Để đồng bộ real-time cần database server (MySQL/PostgreSQL) và kết nối internet.

**Q: Có thể export một phần tin nhắn không?**
A: Hiện tại chỉ export tất cả. Có thể chỉnh sửa file JSON để xóa tin nhắn không muốn import.

**Q: File JSON có an toàn không?**
A: Chứa nội dung tin nhắn dạng plain text. Nên mã hóa file khi chuyển qua mạng không an toàn.

**Q: Dung lượng file lớn quá?**
A: SQLite rất nhẹ, nhưng nếu có nhiều tin nhắn, có thể chia nhỏ file JSON hoặc nén bằng ZIP.