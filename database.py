# database.py
# ساده، ایمن و هر تابع اتصال خودش را باز و می‌بندد تا قفل sqlite کمتر پیش آید.

import sqlite3
from datetime import datetime, date
from typing import Optional
from settings import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            platform TEXT,
            url TEXT,
            title TEXT,
            file_type TEXT,
            downloaded_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# User ops
def create_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (user_id, username, first_name, created_at) VALUES (?, ?, ?, ?)",
                  (user_id, username, first_name, datetime.utcnow().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def user_exists(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    ex = c.fetchone() is not None
    conn.close()
    return ex

def get_user(user_id: int):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, created_at FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

# Download ops
def save_download(user_id: int, platform: str, url: str, title: str, file_type: str):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    c.execute("INSERT INTO downloads (user_id, platform, url, title, file_type, downloaded_at) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, platform, url, title, file_type, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_downloads_recent(user_id: int, limit: int = 5):
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    c.execute("""
        SELECT platform, title, file_type, downloaded_at
        FROM downloads WHERE user_id = ? ORDER BY downloaded_at DESC LIMIT ?
    """, (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def downloads_count_today(user_id: int) -> int:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    today_str = date.today().isoformat()
    c.execute("""
        SELECT COUNT(*) FROM downloads
        WHERE user_id = ? AND date(downloaded_at) = ?
    """, (user_id, today_str))
    cnt = c.fetchone()[0]
    conn.close()
    return cnt

def can_download(user_id: int) -> bool:
    # if no user -> guest limits
    if not user_exists(user_id):
        return downloads_count_today(user_id) < GUEST_DAILY_LIMIT
    else:
        return downloads_count_today(user_id) < USER_DAILY_LIMIT

# init DB on import
init_db()

# NOTE: GUEST_DAILY_LIMIT & USER_DAILY_LIMIT referenced from settings
from settings import GUEST_DAILY_LIMIT, USER_DAILY_LIMIT
