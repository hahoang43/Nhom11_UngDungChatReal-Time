# Database SQLite - Hướng Dẫn Sử Dụng

## Tổng Quan

Database SQLite được thiết lập để lưu trữ:
- **Thông tin người dùng (Users)**: username, password (đã mã hóa), thời gian tạo, lần đăng nhập cuối
- **Lịch sử chat (Messages)**: tin nhắn công khai và tin nhắn riêng

## Cấu Trúc Database

### Bảng `users`
- `username` (TEXT, PRIMARY KEY): Tên người dùng
- `password_hash` (TEXT, NOT NULL): Mật khẩu đã được mã hóa SHA-256
- `created_at` (DATETIME): Thời gian tạo tài khoản
- `last_login` (DATETIME): Thời gian đăng nhập cuối cùng
- `is_active` (INTEGER): Trạng thái tài khoản (1 = active, 0 = inactive)

### Bảng `messages`
- `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT): ID tin nhắn
- `sender` (TEXT, NOT NULL): Người gửi (Foreign Key → users.username)
- `receiver` (TEXT): Người nhận (NULL cho tin nhắn công khai, Foreign Key → users.username)
- `content` (TEXT, NOT NULL): Nội dung tin nhắn
- `message_type` (TEXT): Loại tin nhắn ('public' hoặc 'private')
- `timestamp` (DATETIME): Thời gian gửi tin nhắn

### Indexes
- `idx_messages_timestamp`: Index trên timestamp để tăng tốc truy vấn lịch sử
- `idx_messages_sender`: Index trên sender
- `idx_messages_receiver`: Index trên receiver
- `idx_messages_type`: Index trên message_type

## Các Chức Năng Chính

### 1. Quản Lý Người Dùng

#### `register_user(username, password)`
Đăng ký người dùng mới. Mật khẩu sẽ được mã hóa tự động.
```python
db = Database()
success = db.register_user("john", "password123")
```

#### `login_user(username, password)`
Xác thực đăng nhập. Tự động cập nhật `last_login`.
```python
if db.login_user("john", "password123"):
    print("Đăng nhập thành công!")
```

#### `user_exists(username)`
Kiểm tra username đã tồn tại chưa.
```python
if db.user_exists("john"):
    print("User đã tồn tại")
```

#### `get_user_info(username)`
Lấy thông tin chi tiết của user.
```python
user_info = db.get_user_info("john")
# Returns: {'username': 'john', 'created_at': '...', 'last_login': '...', 'is_active': True}
```

#### `get_all_users(active_only=True)`
Lấy danh sách tất cả users.
```python
users = db.get_all_users()
```

#### `deactivate_user(username)`
Vô hiệu hóa tài khoản.
```python
db.deactivate_user("john")
```

### 2. Quản Lý Tin Nhắn

#### `save_message(sender, content, receiver=None, message_type='public')`
Lưu tin nhắn vào database.
```python
# Tin nhắn công khai
db.save_message("john", "Hello everyone!", message_type='public')

# Tin nhắn riêng
db.save_message("john", "Hello!", receiver="jane", message_type='private')
```

#### `get_history(limit=50, message_type='public', username=None)`
Lấy lịch sử tin nhắn.
```python
# Lấy 20 tin nhắn công khai gần nhất
history = db.get_history(limit=20, message_type='public')

# Lấy tin nhắn của một user cụ thể (cả public và private)
history = db.get_history(limit=50, username="john")
```

#### `get_message_count(username=None)`
Đếm số lượng tin nhắn.
```python
total = db.get_message_count()
user_messages = db.get_message_count("john")
```

## Bảo Mật

- Mật khẩu được mã hóa bằng **SHA-256** trước khi lưu vào database
- Sử dụng **parameterized queries** để tránh SQL injection
- Foreign keys được bật để đảm bảo tính toàn vẹn dữ liệu

## Migration

Database tự động migrate từ schema cũ sang schema mới:
- Nếu database cũ có cột `password`, sẽ tự động chuyển sang `password_hash`
- Thêm các cột mới (`created_at`, `last_login`, `is_active`) nếu chưa có
- Thêm các cột mới cho messages (`receiver`, `message_type`) nếu chưa có

## Test Database

Chạy script test để kiểm tra các chức năng:
```bash
python src/server/test_db.py
```

## Lưu Ý

1. Database file được lưu tại: `src/server/chat.db`
2. Database hỗ trợ multi-threading (check_same_thread=False)
3. Luôn đóng database khi không sử dụng: `db.close()`
4. Có thể sử dụng context manager:
   ```python
   with Database() as db:
       db.register_user("john", "password")
   ```

