# ========================================
# ربات دانلودر - نسخه نهایی با بک‌آپ GitHub
# حجم نامحدود + دیتابیس دائمی
# ========================================

import os
import sqlite3
import hashlib
import yt_dlp
import glob
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests  # برای بک‌آپ به GitHub

TOKEN = os.getenv("TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # اختیاری
GITHUB_REPO = "Mohammadmolayee/telegram-downloader-bot"  # مخزن تو

DB_PATH = "downloads.db"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

MAX_GUEST_DOWNLOADS_PER_DAY = 10

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                first_name TEXT,
                password_hash TEXT,
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
                downloaded_at TEXT
            )
        ''')

init_db()

def backup_to_github():
    if not GITHUB_TOKEN:
        return
    try:
        with open(DB_PATH, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        data = {"message": "Auto backup downloads.db", "content": content}
        requests.put(f"https://api.github.com/repos/{GITHUB_REPO}/contents/downloads.db", headers=headers, json=data)
    except:
        pass  # اگر خطا داد، مهم نیست

# هر ۳۰ دقیقه بک‌آپ بگیر (اختیاری)
import threading
threading.Timer(1800.0, backup_to_github).start()

def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()

def create_user(uid, username, name, pw):
    try:
        with sqlite3.connect(DB_PATH) as c:
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)",
                     (uid, username, name, hash_password(pw), datetime.now().isoformat()))
        return True
    except sqlite3.IntegrityError:
        return False

def user_exists(uid):
    with sqlite3.connect(DB_PATH) as c:
        return c.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone() is not None

def save_download(uid, platform, url, title):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO downloads (user_id,platform,url,title,downloaded_at) VALUES (?,?,?,?,?)",
                 (uid, platform, url, title, datetime.now().isoformat()))

def get_today_count(uid):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as c:
        return c.execute("SELECT COUNT(*) FROM downloads WHERE user_id=? AND substr(downloaded_at,1,10)=?", (uid, today)).fetchone()[0]

def get_total_count(uid):
    with sqlite3.connect(DB_PATH) as c:
        return c.execute("SELECT COUNT(*) FROM downloads WHERE user_id=?", (uid,)).fetchone()[0]

def get_recent_downloads(uid, limit=10):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("SELECT platform, title, downloaded_at FROM downloads WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit))
        return c.fetchall()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("منو", callback_data="show_menu")]]
    await update.message.reply_text(
        "سلام! به ربات دانلودر حرفه‌ای خوش اومدی\n\n"
        "لینک ویدیو یا آهنگ رو بفرست تا برات دانلود کنم!\n"
        "برای امکانات بیشتر (تاریخچه، آمار، نامحدود) دکمه منو رو بزن",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# نمایش منو
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if user_exists(uid):
        kb = [
            [InlineKeyboardButton("📁 دانلودهای من", callback_data="my_downloads")],
            [InlineKeyboardButton("📊 آمار من", callback_data="my_stats")],
            [InlineKeyboardButton("🚪 خروج از حساب", callback_data="logout")],
            [InlineKeyboardButton("❓ راهنما", callback_data="help")],
        ]
        text = "به پنل کاربریت خوش اومدی"
    else:
        kb = [
            [InlineKeyboardButton("👤 ساخت حساب", callback_data="register")],
            [InlineKeyboardButton("❓ راهنما", callback_data="help")],
        ]
        text = "برای ذخیره تاریخچه و نامحدود شدن، حساب بساز"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

# دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if data == "my_downloads":
        downloads = get_recent_downloads(uid, 10)
        if not downloads:
            text = "هنوز دانلودی نداری!"
        else:
            text = "آخرین دانلودها:\n\n"
            for plat, title, dt in downloads:
                time = dt[11:16] if "T" in dt else "نامشخص"
                text += f"• {plat} | {time}\n  {title}\n\n"
        await query.edit_message_text(text + "\n/start بزن برای برگشت")

    elif data == "my_stats":
        total = get_total_count(uid)
        today = get_today_count(uid)
        await query.edit_message_text(
            f"آمار دانلودت\n\n"
            f"کل: {total}\n"
            f"امروز: {today}\n"
            f"وضعیت: نامحدود\n\n"
            f"/start بزن برای برگشت"
        )

    elif data == "logout":
        await query.edit_message_text("از حساب خارج شدی!\n/start بزن")

    elif data == "register":
        if user_exists(uid):
            await query.edit_message_text("شما قبلاً حساب دارید!")
            return
        context.user_data["step"] = "reg_name"
        await query.edit_message_text("نام و نام خانوادگی رو بفرست")

    elif data == "help":
        await query.edit_message_text(
            "راهنما\n\n"
            "• بدون حساب: ۱۰ دانلود در روز\n"
            "• با حساب: نامحدود + تاریخچه کامل\n"
            "• ساخت حساب → نام → یوزرنیم → پسورد (۸-۱۲ حرف/عدد)\n"
            "• هر وقت خواستی /start بزن!"
        )

# پیام‌ها
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()

    if any(s in text for s in ["youtube.com", "youtu.be", "instagram.com", "tiktok.com", "twitter.com", "x.com"]):
        if not user_exists(uid):
            if get_today_count(uid) >= MAX_GUEST_DOWNLOADS_PER_DAY:
                await update.message.reply_text(f"امروز {MAX_GUEST_DOWNLOADS_PER_DAY} تا دانلود کردی!\nحساب بساز تا نامحدود بشه")
                return
        await download_video(update, context, text, uid)
        return

    step = context.user_data.get("step")
    if not step:
        await update.message.reply_text("لینک بفرست یا از منو استفاده کن")
        return

    if step == "reg_name":
        context.user_data["name"] = text
        context.user_data["step"] = "reg_user"
        await update.message.reply_text("یوزرنیم رو بفرست (بدون @)")

    elif step == "reg_user":
        username = text.lstrip("@").strip()
        if len(username) < 3:
            await update.message.reply_text("یوزرنیم کوتاهه!")
            return
        context.user_data["username"] = username
        context.user_data["step"] = "reg_pass"
        await update.message.reply_text("پسورد بفرست (۸-۱۲ حرف و عدد)")

    elif step == "reg_pass":
        if not (8 <= len(text) <= 12 and text.isalnum()):
            await update.message.reply_text("پسورد باید ۸-۱۲ حرف و عدد باشه!")
            return
        if create_user(uid, context.user_data["username"], context.user_data["name"], text):
            await update.message.reply_text("حساب ساخته شد! /start بزن و از امکانات لذت ببر")
        else:
            await update.message.reply_text("این یوزرنیم قبلاً استفاده شده!")
        context.user_data.clear()

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, uid: int):
    msg = await update.message.reply_text("در حال دانلود...")
    plat = "YouTube" if "youtube" in url or "youtu.be" in url else "Instagram/TikTok"

    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file = glob.glob(f'{DOWNLOAD_FOLDER}/{info.get("id")}.*')[0]
            title = info.get("title", "ویدیو")[:100]

        with open(file, "rb") as v:
            await update.message.reply_video(v, caption=title)

        save_download(uid, plat, url, title)
        os.remove(file)
        await msg.delete()
    except Exception as e:
        await msg.edit_text("دانلود نشد! لینک رو چک کن")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_menu, pattern="^show_menu$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("ربات دانلودر - نسخه نهایی فعال شد")
    app.run_polling()

if __name__ == "__main__":
    main()
