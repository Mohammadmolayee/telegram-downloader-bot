# database.py
import sqlite3
from datetime import datetime
from config import DATABASE_PATH

def _conn():
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)

def init_db():
    conn = _conn()
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL;')
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        fullname TEXT,
        password TEXT,
        language TEXT DEFAULT 'fa',
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
        size INTEGER,
        downloaded_at TEXT
    )
    ''')
    conn.commit()
    conn.close()

# user management
def create_user(user_id: int, username: str, fullname: str, password: str, lang: str = 'fa') -> bool:
    conn = _conn()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (user_id, username, fullname, password, language, created_at) VALUES (?,?,?,?,?,?)',
                  (user_id, username, fullname, password, lang, datetime.utcnow().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def user_exists(user_id: int) -> bool:
    conn = _conn()
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE user_id=?', (user_id,))
    res = c.fetchone() is not None
    conn.close()
    return res

def get_user_by_username(username: str):
    conn = _conn()
    c = conn.cursor()
    c.execute('SELECT user_id, username, fullname, password, language FROM users WHERE username=?', (username,))
    row = c.fetchone()
    conn.close()
    return row

def get_user_by_id(user_id: int):
    conn = _conn()
    c = conn.cursor()
    c.execute('SELECT user_id, username, fullname, password, language FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def check_login(username: str, password: str):
    row = get_user_by_username(username)
    if not row:
        return None
    return row if row[3] == password else None

def set_user_lang(user_id: int, lang: str):
    conn = _conn()
    c = conn.cursor()
    c.execute('UPDATE users SET language=? WHERE user_id=?', (lang, user_id))
    conn.commit()
    conn.close()

def get_user_lang(user_id: int) -> str:
    row = get_user_by_id(user_id)
    if not row:
        return 'fa'
    return row[4] or 'fa'

# downloads
def save_download(user_id: int, platform: str, url: str, title: str, size: int):
    conn = _conn()
    c = conn.cursor()
    c.execute('INSERT INTO downloads (user_id, platform, url, title, size, downloaded_at) VALUES (?,?,?,?,?,?)',
              (user_id, platform, url, title, size, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_user_downloads(user_id: int, limit: int = 10):
    conn = _conn()
    c = conn.cursor()
    c.execute('SELECT platform, title, size, downloaded_at FROM downloads WHERE user_id=? ORDER BY downloaded_at DESC LIMIT ?', (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_daily_download_count(user_id: int) -> int:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM downloads WHERE user_id=? AND date(downloaded_at)=?", (user_id, today))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_user_stats(user_id: int):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(size) FROM downloads WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return (row[0] or 0, row[1] or 0)
