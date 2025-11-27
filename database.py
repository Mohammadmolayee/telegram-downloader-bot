# database.py
import sqlite3
from datetime import datetime
import hashlib

DB = "bot.db"


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT UNIQUE,
            password TEXT,
            language TEXT DEFAULT 'fa',
            theme TEXT DEFAULT 'light'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            title TEXT,
            time TEXT
        )
    """)

    conn.commit()
    conn.close()


def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()


def user_exists(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    ok = c.fetchone()
    conn.close()
    return ok is not None


def create_user(user_id, name, username, password):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, 'fa', 'light')",
                  (user_id, name, username, hash_pass(password)))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def login(username, password):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE username=? AND password=?",
              (username, hash_pass(password)))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_user(user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "user_id": row[0],
        "name": row[1],
        "username": row[2],
        "language": row[4],
        "theme": row[5]
    }


def set_language(user_id, lang):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
    conn.commit()
    conn.close()


def set_theme(user_id, theme):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE users SET theme=? WHERE user_id=?", (theme, user_id))
    conn.commit()
    conn.close()


def save_download(user_id, url, title):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO downloads (user_id, url, title, time) VALUES (?, ?, ?, ?)",
              (user_id, url, title, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_last_downloads(user_id, limit=5):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT title, url, time FROM downloads WHERE user_id=? ORDER BY id DESC LIMIT ?",
              (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows
