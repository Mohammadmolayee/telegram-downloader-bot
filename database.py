# database.py
import sqlite3
import re

DB = "bot.db"

def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        language TEXT DEFAULT 'fa'
    )
    """)
    con.commit()
    con.close()

def user_exists(user_id):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    ok = cur.fetchone() is not None
    con.close()
    return ok

def create_user(user_id, name, username, password):
    if not re.match(r"^[A-Za-zآ-ی]+$", name):
        return False
    
    if not re.match(r"^[A-Za-z0-9_]+$", username):
        return False
    
    if not re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]{6,}$", password):
        return False
    
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute(
            "INSERT INTO users(user_id,name,username,password) VALUES(?,?,?,?)",
            (user_id, name, username, password)
        )
        con.commit()
        con.close()
        return True
    except:
        return False

def login(username, password):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT user_id FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    con.close()
    return row[0] if row else None

def get_user(user_id):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return None
    return {
        "user_id": row[0],
        "name": row[1],
        "username": row[2],
        "password": row[3],
        "language": row[4]
    }

def set_language(user_id, lang):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
    con.commit()
    con.close()
