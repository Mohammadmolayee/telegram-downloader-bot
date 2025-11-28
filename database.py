import sqlite3

DB = "users.db"

def connect():
    return sqlite3.connect(DB)

def init_db():
    con = connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        username TEXT,
        password TEXT,
        language TEXT DEFAULT 'fa'
    )
    """)
    con.commit()
    con.close()

def user_exists(user_id):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    data = cur.fetchone()
    con.close()
    return bool(data)

def create_user(user_id, name, username, password):
    con = connect()
    cur = con.cursor()

    try:
        cur.execute("""
            INSERT INTO users(user_id, name, username, password)
            VALUES (?, ?, ?, ?)
        """, (user_id, name, username, password))
        con.commit()
        return True
    except:
        return False
    finally:
        con.close()

def login(username, password):
    con = connect()
    cur = con.cursor()
    cur.execute("""
    SELECT user_id FROM users WHERE username=? AND password=?
    """, (username, password))
    data = cur.fetchone()
    con.close()
    return data[0] if data else None

def get_user(uid):
    con = connect()
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()
    con.close()
    if not row:
        return None

    return {
        "user_id": row[0],
        "name": row[1],
        "username": row[2],
        "password": row[3],
        "language": row[4],
    }

def set_language(uid, lang):
    con = connect()
    cur = con.cursor()
    cur.execute("UPDATE users SET language=? WHERE user_id=?", (lang, uid))
    con.commit()
    con.close()
