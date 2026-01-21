# Nhom11_UngDungChatReal-Time

Ứng dụng chat real-time với giao diện web, hỗ trợ nhắn tin riêng, nhóm, gửi file, và hệ thống bạn bè.

## 1. Cài Đặt

Yêu cầu: Python 3.8+

Cài đặt các thư viện cần thiết:
```bash
python -m pip install -r requirements.txt
```

Nếu muốn chạy test tự động, cài thêm:
```bash
python -m pip install requests
```

## 2. Chạy Server

Server sẽ chạy mặc định tại cổng `8000`.

```bash
# Từ thư mục gốc của dự án
python src/server/main.py
```

Khi chạy thành công, bạn sẽ thấy thông báo:
> Running on http://0.0.0.0:8000

## 3. Chạy Client

### Option A: Giao diện Web (Khuyên dùng)
Mở file `index.html` (nằm ở thư mục gốc) bằng trình duyệt web bất kỳ.

> **Lưu ý**: Có thể mở nhiều tab để chat với nhau.

### Option B: Giao diện Desktop (Python/Tkinter)
Nếu bạn muốn chạy ứng dụng desktop:
```bash
# Từ thư mục gốc
python src/client/main.py
```
*Lưu ý: Giao diện desktop có thể chưa cập nhật đầy đủ các tính năng mới (như Friend System) so với bản Web.*

## 4. Tính Năng Chính

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

## 5. Chạy Kiểm Thử (Testing)

Để kiểm tra tự động luồng kết bạn (Friend Flow):

1. Đảm bảo server đang chạy tại port 8000.
2. Chạy script test:
```bash
python tests/verify_friend_flow.py
```
Script sẽ tự động tạo 2 user (`alice_test`, `bob_test`) và mô phỏng quá trình kết bạn, chat để xác minh hệ thống hoạt động đúng.

## 6. Cấu Trúc Dự Án

- `src/server/`: Mã nguồn server (Python/Flask-SocketIO).
- `src/common/`: Các định nghĩa dùng chung (Message Protocol).
- `index.html`: Giao diện chính của Web Client.
- `requirements.txt`: Danh sách thư viện phụ thuộc.
- `tests/`: Các script kiểm thử tự động.