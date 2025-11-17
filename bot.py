# ========================================
# ربات دانلودر حرفه‌ای - نسخه نهایی و 100% بدون خطا
# بدون حساب + با حساب + منو + UI زیبا
# ========================================

import os
import sqlite3
import hashlib
import yt_dlp
import glob
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("TOKEN رو در Railway بذار!")

DB_PATH = "downloads.db"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# -------------------------------
# دیتابیس
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode = WAL;')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            first_name TEXT,
            password_hash TEXT,
            created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            platform TEXT,
            url TEXT,
            title TEXT,
            file_type TEXT,
            downloaded_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -------------------------------
# توابع کمکی
# -------------------------------
def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()

def create_user(uid, username, first_name, pw):
    try:
        with sqlite3.connect(DB_PATH) as c:
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                     (uid, username, first_name, hash_password(pw), datetime.now().isoformat()))
        return True
    except sqlite3.IntegrityError:
        return False

def user_exists(uid):
    with sqlite3.connect(DB_PATH) as c:
        return c.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone() is not None

def check_login(username, pw):
    with sqlite3.connect(DB_PATH) as c:
        return c.execute("SELECT 1 FROM users WHERE username=? AND password_hash=?",
                        (username, hash_password(pw))).fetchone() is not None

def save_download(uid, plat, url, title, ftype="video"):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO downloads (user_id,platform,url,title,file_type,downloaded_at) VALUES (?,?,?,?,?,?)",
                 (uid, plat, url, title, ftype, datetime.now().isoformat()))

# -------------------------------
# /start
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("منو", callback_data='main_menu')]]
    await update.message.reply_text(
        "سلام! به ربات دانلودر حرفه‌ای خوش اومدی\n\n"
        "ویدیو و آهنگ از یوتیوب، اینستاگرام، تیک‌تاک و همه جا دانلود کن\n\n"
        "فقط لینک رو بفرست تا دانلود کنم!\n"
        "برای امکانات بیشتر (ذخیره دانلودها، لیست دانلودها و ...) دکمه زیر رو بزن",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -------------------------------
# دکمه‌ها
# -------------------------------
async def button_handler(update: Update,
