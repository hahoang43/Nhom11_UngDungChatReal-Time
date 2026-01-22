import sqlite3
import os
import hashlib
from datetime import datetime
from contextlib import contextmanager
import json
import urllib.parse

# Try importing psycopg2 for PostgreSQL support
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/chat.db'))

class Database:
    def delete_group(self, group_id, username):
        """Delete a group if the user is the creator. Removes group, its members, and messages."""
        try:
            # Check if user is creator
            cursor = self.execute_query("SELECT creator FROM groups WHERE id = ?", (group_id,))
            row = cursor.fetchone()
            print(f"[DEBUG] Xóa nhóm: group_id={group_id}, username={username}, creator_trong_db={row['creator'] if row else None}", flush=True)
            if not row or row['creator'] != username:
                print(f"[DEBUG] Không xóa được: username gửi lên='{username}', creator trong db='{row['creator'] if row else None}'", flush=True)
                return False
            # Delete group members
            self.execute_query("DELETE FROM group_members WHERE group_id = ?", (group_id,))
            # Delete group messages
            self.execute_query("DELETE FROM messages WHERE message_type = 'group' AND receiver = ?", (str(group_id),))
            # Delete group
            self.execute_query("DELETE FROM groups WHERE id = ?", (group_id,))
            self.conn.commit()
            print(f"[DEBUG] Đã xóa nhóm thành công: group_id={group_id}", flush=True)
            return True
        except Exception as e:
            print(f"Delete group error: {e}", flush=True)
            self.conn.rollback()
            return False
    def __init__(self):
        """Khởi tạo kết nối database. Hỗ trợ SQLite (local) và Postgres (Production)"""
        self.db_url = os.environ.get('DATABASE_URL')
        self.conn = None
        self.db_type = 'sqlite'

        if self.db_url and self.db_url.startswith('postgres'):
            print(f"✅ DETECTED DATABASE_URL: Connecting to PostgreSQL...")
            if not psycopg2:
                print(f"❌ ERROR: psycopg2 is missing despite DATABASE_URL being set.")
                raise ImportError("psycopg2 is required for PostgreSQL connection")
            self.db_type = 'postgres'
            self.connect_postgres()
            print(f"✅ Connected to PostgreSQL successfully.")
        else:
            print(f"⚠️ NO DATABASE_URL DETECTED: Utilizing local SQLite database.")
            self.db_type = 'sqlite'
            self.connect_sqlite()
            print(f"✅ Connected to SQLite successfully.")
            
        self.create_tables()

    def connect_sqlite(self):
        """Kết nối tới SQLite"""
        # Ensure data directory exists
        data_dir = os.path.dirname(DB_PATH)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row

    def connect_postgres(self):
        """Kết nối tới PostgreSQL"""
        try:
            self.conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        except Exception as e:
            print(f"[DB ERROR] Failed to connect to Postgres: {e}")
            # Fallback to SQLite if Postgres fails (optional, mostly for resilience)
            # For now we raise to fail fast
            raise e

    def get_cursor(self):
        """Trả về cursor tùy theo loại DB"""
        return self.conn.cursor()

    def execute_query(self, query, params=(), cursor=None):
        """
        Helper để execute query, tự động xử lý placeholder
        SQLite dùng '?', Postgres dùng '%s'
        """
        should_close_cursor = False
        if cursor is None:
            cursor = self.get_cursor()
            should_close_cursor = True

        try:
            # Chuyển đổi placeholder nếu là Postgres
            final_query = query
            if self.db_type == 'postgres':
                # Thay thế ? bằng %s
                final_query = query.replace('?', '%s')
            
            cursor.execute(final_query, params)
            
            # Nếu là lệnh SELECT, trả về cursor (để fetch)
            # Nếu là lệnh INSERT/UPDATE, trả về cursor (để commit hoặc lấy lastrowid)
            return cursor
        except Exception as e:
            print(f"[DB ERROR] Query failed: {final_query} | Params: {params} | Error: {e}")
            raise e
        finally:
            if should_close_cursor and self.db_type == 'postgres':
                # Postgres cursor nên được đóng nếu không dùng tiếp? 
                # Thực ra với context manager thì ta handle ở ngoài. 
                # Ở đây ta return cursor nên k đóng vội nếu là SELECT
                pass

    def create_tables(self):
        """Tạo các bảng trong database"""
        cursor = self.get_cursor()
        
        # Define types based on DB
        id_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if self.db_type == 'sqlite' else "SERIAL PRIMARY KEY"
        datetime_def = "DATETIME" if self.db_type == 'sqlite' else "TIMESTAMP"
        
        # Bảng users
        try:
            self.execute_query(f'''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    display_name TEXT,
                    created_at {datetime_def} DEFAULT CURRENT_TIMESTAMP,
                    last_login {datetime_def},
                    is_active INTEGER DEFAULT 1
                )
            ''', cursor=cursor)
            
            # Bảng messages
            self.execute_query(f'''
                CREATE TABLE IF NOT EXISTS messages (
                    id {id_type},
                    sender TEXT NOT NULL,
                    receiver TEXT,
                    content TEXT NOT NULL,
                    message_type TEXT DEFAULT 'public',
                    timestamp {datetime_def} DEFAULT CURRENT_TIMESTAMP
                )
            ''', cursor=cursor)
            # Note: FK removed for simplicity in cross-db compat or add specific ALTER later
            # SQLite supports inline FK, Postgres too but syntax slightly diff if we want complex constraints.
            # Keeping it simple for now.

            # Bảng groups
            self.execute_query(f'''
                CREATE TABLE IF NOT EXISTS groups (
                    id {id_type},
                    name TEXT NOT NULL,
                    creator TEXT NOT NULL,
                    created_at {datetime_def} DEFAULT CURRENT_TIMESTAMP
                )
            ''', cursor=cursor)

            # Bảng group_members
            self.execute_query(f'''
                CREATE TABLE IF NOT EXISTS group_members (
                    group_id INTEGER,
                    username TEXT,
                    joined_at {datetime_def} DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (group_id, username)
                )
            ''', cursor=cursor)

            # Bảng friends
            # status: 'pending', 'accepted'
            self.execute_query(f'''
                CREATE TABLE IF NOT EXISTS friends (
                    user1 TEXT,
                    user2 TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at {datetime_def} DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user1, user2)
                )
            ''', cursor=cursor)

            
            # Indexes
            self.execute_query('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)', cursor=cursor) # PG defaults default to desc? or just timestamp
            self.execute_query('CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)', cursor=cursor)
            self.execute_query('CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver)', cursor=cursor)
            
            self.conn.commit()
            
            # Migration check only for local sqlite usually, but can check columns simply
            self._check_migrations(cursor)
            
        except Exception as e:
            print(f"[DB INIT ERROR] {e}")
            self.conn.rollback()

    def _check_migrations(self, cursor):
        """Simple migration check"""
        try:
            # Check receiver column in messages
            if self.db_type == 'sqlite':
                cursor.execute("PRAGMA table_info(messages)")
                cols = [r['name'] for r in cursor.fetchall()]
                if 'receiver' not in cols:
                    print("Migrating messages table...")
                    self.execute_query("ALTER TABLE messages ADD COLUMN receiver TEXT", cursor=cursor)
                    self.execute_query("ALTER TABLE messages ADD COLUMN message_type TEXT DEFAULT 'public'", cursor=cursor)
                    self.conn.commit()
            else:
                # Postgres check column
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='messages'")
                cols = [row['column_name'] for row in cursor.fetchall()]
                if 'receiver' not in cols:
                     print("Migrating messages table (PG)...")
                     self.execute_query("ALTER TABLE messages ADD COLUMN receiver TEXT", cursor=cursor)
                     self.execute_query("ALTER TABLE messages ADD COLUMN message_type TEXT DEFAULT 'public'", cursor=cursor)
                     self.conn.commit()
            
            # Check display_name in users
            if self.db_type == 'sqlite':
                cursor.execute("PRAGMA table_info(users)")
                cols = [r['name'] for r in cursor.fetchall()]
                if 'display_name' not in cols:
                    print("Migrating users table (add display_name)...")
                    self.execute_query("ALTER TABLE users ADD COLUMN display_name TEXT", cursor=cursor)
                    self.conn.commit()
            else:
                 cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
                 cols = [row['column_name'] for row in cursor.fetchall()]
                 if 'display_name' not in cols:
                     print("Migrating users table (PG add display_name)...")
                     self.execute_query("ALTER TABLE users ADD COLUMN display_name TEXT", cursor=cursor)
                     self.conn.commit()

        except Exception as e:
            print(f"Migration check warning: {e}")

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        try:
            password_hash = self._hash_password(password)
            self.execute_query(
                "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
                (username, password_hash, username)
            )
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            return False

    def login_user(self, username, password):
        password_hash = self._hash_password(password)
        cursor = self.execute_query(
            "SELECT password_hash, is_active FROM users WHERE username = ?",
            (username,)
        )
        # Fetch logic varies slightly by driver if not normalized, but RealDictCursor and Row behave similarly
        row = cursor.fetchone()
        
        if row and row['password_hash'] == password_hash and row['is_active'] == 1:
            self.execute_query(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
                (username,)
            )
            self.conn.commit()
            return True
        return False

    def update_user_display_name(self, username, new_name):
        try:
            self.execute_query(
                "UPDATE users SET display_name = ? WHERE username = ?",
                (new_name, username)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Update name error: {e}")
            self.conn.rollback()
            return False

    def get_user_display_name(self, username):
        cursor = self.execute_query("SELECT display_name FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and row['display_name']:
            return row['display_name']
        return username

    def user_exists(self, username):
        cursor = self.execute_query("SELECT 1 FROM users WHERE username = ?", (username,))
        return cursor.fetchone() is not None

    def save_message(self, sender, content, receiver=None, message_type='public'):
        self.execute_query(
            "INSERT INTO messages (sender, receiver, content, message_type) VALUES (?, ?, ?, ?)",
            (sender, str(receiver) if receiver is not None else None, content, message_type)
        )
        self.conn.commit()

    def get_history(self, limit=50, message_type='public', username=None, group_id=None):
        query = ""
        params = []
        
        base_select = "SELECT sender, receiver, content, timestamp, message_type FROM messages"
        
        if message_type == 'public':
            query = f"{base_select} WHERE message_type = 'public' ORDER BY id DESC LIMIT ?"
            params = [limit]
        elif message_type == 'private' and username:
            query = f"{base_select} WHERE message_type = 'private' AND (sender = ? OR receiver = ?) ORDER BY id DESC LIMIT ?"
            params = [username, username, limit]
        elif message_type == 'group' and group_id:
            query = f"{base_select} WHERE message_type = 'group' AND receiver = ? ORDER BY id DESC LIMIT ?"
            params = [str(group_id), limit]
        else:
            # All messages for user
            if username:
                if self.db_type == 'sqlite':
                    # SQLite subquery
                    query = f"""
                        {base_select}
                        WHERE message_type = 'public' 
                           OR (message_type = 'private' AND (sender = ? OR receiver = ?))
                           OR (message_type = 'group' AND receiver IN (SELECT CAST(group_id AS TEXT) FROM group_members WHERE username = ?))
                        ORDER BY id DESC LIMIT ?
                    """
                else:
                    # Postgres subquery (casting might be needed depending on types)
                     query = f"""
                        {base_select}
                        WHERE message_type = 'public' 
                           OR (message_type = 'private' AND (sender = ? OR receiver = ?))
                           OR (message_type = 'group' AND receiver IN (SELECT CAST(group_id AS TEXT) FROM group_members WHERE username = ?))
                        ORDER BY id DESC LIMIT ?
                    """
                params = [username, username, username, limit]
            else:
                 query = f"{base_select} ORDER BY id DESC LIMIT ?"
                 params = [limit]

        cursor = self.execute_query(query, tuple(params))
        rows = cursor.fetchall()
        
        # Convert rows to dicts if needed (Row/RealDictCursor already act like dicts)
        # But we need a list of simple dicts for JSON serialization usually
        result = []
        for row in rows:
            # Normalize timestamp to string if it's datetime object
            ts = row['timestamp']
            if isinstance(ts, datetime):
                ts = ts.strftime('%Y-%m-%d %H:%M:%S')
                
            result.append({
                'sender': row['sender'],
                'receiver': row['receiver'],
                'content': row['content'],
                'timestamp': ts,
                'message_type': row['message_type']
            })
            
        return result[::-1] # Reverse to chrono order

    def create_group(self, name, creator):
        # Không cho phép tạo nhóm tên 'Chat Công Khai' hoặc các nhóm mặc định
        if name.strip().lower() in ["chat công khai", "public chat", "public", "công khai"]:
            return None
        try:
            cursor = self.execute_query(
                "INSERT INTO groups (name, creator) VALUES (?, ?)",
                (name, creator)
            )
            if self.db_type == 'sqlite':
                group_id = cursor.lastrowid
            else:
                cursor = self.execute_query("INSERT INTO groups (name, creator) VALUES (?, ?) RETURNING id", (name, creator))
                group_id = cursor.fetchone()['id']
            self.execute_query(
                "INSERT INTO group_members (group_id, username) VALUES (?, ?)",
                (group_id, creator)
            )
            self.conn.commit()
            return group_id
        except Exception as e:
            print(f"Create group error: {e}")
            self.conn.rollback()
            return None

    def add_member_to_group(self, group_id, username):
        try:
            # INSERT OR IGNORE syntax is SQLite specific. Postgres uses ON CONFLICT DO NOTHING
            if self.db_type == 'sqlite':
                self.execute_query(
                    "INSERT OR IGNORE INTO group_members (group_id, username) VALUES (?, ?)",
                    (group_id, username)
                )
            else:
                self.execute_query(
                    "INSERT INTO group_members (group_id, username) VALUES (?, ?) ON CONFLICT DO NOTHING",
                    (group_id, username)
                )
            self.conn.commit()
            return True
        except Exception:
            return False

    def remove_member_from_group(self, group_id, username):
        try:
            self.execute_query(
                "DELETE FROM group_members WHERE group_id = ? AND username = ?",
                (group_id, username)
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_user_groups(self, username):
        cursor = self.execute_query('''
            SELECT g.id, g.name, g.creator, g.created_at
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.username = ?
        ''', (username,))
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            ts = row['created_at']
            if isinstance(ts, datetime):
                ts = ts.strftime('%Y-%m-%d %H:%M:%S')
            result.append({
                'id': row['id'],
                'name': row['name'],
                'creator': row['creator'],
                'created_at': ts
            })
        return result


    def get_discoverable_groups(self, username):
        """
        Trả về các nhóm mà user chưa tham gia (ngoại trừ nhóm công khai).
        """
        cursor = self.execute_query('''
            SELECT g.id, g.name, g.creator, g.created_at
            FROM groups g
            WHERE LOWER(g.name) NOT IN ('chat công khai', 'public chat', 'public', 'công khai')
            AND g.id NOT IN (
                SELECT group_id FROM group_members WHERE username = ?
            )
        ''', (username,))
        return [dict(row) for row in cursor.fetchall()]

    def get_group_members(self, group_id):
        cursor = self.execute_query("SELECT username FROM group_members WHERE group_id = ?", (group_id,))
        return [row['username'] for row in cursor.fetchall()]

    def get_all_users(self):
        cursor = self.execute_query("SELECT username, display_name FROM users WHERE is_active = 1")
        return [{'username': row['username'], 'display_name': row['display_name'] or row['username']} for row in cursor.fetchall()]

    def request_friend(self, requester, target):
        """Create a friend request. Stores as (lower, higher) for unicity or directional?"""
        # Let's simple directional: user1 is requester, user2 is target for pending status
        # Check if already friends or pending
        try:
            # Check existing relationship in either direction
            cursor = self.execute_query('''
                SELECT status FROM friends 
                WHERE (user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?)
            ''', (requester, target, target, requester))
            row = cursor.fetchone()
            if row:
                return False, f"Relationship already exists: {row['status']}"

            self.execute_query(
                "INSERT INTO friends (user1, user2, status) VALUES (?, ?, 'pending')",
                (requester, target)
            )
            self.conn.commit()
            return True, "Request sent"
        except Exception as e:
            return False, str(e)

    def accept_friend(self, accepter, requester):
        """Accept a friend request"""
        try:
            # Update status where user1=requester AND user2=accepter
            cursor = self.execute_query(
                "UPDATE friends SET status = 'accepted' WHERE user1 = ? AND user2 = ? AND status = 'pending'",
                (requester, accepter)
            )
            if cursor.rowcount > 0:
                self.conn.commit()
                return True
            return False
        except Exception:
            self.conn.rollback()
            return False

    def get_friends_with_status(self, username):
        """Get all accepted friends for a user, including their last_login"""
        # Friends can be (user1=me, user2=them) OR (user1=them, user2=me)
        query = '''
            SELECT 
                CASE WHEN f.user1 = ? THEN f.user2 ELSE f.user1 END as friend_name,
                u.display_name,
                u.last_login
            FROM friends f
            JOIN users u ON u.username = (CASE WHEN f.user1 = ? THEN f.user2 ELSE f.user1 END)
            WHERE (f.user1 = ? OR f.user2 = ?) AND f.status = 'accepted'
        '''
        cursor = self.execute_query(query, (username, username, username, username))
        result = []
        for row in cursor.fetchall():
            ts = row['last_login']
            if isinstance(ts, datetime):
                ts = ts.isoformat()
            elif ts is None:
                ts = ""
                
            result.append({
                'username': row['friend_name'],
                'display_name': row['display_name'] or row['friend_name'],
                'last_login': ts
            })
        return result

    def get_pending_requests(self, username):
        """Get requests pending for this user (where user2 = username)"""
        query = '''
            SELECT f.user1 as requester, u.display_name
            FROM friends f
            JOIN users u ON u.username = f.user1
            WHERE f.user2 = ? AND f.status = 'pending'
        '''
        cursor = self.execute_query(query, (username,))
        return [{'username': row['requester'], 'display_name': row['display_name'] or row['requester']} for row in cursor.fetchall()]

    def get_sent_requests(self, username):
        """Get requests sent by this user (where user1 = username)"""
        query = '''
            SELECT f.user2 as target, u.display_name
            FROM friends f
            JOIN users u ON u.username = f.user2
            WHERE f.user1 = ? AND f.status = 'pending'
        '''
        cursor = self.execute_query(query, (username,))
        return [{'username': row['target'], 'display_name': row['display_name'] or row['target']} for row in cursor.fetchall()]
    
    def are_friends(self, user1, user2):
        cursor = self.execute_query('''
            SELECT 1 FROM friends 
            WHERE ((user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?)) 
            AND status = 'accepted'
        ''', (user1, user2, user2, user1))
        return cursor.fetchone() is not None

    def update_last_seen(self, username):
        """Update last_login timestamp now"""
        try:
            self.execute_query(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
                (username,)
            )
            self.conn.commit()
        except:
            pass

    def close(self):
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

