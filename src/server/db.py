import sqlite3
import os
import hashlib
from datetime import datetime
from contextlib import contextmanager
import json

# Main DB: Users, Groups Metadata, Group Members, Public/Private Messages
DB_PATH = os.path.join(os.path.dirname(__file__), 'chat.db')
# Directory for Separate Group DBs: Group Chat History
GROUPS_DATA_DIR = os.path.join(os.path.dirname(__file__), 'groups_data')

class Database:
    def __init__(self):
        """Initialize main DB connection and ensure groups_data directory exists"""
        # Ensure groups data directory exists
        os.makedirs(GROUPS_DATA_DIR, exist_ok=True)

        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        """Create tables in the Main DB"""
        cursor = self.conn.cursor()
        
        # We can implement a simple migration check or just create if not exists
        # Bảng users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Bảng messages (Main DB stores Public & Private only)
        # Note: receiver column used for Private chat (username)
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
        
        # Bảng groups (Metadata only)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                creator TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator) REFERENCES users(username)
            )
        ''')

        # Bảng group_members (Membership persistence)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                group_id INTEGER,
                username TEXT,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, username),
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            )
        ''')

        # Indexes for main DB
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(message_type)')
        
        self.conn.commit()

    def _get_group_db_path(self, group_id):
        """Return the path to the specific group's database file"""
        return os.path.join(GROUPS_DATA_DIR, f'group_{group_id}.db')

    def _init_group_db(self, group_id):
        """Initialize a specific group database with messages table"""
        db_path = self._get_group_db_path(group_id)
        # Connect (creates file if not exists)
        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            
            # Create messages table for THIS group
            conn.execute('''
                CREATE TABLE IF NOT EXISTS group_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_grp_msg_timestamp ON group_messages(timestamp DESC)')
            conn.commit()
            return conn
        except Exception as e:
            print(f"[DB ERROR] Failed to init group DB {group_id}: {e}")
            return None

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        cursor = self.conn.cursor()
        try:
            password_hash = self._hash_password(password)
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login_user(self, username, password):
        cursor = self.conn.cursor()
        password_hash = self._hash_password(password)
        cursor.execute("SELECT password_hash, is_active FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and row['password_hash'] == password_hash and row['is_active'] == 1:
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?", (username,))
            self.conn.commit()
            return True
        return False

    def user_exists(self, username):
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        return cursor.fetchone() is not None

    def save_message(self, sender, content, receiver=None, message_type='public'):
        """
        Lưu tin nhắn. Nếu là GROUP, lưu vào DB riêng của nhóm.
        Nếu là Public/Private, lưu vào Main DB.
        """
        print(f"[DB DEBUG] Saving message: type={message_type}, sender={sender}, receiver={receiver}")
        
        if message_type == 'group':
            # Save to Group DB
            if receiver is None: return # Should be group_id
            group_id = receiver
            
            conn = self._init_group_db(group_id)
            if conn:
                try:
                    conn.execute(
                        "INSERT INTO group_messages (sender, content) VALUES (?, ?)",
                        (sender, content)
                    )
                    conn.commit()
                    print(f"[DB] Saved group message to {self._get_group_db_path(group_id)}")
                except Exception as e:
                    print(f"[DB ERROR] Failed to save group message: {e}")
                finally:
                    conn.close()
                
        else:
            # Save to Main DB (Public / Private)
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO messages (sender, receiver, content, message_type) VALUES (?, ?, ?, ?)",
                (sender, str(receiver) if receiver is not None else None, content, message_type)
            )
            self.conn.commit()

    def get_history(self, limit=50, message_type='public', username=None, group_id=None):
        """
        Lấy lịch sử. Nếu là GROUP, lấy từ DB riêng.
        """
        if message_type == 'group' and group_id:
            # Query Group DB
            try:
                db_path = self._get_group_db_path(group_id)
                if not os.path.exists(db_path):
                    return []
                
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT sender, content, timestamp 
                    FROM group_messages 
                    ORDER BY id DESC LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                conn.close()
                
                # Transform to match expected structure
                result = []
                for row in rows:
                    r_dict = dict(row)
                    r_dict['receiver'] = group_id
                    r_dict['message_type'] = 'group'
                    result.append(r_dict)
                
                print(f"[DB DEBUG] Retrieved {len(result)} messages from {db_path}")
                return result[::-1]
            except Exception as e:
                print(f"[DB ERROR] Failed to get group history: {e}")
                return []
                
        else:
            # Query Main DB
            cursor = self.conn.cursor()
            if message_type == 'public':
                cursor.execute('''
                    SELECT sender, receiver, content, timestamp, message_type 
                    FROM messages WHERE message_type = 'public'
                    ORDER BY id DESC LIMIT ?
                ''', (limit,))
            elif message_type == 'private' and username:
                cursor.execute('''
                    SELECT sender, receiver, content, timestamp, message_type 
                    FROM messages 
                    WHERE message_type = 'private' AND (sender = ? OR receiver = ?)
                    ORDER BY id DESC LIMIT ?
                ''', (username, username, limit))
            else:
                return []
            
            rows = cursor.fetchall()
            return rows[::-1]

    def create_group(self, name, creator):
        """Tạo nhóm mới trong Metadata và khởi tạo DB riêng"""
        cursor = self.conn.cursor()
        try:
            # 1. Create metadata in Main DB
            cursor.execute("INSERT INTO groups (name, creator) VALUES (?, ?)", (name, creator))
            group_id = cursor.lastrowid
            
            # 2. Add creator to members in Main DB
            cursor.execute("INSERT INTO group_members (group_id, username) VALUES (?, ?)", (group_id, creator))
            self.conn.commit()
            
            # 3. Initialize separate DB file
            self._init_group_db(group_id)
            
            return group_id
        except Exception as e:
            print(f"[DB ERROR] create_group failed: {e}")
            return None

    def add_member_to_group(self, group_id, username):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO group_members (group_id, username) VALUES (?, ?)", (group_id, username))
            self.conn.commit()
            return True
        except: return False

    def remove_member_from_group(self, group_id, username):
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM group_members WHERE group_id = ? AND username = ?", (group_id, username))
            self.conn.commit()
            return True
        except: return False
    
    def get_all_groups(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, creator, created_at FROM groups")
        return [dict(row) for row in cursor.fetchall()]

    def get_group_members(self, group_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT username FROM group_members WHERE group_id = ?", (group_id,))
        return [row['username'] for row in cursor.fetchall()]
        
    def get_user_groups(self, username):
        """Lấy danh sách các nhóm mà user tham gia"""
        cursor = self.conn.cursor()
        # Returns metadata linked to the user
        cursor.execute('''
            SELECT g.id, g.name, g.creator, g.created_at
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.username = ?
        ''', (username,))
        return [dict(row) for row in cursor.fetchall()]

    def get_all_users(self, active_only=True):
        cursor = self.conn.cursor()
        sql = "SELECT username, created_at, last_login, is_active FROM users"
        if active_only: sql += " WHERE is_active = 1"
        cursor.execute(sql + " ORDER BY username")
        return [dict(row) for row in cursor.fetchall()]
        
    def get_user_info(self, username): 
        # Added missing method for completeness
        cursor = self.conn.cursor()
        cursor.execute("SELECT username, created_at, last_login, is_active FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        if self.conn: self.conn.close()
