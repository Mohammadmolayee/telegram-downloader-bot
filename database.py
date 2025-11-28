# database.py
import sqlite3
import threading
from datetime import datetime
import hashlib

DB = "bot.db"
_lock = threading.Lock()

def _conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    with _lock:
        c = _conn()
        cur = c.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT UNIQUE,
            password_hash TEXT,
            language TEXT DEFAULT 'fa',
            theme TEXT DEFAULT 'light',
            created_at TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            title TEXT,
            file_type TEXT,
            created_at TEXT
        )""")
        c.commit()
        c.close()

def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def user_exists(user_id):
    c = _conn()
    cur = c.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    ok = cur.fetchone() is not None
    c.close()
    return ok

def create_user(user_id, name, username, password):
    try:
        c = _conn()
        cur = c.cursor()
        cur.execute("INSERT INTO users (user_id, name, username, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, name, username, _hash(password), datetime.utcnow().isoformat()))
        c.commit()
        c.close()
        return True
    except Exception:
        return False

def login(username, password):
    c = _conn()
    cur = c.cursor()
    cur.execute("SELECT user_id FROM users WHERE username=? AND password_hash=?", (username, _hash(password)))
    r = cur.fetchone()
    c.close()
    return r[0] if r else None

def get_user(user_id):
    c = _conn()
    cur = c.cursor()
    cur.execute("SELECT user_id, name, username, language, theme FROM users WHERE user_id=?", (user_id,))
    r = cur.fetchone()
    c.close()
    if not r:
        return None
    return {"user_id": r[0], "name": r[1], "username": r[2], "language": r[3] or "fa", "theme": r[4] or "light"}

def set_language(user_id, lang):
    c = _conn()
    cur = c.cursor()
    cur.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
    c.commit()
    c.close()

def set_theme(user_id, theme):
    c = _conn()
    cur = c.cursor()
    cur.execute("UPDATE users SET theme=? WHERE user_id=?", (theme, user_id))
    c.commit()
    c.close()

def save_download(user_id, url, title, file_type):
    c = _conn()
    cur = c.cursor()
    cur.execute("INSERT INTO downloads (user_id, url, title, file_type, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, url, title, file_type, datetime.utcnow().isoformat()))
    c.commit()
    c.close()

def recent_downloads(user_id, limit=10):
    c = _conn()
    cur = c.cursor()
    cur.execute("SELECT title, url, file_type, created_at FROM downloads WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (user_id, limit))
    rows = cur.fetchall()
    c.close()
    return rows
