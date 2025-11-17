# ========================================
# ربات دانلودر حرفه‌ای - نسخه نهایی با همه امکانات
# بدون حساب دانلود کن + با حساب (منو + دانلودها + خروج + آمار + محدودیت)
# ========================================

import os
import sqlite3
import yt_dlp
import glob
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN رو در Railway بذار!")

DB_PATH = "downloads.db"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# محدودیت دانلود برای کاربران بدون لاگین (۱۰ تا در روز)
MAX_DOWNLOADS_PER_DAY = 10

# -------------------------------
# دیتابیس
# -------------------------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                first_name TEXT,
                password_hash TEXT,
                created_at TEXT
            )
        ''')
        conn.execute('''
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

# -------------------------------
# توابع کمکی
# -------------------------------
def hash_password(pw): return hashlib.sha256(pw.encode()).hexdigest()

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

def get_user_downloads_count(uid):
    with sqlite3.connect(DB_PATH) as c:
        return c.execute("SELECT COUNT(*) FROM downloads WHERE user_id=?", (uid,)).fetchone()[0]

def get_today_downloads_count(uid):
    today = datetime.now().date()
    with sqlite3.connect(DB_PATH) as c:
        count = c.execute('''
            SELECT COUNT(*) FROM downloads 
            WHERE user_id=? AND date(downloaded_at)=?
        ''', (uid, today)).fetchone()[0]
        return count

# -------------------------------
# /start
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("منو", callback_data="main_menu")]]
    await update.message.reply_text(
        "سلام! به ربات دانلودر حرفه‌ای خوش اومدی\n\n"
        "ویدیو و آهنگ از یوتیوب، اینستاگرام، تیک‌تاک و همه جا دانلود کن\n\n"
        "فقط لینک رو بفرست تا برات دانلود کنم!\n"
        "برای امکانات بیشتر (ذخیره دانلودها، آمار، ...) دکمه زیر رو بزن",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -------------------------------
# منو اصلی
# -------------------------------
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    kb = [
        [InlineKeyboardButton("ساخت حساب", callback_data="create")],
        [InlineKeyboardButton("ورود", callback_data="login")],
    ]
    if user_exists(user_id):
        kb += [
            [InlineKeyboardButton("دانلودهای من", callback_data="my_downloads")],
            [InlineKeyboardButton("آمار من", callback_data="stats")],
            [InlineKeyboardButton("خروج از حساب", callback_data="logout")],
        ]
    kb += [[InlineKeyboardButton("راهنما", callback_data="help")]]

    await query.edit_message_text("منو اصلی\nانتخاب کن:", reply_markup=InlineKeyboardMarkup(kb))

# -------------------------------
# ساخت حساب
# -------------------------------
async def create_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if user_exists(query.from_user.id):
        await query.edit_message_text("شما قبلاً حساب دارید!")
        return
    context.user_data.update({'step': 'reg_name', 'user_id': query.from_user.id})
    await query.edit_message_text("نام و نام خانوادگی رو بفرست")

# -------------------------------
# ورود
# -------------------------------
async def login_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.update({'step': 'login_user'})
    await query.edit_message_text("یوزرنیم رو بفرست")

# -------------------------------
# دانلودهای من
# -------------------------------
async def my_downloads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    downloads = get_user_downloads_count(uid)
    today = get_today_downloads_count(uid)
    await query.edit_message_text(
        f"دانلودهای من\n\n"
        f"کل دانلودها: {downloads}\n"
        f"امروز: {today}\n\n"
        f"برای برگشت، /start بزن"
    )

# -------------------------------
# آمار من
# -------------------------------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    total = get_user_downloads_count(uid)
    today = get_today_downloads_count(uid)
    await query.edit_message_text(
        f"آمار حساب شما\n\n"
        f"کل دانلودها: {total}\n"
        f"دانلود امروز: {today}\n"
        f"محدودیت روزانه: {MAX_DOWNLOADS_PER_DAY}\n\n"
        f"برای برگشت، /start بزن"
    )

# -------------------------------
# خروج از حساب
# -------------------------------
async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("از حساب خارج شدی!\n\nبرای ورود دوباره، /start بزن")

# -------------------------------
# راهنما
# -------------------------------
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "راهنما\n\n"
        "• بدون حساب هم می‌تونی لینک بفرستی و دانلود کنی\n"
        "• با حساب: دانلودها ذخیره می‌شن + آمار + محدودیت\n"
        "• ساخت حساب: نام + یوزرنیم + پسورد\n"
        "• ورود: یوزرنیم + پسورد\n"
        "• دانلود: لینک اینستاگرام/یوتیوب بفرست\n\n"
        "هر سوالی داشتی /start بزن!"
    )

# -------------------------------
# پیام‌ها و فرم‌ها
# -------------------------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    step = context.user_data.get('step')

    # دانلود (با یا بدون حساب)
    if any(x in text for x in ["youtube.com", "youtu.be", "instagram.com", "tiktok.com", "twitter.com", "x.com"]):
        # اگر لاگین نشده و محدودیت روزانه پر شده
        if not user_exists(user_id):
            today_count = get_today_downloads_count(user_id)
            if today_count >= MAX_DOWNLOADS_PER_DAY:
                await update.message.reply_text(f"محدودیت روزانه: {MAX_DOWNLOADS_PER_DAY} دانلود\nبرای دانلود بیشتر، حساب بساز!")
                return
        await download_video(update, context, text, user_id)
        return

    if not step:
        await update.message.reply_text("لطفاً لینک بفرست یا از منو استفاده کن")
        return

    # ثبت‌نام
    if step == 'reg_name':
        context.user_data['name'] = text
        context.user_data['step'] = 'reg_user'
        await update.message.reply_text("یوزرنیم رو بفرست (بدون @)")

    elif step == 'reg_user':
        username = text.lstrip('@')
        if len(username) < 3:
            await update.message.reply_text("یوزرنیم کوتاهه!")
            return
        context.user_data['username'] = username
        context.user_data['step'] = 'reg_pass'
        await update.message.reply_text("پسورد بفرست (۸-۱۲ حرف/عدد)")

    elif step == 'reg_pass':
        if not (8 <= len(text) <= 12 and text.isalnum()):
            await update.message.reply_text("پسورد باید ۸-۱۲ حرف/عدد باشه!")
            return
        if create_user(user_id, context.user_data['username'], context.user_data['name'], text):
            await update.message.reply_text("حساب ساخته شد! حالا /start بزن و ورود رو بزن")
        else:
            await update.message.reply_text("یوزرنیم تکراریه!")
        context.user_data.clear()

    # ورود
    elif step == 'login_user':
        context.user_data['login_user'] = text.lstrip('@')
        context.user_data['step'] = 'login_pass'
        await update.message.reply_text("پسورد رو بفرست")

    elif step == 'login_pass':
        if check_login(context.user_data['login_user'], text):
            await update.message.reply_text("ورود موفق! حالا لینک بفرست")
        else:
            await update.message.reply_text("یوزرنیم یا پسورد اشتباه!")
        context.user_data.clear()

# -------------------------------
# دانلود ویدیو
# -------------------------------
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, user_id: int):
    msg = await update.message.reply_text("در حال دانلود...")
    platform = "YouTube" if "youtube" in url or "youtu.be" in url else "Instagram/TikTok"

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
            file_path = glob.glob(f"{DOWNLOAD_FOLDER}/{info.get('id')}.*")[0]
            title = info.get('title', 'ویدیو')

        with open(file_path, 'rb') as video:
            await update.message.reply_video(video, caption=f"{platform}: {title}")

        if user_exists(user_id):
            save_download(user_id, platform, url, title)

        os.remove(file_path)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"خطا: {str(e)[:100]}")

# -------------------------------
# اجرا
# -------------------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("ربات دانلودر با همه امکانات فعال شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
