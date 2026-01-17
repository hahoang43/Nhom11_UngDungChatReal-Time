import sqlite3
import os
import hashlib
from datetime import datetime
from contextlib import contextmanager
import json

DB_PATH = os.path.join(os.path.dirname(__file__), 'chat.db')

class Database:
    def __init__(self):
        """Khởi tạo kết nối database và tạo các bảng nếu chưa tồn tại"""
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries for easier access
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        """Tạo các bảng trong database: users và messages"""
        cursor = self.conn.cursor()
        
        # Kiểm tra và migrate từ schema cũ nếu cần
        self._migrate_schema(cursor)
        
        # Bảng users: Lưu thông tin người dùng
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Bảng messages: Lưu lịch sử chat
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                receiver TEXT,
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'public',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender) REFERENCES users(username)
            )
        ''')
        
        # Bảng groups: Lưu thông tin nhóm chat
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                creator TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator) REFERENCES users(username)
            )
        ''')

        # Bảng group_members: Lưu thành viên của nhóm
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                group_id INTEGER,
                username TEXT,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, username),
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            )
        ''');

        # Tạo indexes để tăng hiệu suất truy vấn
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
            ON messages(timestamp DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_sender 
            ON messages(sender)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_receiver 
            ON messages(receiver)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_type 
            ON messages(message_type)
        ''')
        
        self.conn.commit()

    def _migrate_schema(self, cursor):
        """Migrate từ schema cũ sang schema mới nếu cần"""
        try:
            # Kiểm tra xem bảng users có tồn tại không
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if cursor.fetchone():
                # Bảng tồn tại, kiểm tra schema
                cursor.execute("PRAGMA table_info(users)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Kiểm tra và thêm các cột còn thiếu
                needs_migration = False
                missing_columns = []
                
                required_columns = ['password_hash', 'created_at', 'last_login', 'is_active']
                for col in required_columns:
                    if col not in columns:
                        missing_columns.append(col)
                        needs_migration = True
                
                # Kiểm tra nếu có cột password cũ cần migrate
                has_old_password = 'password' in columns and 'password_hash' not in columns
                
                if needs_migration or has_old_password:
                    print("[DB] Migrating users table...")
                    try:
                        # Thêm các cột còn thiếu
                        if 'password_hash' not in columns:
                            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
                        
                        if 'created_at' not in columns:
                            cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME")
                            from datetime import datetime
                            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            cursor.execute("UPDATE users SET created_at = ? WHERE created_at IS NULL", (current_time,))
                        
                        if 'last_login' not in columns:
                            cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
                        
                        if 'is_active' not in columns:
                            cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
                            cursor.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
                        
                        # Migrate password cũ sang password_hash nếu có
                        if has_old_password:
                            cursor.execute("SELECT username, password FROM users WHERE password IS NOT NULL AND (password_hash IS NULL OR password_hash = '')")
                            users = cursor.fetchall()
                            for username, password in users:
                                password_hash = self._hash_password(password)
                                cursor.execute(
                                    "UPDATE users SET password_hash = ? WHERE username = ?",
                                    (password_hash, username)
                                )
                        
                        # Đảm bảo password_hash không null cho các user mới
                        cursor.execute("UPDATE users SET password_hash = ? WHERE password_hash IS NULL OR password_hash = ''", 
                                     (self._hash_password('default'),))
                        
                        print("[DB] Users table migration completed!")
                    except sqlite3.OperationalError as e:
                        print(f"[DB] Migration error: {e}")
                        # Nếu migration thất bại, thử tạo lại bảng
                        try:
                            self._recreate_users_table(cursor)
                        except Exception as e2:
                            print(f"[DB] Failed to recreate table: {e2}")
            
            # Kiểm tra bảng messages
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(messages)")
                msg_columns = [row[1] for row in cursor.fetchall()]
                
                if 'receiver' not in msg_columns:
                    print("[DB] Migrating messages table...")
                    try:
                        # Thêm các cột mới cho messages
                        cursor.execute("ALTER TABLE messages ADD COLUMN receiver TEXT")
                        cursor.execute("ALTER TABLE messages ADD COLUMN message_type TEXT DEFAULT 'public'")
                        # Cập nhật các tin nhắn cũ thành public
                        cursor.execute("UPDATE messages SET message_type = 'public' WHERE message_type IS NULL")
                        print("[DB] Messages table migration completed!")
                    except sqlite3.OperationalError as e:
                        print(f"[DB] Migration warning: {e}")
                
        except sqlite3.OperationalError as e:
            # Bảng chưa tồn tại hoặc lỗi khác, không cần migrate
            pass

    def _recreate_users_table(self, cursor):
        """Tạo lại bảng users với schema mới (dùng khi migration thất bại)"""
        try:
            print("[DB] Recreating users table...")
            # Lưu dữ liệu cũ
            cursor.execute("SELECT username, password FROM users")
            old_users = cursor.fetchall()
            
            # Tạo bảng mới
            cursor.execute("DROP TABLE users")
            cursor.execute('''
                CREATE TABLE users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            # Khôi phục dữ liệu với password_hash
            from datetime import datetime
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for username, password in old_users:
                password_hash = self._hash_password(password)
                cursor.execute(
                    "INSERT INTO users (username, password_hash, created_at, is_active) VALUES (?, ?, ?, ?)",
                    (username, password_hash, current_time, 1)
                )
            print("[DB] Users table recreated successfully!")
        except Exception as e:
            print(f"[DB] Error recreating users table: {e}")

    def _hash_password(self, password):
        """Mã hóa mật khẩu bằng SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        """
        Đăng ký người dùng mới
        
        Args:
            username: Tên người dùng
            password: Mật khẩu (sẽ được mã hóa)
            
        Returns:
            True nếu đăng ký thành công, False nếu username đã tồn tại
        """
        cursor = self.conn.cursor()
        try:
            password_hash = self._hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login_user(self, username, password):
        """
        Xác thực đăng nhập người dùng
        
        Args:
            username: Tên người dùng
            password: Mật khẩu
            
        Returns:
            True nếu thông tin đăng nhập hợp lệ, False nếu không
        """
        cursor = self.conn.cursor()
        password_hash = self._hash_password(password)
        cursor.execute(
            "SELECT password_hash, is_active FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        
        if row and row['password_hash'] == password_hash and row['is_active'] == 1:
            # Cập nhật thời gian đăng nhập cuối
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
                (username,)
            )
            self.conn.commit()
            return True
        return False

    def user_exists(self, username):
        """Kiểm tra xem username đã tồn tại chưa"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        return cursor.fetchone() is not None

    def save_message(self, sender, content, receiver=None, message_type='public'):
        """
        Lưu tin nhắn vào database
        
        Args:
            sender: Người gửi
            content: Nội dung tin nhắn
            receiver: Người nhận (Username cho private, GroupID cho group, None cho public)
            message_type: Loại tin nhắn ('public', 'private', hoặc 'group')
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO messages (sender, receiver, content, message_type) VALUES (?, ?, ?, ?)",
            (sender, str(receiver) if receiver is not None else None, content, message_type)
        )
        self.conn.commit()

    def get_history(self, limit=50, message_type='public', username=None, group_id=None):
        """
        Lấy lịch sử tin nhắn
        
        Args:
            limit: Số lượng tin nhắn tối đa
            message_type: Loại tin nhắn ('public', 'private', 'group', hoặc None cho tất cả)
            username: Nếu được chỉ định, chỉ lấy tin nhắn liên quan đến user này
            group_id: Nếu được chỉ định, chỉ lấy tin nhắn của nhóm này
            
        Returns:
            List các Rows
        """
        cursor = self.conn.cursor()
        
        if message_type == 'public':
            cursor.execute('''
                SELECT sender, receiver, content, timestamp, message_type 
                FROM messages 
                WHERE message_type = 'public'
                ORDER BY id DESC LIMIT ?
            ''', (limit,))
        elif message_type == 'private' and username:
            # Lấy tin nhắn riêng của user
            cursor.execute('''
                SELECT sender, receiver, content, timestamp, message_type 
                FROM messages 
                WHERE message_type = 'private' AND (sender = ? OR receiver = ?)
                ORDER BY id DESC LIMIT ?
            ''', (username, username, limit))
        elif message_type == 'group' and group_id:
            # Lấy tin nhắn của nhóm
            cursor.execute('''
                SELECT sender, receiver, content, timestamp, message_type 
                FROM messages 
                WHERE message_type = 'group' AND receiver = ?
                ORDER BY id DESC LIMIT ?
            ''', (str(group_id), limit))
        else:
            # Lấy tất cả tin nhắn liên quan đến user
            if username:
                cursor.execute('''
                    SELECT sender, receiver, content, timestamp, message_type 
                    FROM messages 
                    WHERE message_type = 'public' 
                       OR (message_type = 'private' AND (sender = ? OR receiver = ?))
                       OR (message_type = 'group' AND receiver IN (SELECT group_id FROM group_members WHERE username = ?))
                    ORDER BY id DESC LIMIT ?
                ''', (username, username, username, limit))
            else:
                cursor.execute('''
                    SELECT sender, receiver, content, timestamp, message_type 
                    FROM messages 
                    ORDER BY id DESC LIMIT ?
                ''', (limit,))
        
        rows = cursor.fetchall()
        # Reverse để hiển thị tin nhắn cũ nhất trước
        return rows[::-1]

    def create_group(self, name, creator):
        """Tạo nhóm mới và thêm creator làm thành viên đầu tiên"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO groups (name, creator) VALUES (?, ?)",
                (name, creator)
            )
            group_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO group_members (group_id, username) VALUES (?, ?)",
                (group_id, creator)
            )
            self.conn.commit()
            return group_id
        except Exception as e:
            print(f"[DB ERROR] create_group failed: {e}")
            return None

    def add_member_to_group(self, group_id, username):
        """Thêm thành viên vào nhóm"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO group_members (group_id, username) VALUES (?, ?)",
                (group_id, username)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[DB ERROR] add_member_to_group failed: {e}")
            return False

    def remove_member_from_group(self, group_id, username):
        """Xóa thành viên khỏi nhóm"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM group_members WHERE group_id = ? AND username = ?",
                (group_id, username)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[DB ERROR] remove_member_from_group failed: {e}")
            return False

    def get_user_groups(self, username):
        """Lấy danh sách các nhóm mà user tham gia"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT g.id, g.name, g.creator, g.created_at
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.username = ?
        ''', (username,))
        return [dict(row) for row in cursor.fetchall()]

    def get_all_groups(self):
        """Lấy danh sách tất cả các nhóm"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, creator, created_at FROM groups")
        return [dict(row) for row in cursor.fetchall()]

    def get_group_members(self, group_id):
        """Lấy danh sách thành viên của nhóm"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT username FROM group_members WHERE group_id = ?
        ''', (group_id,))
        return [row['username'] for row in cursor.fetchall()]

    def get_user_info(self, username):
        """
        Lấy thông tin người dùng
        
        Returns:
            Dictionary chứa thông tin user hoặc None nếu không tìm thấy
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT username, created_at, last_login, is_active FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        if row:
            return {
                'username': row['username'],
                'created_at': row['created_at'],
                'last_login': row['last_login'],
                'is_active': bool(row['is_active'])
            }
        return None

    def get_all_users(self, active_only=True):
        """
        Lấy danh sách tất cả người dùng
        
        Args:
            active_only: Chỉ lấy user đang active
            
        Returns:
            List các dictionary chứa thông tin user
        """
        cursor = self.conn.cursor()
        if active_only:
            cursor.execute(
                "SELECT username, created_at, last_login FROM users WHERE is_active = 1 ORDER BY username"
            )
        else:
            cursor.execute(
                "SELECT username, created_at, last_login, is_active FROM users ORDER BY username"
            )
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def deactivate_user(self, username):
        """Vô hiệu hóa tài khoản người dùng"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET is_active = 0 WHERE username = ?",
            (username,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def get_message_count(self, username=None):
        """Đếm số lượng tin nhắn (tổng hoặc của một user)"""
        cursor = self.conn.cursor()
        if username:
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE sender = ? OR receiver = ?",
                (username, username)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM messages")
        return cursor.fetchone()[0]

    def export_messages(self, filepath):
        """Xuất tất cả tin nhắn ra file JSON"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM messages ORDER BY timestamp")
        messages = cursor.fetchall()
        
        # Convert to list of dicts
        messages_list = []
        for msg in messages:
            messages_list.append({
                'id': msg['id'],
                'sender': msg['sender'],
                'receiver': msg['receiver'],
                'content': msg['content'],
                'message_type': msg['message_type'],
                'timestamp': msg['timestamp']
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(messages_list, f, ensure_ascii=False, indent=2)
        
        return len(messages_list)

    def import_messages(self, filepath):
        """Nhập tin nhắn từ file JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        
        cursor = self.conn.cursor()
        imported_count = 0
        
        for msg in messages:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO messages 
                    (id, sender, receiver, content, message_type, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    msg['id'],
                    msg['sender'],
                    msg['receiver'],
                    msg['content'],
                    msg['message_type'],
                    msg['timestamp']
                ))
                if cursor.rowcount > 0:
                    imported_count += 1
            except Exception as e:
                print(f"Lỗi khi import tin nhắn ID {msg.get('id')}: {e}")
                continue
        
        self.conn.commit()
        return imported_count

    @contextmanager
    def transaction(self):
        """Context manager để quản lý transaction"""
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def close(self):
        """Đóng kết nối database"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Support context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support context manager"""
        self.close()
