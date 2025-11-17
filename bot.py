# ========================================
# ربات دانلودر حرفه‌ای - نسخه نهایی و 100% کارکردن
# بدون حساب دانلود کن + با حساب امکانات بیشتر
# ========================================

import os
import sqlite3
import hashlib
import yt_dlp
import glob
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# توکن
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN رو در Railway بذار!")

# پوشه و دیتابیس
DB_PATH = "downloads.db"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# دیتابیس
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                first_name TEXT,
                password_hash TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT,
                url TEXT,
                title TEXT,
                downloaded_at TEXT
            )
        """)

init_db()

# هش پسورد
def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()

# توابع کاربر
def create_user(uid, username, name, pw):
    try:
        with sqlite3.connect(DB_PATH) as c:
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                     (uid, username, name, hash_password(pw), datetime.now().isoformat()))
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

def save_download(uid, plat, url, title):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO downloads (user_id,platform,url,title,downloaded_at) VALUES (?,?,?,?,?)",
                 (uid, plat, url, title, datetime.now().isoformat()))

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("منو", callback_data="main_menu")]]
    await update.message.reply_text(
        "سلام! به ربات دانلودر حرفه‌ای خوش اومدی\n\n"
        "ویدیو و آهنگ از یوتیوب، اینستاگرام، تیک‌تاک و همه جا دانلود کن\n\n"
        "فقط لینک رو بفرست تا برات دانلود کنم!\n"
        "برای ذخیره دانلودها و امکانات بیشتر، دکمه زیر رو بزن",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "main_menu":
        kb = [
            [InlineKeyboardButton("ساخت حساب", callback_data="create")],
            [InlineKeyboardButton("ورود", callback_data="login")],
            [InlineKeyboardButton("راهنما", callback_data="help")],
        ]
        await query.edit_message_text("منو اصلی\nانتخاب کن:", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data == "create":
        if user_exists(uid):
            await query.edit_message_text("شما قبلاً حساب دارید!")
            return
        context.user_data["step"] = "reg_name"
        await query.edit_message_text("نام و نام خانوادگی رو بفرست")

    elif query.data == "login":
        context.user_data["step"] = "login_user"
        await query.edit_message_text("یوزرنیم رو بفرست")

    elif query.data == "help":
        await query.edit_message_text(
            "راهنما\n\n"
            "ساخت حساب:\n"
            "• یوزرنیم: بدون @، حداقل ۳ حرف (مثل ali123)\n"
            "• پسورد: ۸-۱۲ حرف و عدد (مثل Pass1234)\n\n"
            "دانلود:\n"
            "• بدون حساب هم می‌تونی لینک بفرستی\n"
            "• با حساب، دانلودها ذخیره می‌شن\n\n"
            "هر سوالی داشتی /start بزن!"
        )

# پیام‌ها
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()
    step = context.user_data.get("step")

    # دانلود بدون حساب
    if not step and any(x in text for x in ["youtube.com", "youtu.be", "instagram.com", "tiktok.com", "twitter.com", "x.com"]):
        await download_video(update, context, text, uid)
        return

    # ثبت‌نام
    if step == "reg_name":
        context.user_data["name"] = text
        context.user_data["step"] = "reg_user"
        await update.message.reply_text("یوزرنیم رو بفرست (بدون @)")

    elif step == "reg_user":
        username = text.lstrip("@")
        if len(username) < 3:
            await update.message.reply_text("یوزرنیم باید حداقل ۳ حرف باشه!")
            return
        context.user_data["username"] = username
        context.user_data["step"] = "reg_pass"
        await update.message.reply_text("پسورد بفرست (۸-۱۲ حرف/عدد)")

    elif step == "reg_pass":
        if not (8 <= len(text) <= 12 and text.isalnum()):
            await update.message.reply_text("پسورد باید ۸-۱۲ حرف و عدد باشه!")
            return
        if create_user(uid, context.user_data["username"], context.user_data["name"], text):
            await update.message.reply_text("حساب ساخته شد!\nحالا /start بزن و ورود رو انتخاب کن")
        else:
            await update.message.reply_text("یوزرنیم تکراریه!")
        context.user_data.clear()

    # ورود
    elif step == "login_user":
        context.user_data["login_user"] = text.lstrip("@")
        context.user_data["step"] = "login_pass"
        await update.message.reply_text("پسورد رو بفرست")

    elif step == "login_pass":
        if check_login(context.user_data["login_user"], text):
            await update.message.reply_text("ورود موفق!\nاز این به بعد دانلودها ذخیره می‌شن")
        else:
            await update.message.reply_text("یوزرنیم یا پسورد اشتباه!")
        context.user_data.clear()

    else:
        await update.message.reply_text("لطفاً لینک بفرست یا از منو استفاده کن")

# دانلود
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, uid: int):
    msg = await update.message.reply_text("در حال دانلود...")
    plat = "YouTube" if "youtube" in url or "youtu.be" in url else "Instagram/TikTok"

    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'merge_output_format': 'mp4',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file = glob.glob(f"{DOWNLOAD_FOLDER}/{info.get('id')}.*")[0]
            title = info.get("title", "ویدیو")

        with open(file, "rb") as video:
            await update.message.reply_video(video, caption=f"{plat}: {title}")

        if user_exists(uid):
            save_download(uid, plat, url, title)

        os.remove(file)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"خطا: {str(e)[:100]}")

# اجرا
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("ربات دانلودر فعال شد...")
    app.run_polling()

if __name__ == "__main__":
    main()
