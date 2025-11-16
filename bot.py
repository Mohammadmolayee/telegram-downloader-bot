# ========================================
# ربات دانلودر حرفه‌ای - نسخه نهایی با Polling
# بدون ایمیل + بهینه + پایدار
# ========================================

import os
import sqlite3
import yt_dlp
import glob
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# -------------------------------
# تنظیمات
# -------------------------------
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("TOKEN رو در Railway بذار!")

DB_PATH = "/tmp/downloads.db"
DOWNLOAD_FOLDER = "/tmp/downloads"
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
            password TEXT,
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
# توابع دیتابیس
# -------------------------------
def create_user(user_id, username, first_name, password):
    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute('INSERT INTO users (user_id, username, first_name, password, created_at) VALUES (?, ?, ?, ?, ?)',
                        (user_id, username, first_name, password, datetime.now().isoformat()))
            return True
        except sqlite3.IntegrityError:
            return False

def user_exists(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,)).fetchone() is not None

def check_login(username, password):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute('SELECT 1 FROM users WHERE username = ? AND password = ?', (username, password)).fetchone() is not None

def save_download(user_id, platform, url, title, file_type):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('INSERT INTO downloads (user_id, platform, url, title, file_type, downloaded_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (user_id, platform, url, title, file_type, datetime.now().isoformat()))

def get_user_downloads(user_id, limit=5):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute('SELECT platform, title, file_type, downloaded_at FROM downloads WHERE user_id = ? ORDER BY downloaded_at DESC LIMIT ?', (user_id, limit)).fetchall()

# -------------------------------
# /start
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ساخت حساب", callback_data='create')],
        [InlineKeyboardButton("ورود", callback_data='login')],
        [InlineKeyboardButton("دانلودها", callback_data='downloads')],
        [InlineKeyboardButton("راهنما", callback_data='help')],
    ]
    await update.message.reply_text(
        "به ربات دانلودر حرفه‌ای خوش اومدی!\n"
        "ویدیو و آهنگ از هر پلتفرمی دانلود کن\n"
        "فقط لینک رو بفرست!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -------------------------------
# دکمه‌ها
# -------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'create':
        if user_exists(user_id):
            await query.edit_message_text("شما قبلاً حساب دارید!")
            return
        context.user_data.update({'step': 'first_name', 'user_id': user_id})
        await query.edit_message_text("نام و نام خانوادگی رو بفرست")

    elif data == 'login':
        context.user_data.update({'step': 'username_login'})
        await query.edit_message_text("یوزرنیم رو بفرست")

    elif data == 'downloads':
        if not user_exists(user_id):
            await query.edit_message_text("اول حساب بساز یا وارد شو!")
            return
        downloads = get_user_downloads(user_id)
        if not downloads:
            await query.edit_message_text("هنوز دانلودی نداری!")
            return
        text = "آخرین دانلودها:\n\n"
        for plat, title, ftype, time in downloads:
            icon = "ویدیو" if ftype == "video" else "آهنگ"
            text += f"{icon} {plat}: {title}\n   {time.split('T')[0]}\n\n"
        await query.edit_message_text(text)

    elif data == 'help':
        await query.edit_message_text(
            "راهنما:\n"
            "1. حساب بساز (نام + یوزرنیم + پسورد)\n"
            "2. وارد شو\n"
            "3. لینک اینستاگرام/یوتیوب بفرست"
        )

# -------------------------------
# پیام‌ها
# -------------------------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    step = context.user_data.get('step')

    if not step and any(p in text for p in ["instagram.com", "youtube.com", "youtu.be"]) and user_exists(user_id):
        await download_video(update, context, text, user_id)
        return

    if not step:
        await update.message.reply_text("از منو شروع کن!")
        return

    if step == 'first_name':
        context.user_data.update({'first_name': text, 'step': 'username'})
        await update.message.reply_text("یوزرنیم رو بفرست (مثل @mohammad)")

    elif step == 'username':
        username = text.lstrip('@')
        context.user_data.update({'username': username, 'step': 'password'})
        await update.message.reply_text("پسورد رو بفرست (حداقل ۶ حرف)")

    elif step == 'password':
        if len(text) < 6:
            await update.message.reply_text("پسورد کوتاهه! حداقل ۶ حرف")
            return
        if create_user(user_id, context.user_data['username'], context.user_data['first_name'], text):
            await update.message.reply_text("حساب ساخته شد! حالا لینک بفرست")
        else:
            await update.message.reply_text("یوزرنیم تکراریه!")
            context.user_data['step'] = 'username'
        context.user_data.clear()

    elif step == 'username_login':
        context.user_data.update({'username_login': text, 'step': 'password_login'})
        await update.message.reply_text("پسورد رو بفرست")

    elif step == 'password_login':
        if check_login(context.user_data['username_login'], text):
            await update.message.reply_text("ورود موفق! لینک بفرست")
            context.user_data.clear()
        else:
            await update.message.reply_text("یوزرنیم یا پسورد اشتباه!")
            context.user_data['step'] = 'username_login'

# -------------------------------
# دانلود ویدیو
# -------------------------------
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, user_id: int):
    msg = await update.message.reply_text("در حال دانلود... ⏳")
    platform = "YouTube" if "youtube" in url or "youtu.be" in url else "Instagram"
    
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'merge_output_format': 'mp4',
            'retries': 3,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = glob.glob(f"{DOWNLOAD_FOLDER}/{info.get('id')}.*")[0]
            title = info.get('title', 'ویدیو')

        with open(file_path, 'rb') as f:
            await update.message.reply_video(f, caption=f"{platform}: {title}")

        save_download(user_id, platform, url, title, "video")
        os.remove(file_path)
        await msg.delete()

    except Exception as e:
        await msg.edit_text("خطا: دانلود نشد!")

# -------------------------------
# اجرای ربات با Polling (پایدار)
# -------------------------------
def main():
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("ربات با Polling فعال شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
