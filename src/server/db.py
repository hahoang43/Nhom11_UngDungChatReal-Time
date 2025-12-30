import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'chat.db')

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT
            )
        ''')
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def register_user(self, username, password):
        """Registers a new user. Returns True if successful, False if username exists."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login_user(self, username, password):
        """Checks credentials. Returns True if valid."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and row[0] == password:
            return True
        return False

    def save_message(self, sender, content):
        """Saves a chat message."""
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO messages (sender, content) VALUES (?, ?)", (sender, content))
        self.conn.commit()

    def get_history(self, limit=50):
        """Retrieves last N messages."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT sender, content, timestamp FROM messages ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return rows[::-1] # Reverse to show oldest first

    def close(self):
        self.conn.close()
