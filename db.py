# db.py — database helpers
import sqlite3
from datetime import datetime, timedelta
import bcrypt
from typing import Optional, Tuple, List

DB_PATH = "downloads.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL;')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            first_name TEXT,
            password_hash BLOB,
            lang TEXT DEFAULT 'fa',
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            platform TEXT,
            url TEXT,
            title TEXT,
            file_type TEXT,
            file_size INTEGER,
            downloaded_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def create_user(user_id: int, username: str, first_name: str, password: str, lang: str = 'fa') -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        hashed = hash_password(password)
        c.execute('''
            INSERT INTO users (user_id, username, first_name, password_hash, lang, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, sqlite3.Binary(hashed), lang, datetime.utcnow().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_username(username: str) -> Optional[Tuple[int,str,str,bytes,str]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, username, first_name, password_hash, lang FROM users WHERE username=?', (username,))
    row = c.fetchone()
    conn.close()
    return row

def user_exists(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE user_id=?', (user_id,))
    r = c.fetchone() is not None
    conn.close()
    return r

def get_user_lang(user_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT lang FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 'fa'

def set_user_lang(user_id: int, lang: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET lang=? WHERE user_id=?', (lang, user_id))
    conn.commit()
    conn.close()

def save_download(user_id: int, platform: str, url: str, title: str, file_type: str, file_size: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO downloads (user_id, platform, url, title, file_type, file_size, downloaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, platform, url, title, file_type, file_size, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_user_downloads(user_id: int, limit: int = 10) -> List[Tuple]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT platform, title, file_type, file_size, downloaded_at
        FROM downloads WHERE user_id=? ORDER BY downloaded_at DESC LIMIT ?
    ''', (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_daily_download_count(user_id: int) -> int:
    since = datetime.utcnow() - timedelta(days=1)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM downloads WHERE user_id=? AND downloaded_at>=?', (user_id, since.isoformat()))
    row = c.fetchone()
    conn.close()
    return int(row[0]) if row else 0

def get_user_stats(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*), COALESCE(SUM(file_size),0) FROM downloads WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return int(row[0]), int(row[1])
