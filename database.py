# database.py
import sqlite3
from datetime import datetime
import hashlib
import threading

DB = "bot.db"
_lock = threading.Lock()

def _connect():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    with _lock:
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT UNIQUE,
                password_hash TEXT,
                language TEXT DEFAULT 'fa',
                theme TEXT DEFAULT 'light',
                created_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                url TEXT,
                title TEXT,
                file_type TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# user functions
def user_exists(user_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    ok = c.fetchone() is not None
    conn.close()
    return ok

def create_user(user_id, name, username, password):
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute("INSERT INTO users (user_id, name, username, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                  (user_id, name, username, _hash(password), datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def login(username, password):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE username=? AND password_hash=?", (username, _hash(password)))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_user(user_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT user_id, name, username, language, theme FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "user_id": row[0],
        "name": row[1],
        "username": row[2],
        "language": row[3] or "fa",
        "theme": row[4] or "light"
    }

def set_language(user_id, lang):
    conn = _connect()
    c = conn.cursor()
    c.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
    conn.commit()
    conn.close()

def set_theme(user_id, theme):
    conn = _connect()
    c = conn.cursor()
    c.execute("UPDATE users SET theme=? WHERE user_id=?", (theme, user_id))
    conn.commit()
    conn.close()

# downloads
def save_download(user_id, url, title, file_type):
    conn = _connect()
    c = conn.cursor()
    c.execute("INSERT INTO downloads (user_id, url, title, file_type, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, url, title, file_type, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def recent_downloads(user_id, limit=10):
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT title, url, file_type, created_at FROM downloads WHERE user_id=? ORDER BY id DESC LIMIT ?",
              (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows
