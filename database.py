# database.py
import sqlite3
from datetime import datetime, date

DB_PATH = "database.db"


def connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    db = connect()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            password TEXT,
            language TEXT DEFAULT 'fa',
            theme TEXT DEFAULT 'light',
            is_member INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            timestamp TEXT
        )
    """)

    db.commit()
    db.close()


# -------------------------
# USER MANAGEMENT
# -------------------------
def user_exists(user_id):
    db = connect()
    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone() is not None
    db.close()
    return exists


def create_user(user_id, name, username, password):
    db = connect()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO users (user_id, name, username, password, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, name, username, password, datetime.now().isoformat()))

    db.commit()
    db.close()


def get_user(user_id):
    db = connect()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    db.close()
    return row


def set_language(user_id, lang):
    db = connect()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    db.commit()
    db.close()


def set_theme(user_id, theme):
    db = connect()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET theme = ? WHERE user_id = ?", (theme, user_id))
    db.commit()
    db.close()


def authenticate_user(user_id, username, password):
    db = connect()
    cursor = db.cursor()
    cursor.execute("""
        SELECT 1 FROM users
        WHERE user_id = ? AND username = ? AND password = ?
    """, (user_id, username, password))
    ok = cursor.fetchone() is not None
    db.close()
    return ok


# -------------------------
# DOWNLOAD RECORDS
# -------------------------
def add_download(user_id, url):
    db = connect()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO downloads (user_id, url, timestamp)
        VALUES (?, ?, ?)
    """, (user_id, url, datetime.now().isoformat()))
    db.commit()
    db.close()


def get_daily_downloads(user_id):
    today = date.today().isoformat()
    db = connect()
    cursor = db.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM downloads
        WHERE user_id = ? AND timestamp LIKE ?
    """, (user_id, today + "%"))

    count = cursor.fetchone()[0]
    db.close()
    return count


def get_recent_downloads(user_id, limit=10):
    db = connect()
    cursor = db.cursor()
    cursor.execute("""
        SELECT url, timestamp
        FROM downloads
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, limit))

    rows = cursor.fetchall()
    db.close()
    return rows
