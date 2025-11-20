# db.py

import sqlite3
from datetime import datetime
from config import DATABASE_PATH


def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        fullname TEXT,
        username TEXT UNIQUE,
        password TEXT,
        language TEXT DEFAULT 'fa'
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()


def create_user(user_id, fullname, username, password):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (user_id, fullname, username, password) VALUES (?, ?, ?, ?)",
                  (user_id, fullname, username, password))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def check_login(username, password):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    c.execute("SELECT user_id FROM users WHERE username=? AND password=?", (username, password))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_user_language(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    c.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "fa"


def set_language(user_id, lang):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
    conn.commit()
    conn.close()


def count_downloads_today(user_id):
    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM downloads WHERE user_id=? AND date=?", (user_id, today))
    row = c.fetchone()
    conn.close()
    return row[0]


def add_download(user_id):
    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO downloads (user_id, date) VALUES (?, ?)", (user_id, today))
    conn.commit()
    conn.close()
