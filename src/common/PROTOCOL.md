# Giao Thức Giao Tiếp (Communication Protocol)

## Tổng Quan

Giao thức sử dụng JSON format với header cố định 10 bytes để chỉ định độ dài message. Tất cả messages được gửi qua TCP socket hoặc WebSocket.

**Version**: 1.0  
**Port mặc định**: 5555  
**Encoding**: UTF-8

## Định Dạng Message

### Cấu Trúc Chung

```json
{
    "type": "MESSAGE_TYPE",
    "payload": {...},
    "encrypted": false
}
```

### Header Format

- **Header Length**: 10 bytes (padded với spaces)
- **Encoding**: UTF-8
- **Format**: `{length:<10}`

Ví dụ: Message có độ dài 150 bytes → Header: `"150       "`

## Các Loại Message

### 1. LOGIN - Đăng Nhập

**Client → Server:**
```json
{
    "type": "LOGIN",
    "payload": {
        "username": "john",
        "password": "password123"
    }
}
```

**Server → Client (Success):**
```json
{
    "type": "LOGIN_SUCCESS",
    "payload": "Welcome john!"
}
```

**Server → Client (Error):**
```json
{
    "type": "ERROR",
    "payload": "Invalid username or password"
}
```

### 2. REGISTER - Đăng Ký

**Client → Server:**
```json
{
    "type": "REGISTER",
    "payload": {
        "username": "john",
        "password": "password123"
    }
}
```

**Server → Client (Success):**
```json
{
    "type": "LOGIN_SUCCESS",
    "payload": "Welcome john!"
}
```

**Server → Client (Error):**
```json
{
    "type": "ERROR",
    "payload": "Username already exists"
}
```

### 3. TEXT - Tin Nhắn Công Khai

**Client → Server:**
```json
{
    "type": "TEXT",
    "payload": "Hello everyone!",
    "encrypted": true
}
```

**Lưu ý**: 
- Nếu `encrypted: true`, payload là ciphertext đã được mã hóa AES-256-CBC và encode base64
- Nếu `encrypted: false`, payload là plaintext

**Server → Client (Broadcast):**
```json
{
    "type": "TEXT",
    "payload": "john: Hello everyone!",
    "encrypted": true
}
```

**Server xử lý**:
1. Nhận tin nhắn từ client (có thể đã mã hóa)
2. Giải mã nếu cần
3. Lưu plaintext vào database
4. Mã hóa lại với key của từng client khi broadcast

### 4. PRIVATE - Tin Nhắn Riêng Tư

**Client → Server:**
```json
{
    "type": "PRIVATE",
    "payload": {
        "receiver": "jane",
        "content": "Hello, this is a private message"
    },
    "encrypted": true
}
```

**Lưu ý**: 
- `content` có thể là plaintext hoặc ciphertext (nếu `encrypted: true`)
- Server sẽ giải mã, lưu vào DB với `message_type='private'`, sau đó mã hóa lại cho receiver

**Server → Receiver:**
```json
{
    "type": "PRIVATE",
    "payload": {
        "sender": "john",
        "content": "Hello, this is a private message"
    },
    "encrypted": true
}
```

**Server → Sender (Confirmation - Optional):**
```json
{
    "type": "PRIVATE",
    "payload": {
        "receiver": "jane",
        "content": "Hello, this is a private message",
        "status": "sent"
    },
    "encrypted": false
}
```

**Xử lý lỗi**:
- Nếu receiver không tồn tại hoặc offline → Server gửi ERROR message
- Nếu receiver không online → Lưu vào DB, gửi khi receiver đăng nhập

### 5. EXIT/LOGOUT - Thoát/Logout

**Client → Server:**
```json
{
    "type": "EXIT",
    "payload": ""
}
```

**Server xử lý**:
1. Xóa client khỏi danh sách kết nối
2. Broadcast thông báo: `"Server: {username} has left the chat."`
3. Đóng kết nối socket
4. Giải phóng tài nguyên (encryption keys, file transfers)

**Lưu ý**: Client nên gửi EXIT message trước khi đóng socket để server có thể cleanup đúng cách.

### 6. FILE_REQUEST - Yêu Cầu Gửi File

**Client → Server:**
```json
{
    "type": "FILE_REQUEST",
    "payload": {
        "filename": "document.pdf",
        "filesize": 1024000,
        "receiver": null  // null = public, "username" = private
    }
}
```

### 7. FILE_CHUNK - Chunk của File

**Client → Server:**
```json
{
    "type": "FILE_CHUNK",
    "payload": {
        "chunk_num": 0,
        "data": "base64_encoded_chunk_data"
    }
}
```

### 8. FILE_END - Kết Thúc Gửi File

**Client → Server:**
```json
{
    "type": "FILE_END",
    "payload": {
        "filename": "document.pdf"
    }
}
```

**Server → All Clients:**
```json
{
    "type": "FILE",
    "payload": {
        "sender": "john",
        "filename": "document.pdf",
        "filesize": 1024000,
        "filepath": "server/path/to/file",
        "message": "john đã gửi file: document.pdf"
    }
}
```

### 9. USER_LIST - Danh Sách User Online

**Client → Server:**
```json
{
    "type": "USER_LIST",
    "payload": ""
}
```

**Server → Client:**
```json
{
    "type": "USER_LIST",
    "payload": {
        "users": ["john", "jane", "bob"]
    }
}
```

### 10. ERROR - Thông Báo Lỗi

**Server → Client:**
```json
{
    "type": "ERROR",
    "payload": "Error message here"
}
```

## Mã Hóa (Encryption)

### Thông Số Kỹ Thuật

- **Algorithm**: AES-256-CBC
- **Key derivation**: PBKDF2 với SHA-256
- **Iterations**: 100,000
- **Key length**: 32 bytes (256 bits)
- **IV**: Random 16 bytes cho mỗi message
- **Block size**: 16 bytes
- **Padding**: PKCS7
- **Format**: Base64 encoded

### Cơ Chế Mã Hóa

1. **Key Generation**: 
   - Key được tạo từ password của user bằng PBKDF2
   - Mỗi user có key riêng, không chia sẻ key giữa các users

2. **Encryption Flow**:
   ```
   Plaintext → AES-256-CBC Encrypt (với IV ngẫu nhiên) → Base64 Encode → Ciphertext
   ```

3. **Decryption Flow**:
   ```
   Ciphertext → Base64 Decode → AES-256-CBC Decrypt → Plaintext
   ```

4. **Server Behavior**:
   - Server giải mã tin nhắn từ client để lưu plaintext vào database
   - Server mã hóa lại tin nhắn với key của từng client khi broadcast
   - Mỗi client chỉ có thể giải mã tin nhắn của chính mình

### Ví Dụ

**Plaintext**: `"Hello World"`  
**Encrypted (base64)**: `"U2FsdGVkX1+..."`  
**Message**:
```json
{
    "type": "TEXT",
    "payload": "U2FsdGVkX1+...",
    "encrypted": true
}
```

## Luồng Giao Tiếp (Communication Flow)

### 1. Kết Nối và Đăng Nhập

```
Client                    Server
  |                         |
  |---- LOGIN ------------>|
  |   {username, password}  | (Validate credentials)
  |                         | (Create encryption key)
  |<--- LOGIN_SUCCESS -----|
  |   "Welcome username!"   |
  |                         |
  |<--- TEXT (history) -----| (Send last 20 messages)
  |<--- TEXT (history) -----|
  |<--- TEXT (history) -----|
  |                         |
  |<--- TEXT (broadcast) ---| "Server: username joined"
```

### 1.1. Đăng Ký

```
Client                    Server
  |                         |
  |---- REGISTER ---------->|
  |   {username, password}  | (Check if exists)
  |                         | (Create user, hash password)
  |<--- LOGIN_SUCCESS -----| (Auto-login after register)
  |   "Welcome username!"   |
```

**Lưu ý**: Sau khi đăng ký thành công, server tự động đăng nhập user.

### 2. Gửi Tin Nhắn Công Khai

```
Client A                  Server                    Client B, C, ...
  |                         |                            |
  |---- TEXT (encrypted) ->|                            |
  |   "Hello"              | (Decrypt with A's key)    |
  |                         | (Save plaintext to DB)    |
  |                         | (Encrypt with B's key)    |
  |                         |---- TEXT (encrypted) ----->|
  |                         |   "A: Hello"              |
  |                         | (Encrypt with C's key)    |
  |                         |---- TEXT (encrypted) ----->|
  |                         |   "A: Hello"              |
```

**Đặc điểm**:
- Mỗi client nhận tin nhắn đã được mã hóa với key riêng của mình
- Server lưu plaintext vào database
- Tất cả clients online đều nhận được tin nhắn

### 3. Gửi Tin Nhắn Riêng (Private Message)

```
Sender                     Server                    Receiver
  |                         |                            |
  |---- PRIVATE ----------->|                            |
  |   {receiver, content}   | (Check receiver exists)    |
  |                         | (Check receiver online)     |
  |                         | (Decrypt, save to DB)      |
  |                         |   message_type='private'   |
  |                         | (Encrypt with receiver key)|
  |                         |---- PRIVATE --------------->|
  |                         |   {sender, content}        |
  |<--- PRIVATE (confirm) --|                            |
  |   {status: "sent"}      |                            |
```

**Xử lý trường hợp đặc biệt**:
- **Receiver offline**: Lưu vào DB, gửi khi receiver đăng nhập
- **Receiver không tồn tại**: Gửi ERROR message về sender
- **Receiver = Sender**: Có thể cho phép hoặc từ chối (tùy implementation)

### 4. Gửi File

```
Sender                     Server                    All Clients
  |                         |                            |
  |---- FILE_REQUEST ------>|                            |
  |   {filename, filesize}  |                            |
  |                         |                            |
  |---- FILE_CHUNK -------->|                            |
  |   {chunk_num, data}     |                            |
  |---- FILE_CHUNK -------->|                            |
  |   {chunk_num, data}     |                            |
  |---- FILE_CHUNK -------->|                            |
  |   ...                   |                            |
  |---- FILE_END ---------->|                            |
  |   {filename}            | (Save file to disk)        |
  |                         | (Save file info to DB)     |
  |                         | (Broadcast file info)      |
  |<--- FILE --------------|                            |
  |   {sender, filename,    |<--- FILE ------------------|
  |    filesize, filepath}  |   {sender, filename,       |
  |                         |    filesize, filepath}     |
```

**Chi tiết**:
- **Chunk size**: 8KB (8192 bytes) mặc định
- **Chunk encoding**: Base64
- **File storage**: Server lưu tại `src/server/received_files/`
- **File naming**: `{timestamp}_{original_filename}` để tránh trùng
- **Database**: Lưu message `"📎 File: {filename} ({size})"` với `message_type='public'`
- **Broadcast**: Gửi file info đến tất cả clients (kể cả sender)

## Xử Lý Lỗi (Error Handling)

### 1. Connection Errors

**Lỗi kết nối**:
- Client nên thử reconnect với exponential backoff
- Hiển thị thông báo "Đang kết nối lại..." trong UI
- Lưu tin nhắn chưa gửi để retry sau

**Timeout**:
- Socket timeout: 30 giây mặc định
- File transfer timeout: 60 giây

### 2. Message Errors

**Decryption Error**:
```json
{
    "type": "TEXT",
    "payload": "[Lỗi giải mã tin nhắn]",
    "encrypted": false
}
```

**Invalid Message Format**:
```json
{
    "type": "ERROR",
    "payload": "Invalid message format"
}
```

**Missing Fields**:
```json
{
    "type": "ERROR",
    "payload": "Missing required field: username"
}
```

### 3. Authentication Errors

**Invalid Credentials**:
```json
{
    "type": "ERROR",
    "payload": "Invalid username or password"
}
```

**Username Already Exists**:
```json
{
    "type": "ERROR",
    "payload": "Username already exists"
}
```

**User Not Found** (cho PRIVATE message):
```json
{
    "type": "ERROR",
    "payload": "User 'jane' not found or offline"
}
```

### 4. File Transfer Errors

**File Too Large**:
- Client nên cảnh báo nếu file > 10MB
- Server có thể giới hạn kích thước file

**File Transfer Failed**:
- Client hiển thị "✗ Gửi thất bại"
- Server cleanup file chunks nếu transfer không hoàn tất

### 5. Best Practices

1. **Luôn kiểm tra message type** trước khi xử lý
2. **Validate payload** trước khi sử dụng
3. **Xử lý encryption/decryption** với try-except
4. **Timeout handling** cho các operations dài
5. **Error handling** cho tất cả network operations
6. **Logging** các lỗi để debug

## Bảng Tóm Tắt Message Types

| Type | Hướng | Mô Tả | Payload |
|------|-------|-------|---------|
| `LOGIN` | C→S | Đăng nhập | `{username, password}` |
| `REGISTER` | C→S | Đăng ký | `{username, password}` |
| `LOGIN_SUCCESS` | S→C | Đăng nhập thành công | `string` |
| `TEXT` | C↔S | Tin nhắn công khai | `string` (có thể encrypted) |
| `PRIVATE` | C↔S | Tin nhắn riêng | `{sender/receiver, content}` |
| `EXIT` | C→S | Thoát/Logout | `""` |
| `FILE_REQUEST` | C→S | Yêu cầu gửi file | `{filename, filesize, receiver}` |
| `FILE_CHUNK` | C→S | Chunk của file | `{chunk_num, data}` |
| `FILE_END` | C→S | Kết thúc gửi file | `{filename}` |
| `FILE` | S→C | Thông tin file đã gửi | `{sender, filename, filesize, filepath}` |
| `USER_LIST` | C↔S | Danh sách user online | `{users: [...]}` |
| `ERROR` | S→C | Thông báo lỗi | `string` |

**Ký hiệu**:
- `C→S`: Client gửi đến Server
- `S→C`: Server gửi đến Client
- `C↔S`: Hai chiều

## Ví Dụ Thực Tế

### Ví dụ 1: Đăng nhập và gửi tin nhắn

```python
# 1. Client gửi LOGIN
{
    "type": "LOGIN",
    "payload": {
        "username": "alice",
        "password": "secret123"
    }
}

# 2. Server trả về LOGIN_SUCCESS
{
    "type": "LOGIN_SUCCESS",
    "payload": "Welcome alice!"
}

# 3. Server gửi lịch sử chat
{
    "type": "TEXT",
    "payload": "[2024-01-01 10:00:00] bob: Hello!",
    "encrypted": false
}

# 4. Client gửi tin nhắn mới
{
    "type": "TEXT",
    "payload": "U2FsdGVkX1+vupppZksvRf5pq5g5XkFy...",  # "Hi everyone!" encrypted
    "encrypted": true
}

# 5. Server broadcast đến các clients khác
{
    "type": "TEXT",
    "payload": "U2FsdGVkX1+xyz...",  # "alice: Hi everyone!" encrypted với key của mỗi client
    "encrypted": true
}
```

### Ví dụ 2: Gửi file

```python
# 1. Client gửi FILE_REQUEST
{
    "type": "FILE_REQUEST",
    "payload": {
        "filename": "document.pdf",
        "filesize": 245760,
        "receiver": null
    }
}

# 2. Client gửi các chunks
{
    "type": "FILE_CHUNK",
    "payload": {
        "chunk_num": 0,
        "data": "JVBERi0xLjQKJeLjz9MKMy..."
    }
}
# ... (30 chunks cho file 240KB)

# 3. Client gửi FILE_END
{
    "type": "FILE_END",
    "payload": {
        "filename": "document.pdf"
    }
}

# 4. Server broadcast FILE info
{
    "type": "FILE",
    "payload": {
        "sender": "alice",
        "filename": "document.pdf",
        "filesize": 245760,
        "filepath": "src/server/received_files/20240101_100000_document.pdf",
        "message": "alice đã gửi file: document.pdf"
    }
}
```

## Tài Liệu Tham Khảo

- **AES Encryption**: [NIST FIPS 197](https://csrc.nist.gov/publications/detail/fips/197/final)
- **PBKDF2**: [RFC 2898](https://tools.ietf.org/html/rfc2898)
- **WebSocket Protocol**: [RFC 6455](https://tools.ietf.org/html/rfc6455)
- **JSON Format**: [JSON.org](https://www.json.org/)

