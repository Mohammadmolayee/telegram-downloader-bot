import sqlite3
from datetime import datetime

DB = "bot_data.db"

def _conn():
    return sqlite3.connect(DB, timeout=30)

def init_db():
    c = _conn(); cur = c.cursor()
    cur.execute('PRAGMA journal_mode=WAL;')
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        language TEXT DEFAULT 'fa',
        theme TEXT DEFAULT 'light',
        created_at TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS downloads(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        url TEXT,
        platform TEXT,
        file_name TEXT,
        status TEXT,
        created_at TEXT
    )""")
    c.commit(); c.close()

# user helpers
def user_exists(uid):
    c = _conn(); cur = c.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id=?", (uid,))
    r = cur.fetchone(); c.close()
    return bool(r)

def create_user(uid, name, username, password):
    try:
        c = _conn(); cur = c.cursor()
        cur.execute("INSERT INTO users(user_id,name,username,password,created_at) VALUES (?,?,?,?,?)",
                    (uid, name, username, password, datetime.utcnow().isoformat()))
        c.commit(); c.close(); return True
    except Exception:
        return False

def get_user(uid):
    c = _conn(); cur = c.cursor()
    cur.execute("SELECT user_id,name,username,password,language,theme,created_at FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone(); c.close()
    if not row: return None
    return {"user_id": row[0], "name": row[1], "username": row[2], "password": row[3],
            "language": row[4] or "fa", "theme": row[5] or "light", "created_at": row[6]}

def login(username, password):
    c = _conn(); cur = c.cursor()
    cur.execute("SELECT user_id FROM users WHERE username=? AND password=?", (username, password))
    r = cur.fetchone(); c.close()
    return r[0] if r else None

def set_language(uid, lang):
    c = _conn(); cur = c.cursor()
    cur.execute("UPDATE users SET language=? WHERE user_id=?", (lang, uid)); c.commit(); c.close()

def set_theme(uid, theme):
    c = _conn(); cur = c.cursor()
    cur.execute("UPDATE users SET theme=? WHERE user_id=?", (theme, uid)); c.commit(); c.close()

# downloads
def add_download(user_id, url, platform, file_name="", status="pending"):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO downloads(user_id,url,platform,file_name,status,created_at) VALUES (?,?,?,?,?,?)",
                (user_id, url, platform, file_name, status, datetime.utcnow().isoformat()))
    c.commit(); id = cur.lastrowid; c.close(); return id

def set_download_status(dl_id, status, file_name=None):
    c = _conn(); cur = c.cursor()
    if file_name:
        cur.execute("UPDATE downloads SET status=?, file_name=? WHERE id=?", (status, file_name, dl_id))
    else:
        cur.execute("UPDATE downloads SET status=? WHERE id=?", (status, dl_id))
    c.commit(); c.close()
