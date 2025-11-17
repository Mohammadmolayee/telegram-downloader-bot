import os
import sqlite3
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
# توابع دیتابیس
# -------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(user_id, username, first_name, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        hashed_pw = hash_password(password)
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, hashed_pw, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def user_exists(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def check_login(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    hashed_pw = hash_password(password)
    cursor.execute('SELECT 1 FROM users WHERE username = ? AND password_hash = ?', (username, hashed_pw))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def save_download(user_id, platform, url, title, file_type):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO downloads (user_id, platform, url, title, file_type, downloaded_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, platform, url, title, file_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_downloads(user_id, limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT platform, title, file_type, downloaded_at
        FROM downloads WHERE user_id = ?
        ORDER BY downloaded_at DESC LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

# -------------------------------
# /start — خوش‌آمدگویی + "لینک بفرست" + دکمه منو
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 منو", callback_data='menu')],
    ]
    await update.message.reply_text(
        "سلام! به ربات دانلودر حرفه‌ای خوش اومدی 😊\n\n"
        "اینجا می‌تونی:\n"
        "📹 ویدیو و 🎵 اهنگ هر پلتفرمی دانلود کنی\n"
        "پشتیبانی از تمامی پلتفرم ها : یوتیوب,اینستاگرام,تیک‌تاک,توییتر,فیسبوک,ساندکلود,اسپاتیفای و....\n\n"
        "💡 برای دانلود، فقط لینک رو بفرست!\n"
        "🔧 برای خدمات بیشتر، دکمه 'منو' رو بزن 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -------------------------------
# دکمه "منو" — ۳ دکمه
# -------------------------------
async def menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("👤 ساخت حساب", callback_data='create_account')],
        [InlineKeyboardButton("🔐 ورود", callback_data='login')],
        [InlineKeyboardButton("❓ راهنما", callback_data='help')],
    ]
    await query.edit_message_text(
        "منو اصلی 🔧\n\n"
        "انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -------------------------------
# راهنما
# -------------------------------
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "راهنما ❓\n\n"
        "👤 **ساخت حساب**: نام + یوزرنیم (بدون @, مثل mohammad) + پسورد (۸-۱۲ حرف/عدد, مثل MyPass123)\n"
        "🔐 **ورود**: یوزرنیم و پسورد\n"
        "📱 **دانلود**: بعد از ورود، لینک اینستاگرام/یوتیوب بفرست\n"
        "📂 **دانلودهای من**: لیست اخیرت رو ببین\n\n"
        "💡 نکته: بدون حساب هم می‌تونی لینک بفرستی و دانلود کنی (بدون ذخیره)\n\n"
        "برای شروع، /start بزن!"
    )

# -------------------------------
# دکمه "ساخت حساب" — فرم ۳ فیلد
# -------------------------------
async def create_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_exists(user_id):
        await query.edit_message_text("شما قبلاً حساب دارید! 👤\n\nبرای ورود، دکمه 'ورود' رو بزن")
        return
    context.user_data.clear()
    context.user_data['step'] = 'first_name'
    context.user_data['user_id'] = user_id
    await query.edit_message_text("ساخت حساب 👤\n\nنام و نام خانوادگی رو بفرست (مثل محمد احمدی)")

async def get_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['first_name'] = text
    context.user_data['step'] = 'username'
    await update.message.reply_text("یوزرنیم رو بفرست (بدون @, حداقل ۳ حرف, مثل mohammad) 📝")

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith('@'): text = text[1:]
    if len(text) < 3:
        await update.message.reply_text("یوزرنیم کوتاهه! حداقل ۳ حرف (مثل mohammad)")
        return 'username'
    context.user_data['username'] = text
    context.user_data['step'] = 'password'
    await update.message.reply_text("پسورد رو بفرست (۸-۱۲ حرف/عدد, بدون فاصله, مثل MyPass123) 🔐")

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if len(text) < 8 or len(text) > 12 or not text.isalnum():
        await update.message.reply_text("پسورد نامعتبر! ۸-۱۲ حرف/عدد, بدون فاصله (مثل MyPass123)")
        return 'password'
    user_id = context.user_data['user_id']
    username = context.user_data['username']
    first_name = context.user_data['first_name']
    if create_user(user_id, username, first_name, text):
        await update.message.reply_text(
            "حساب با موفقیت ساخته شد! 🎉\n\n"
            "حالا برای ورود، /start بزن و 'ورود به حساب' رو انتخاب کن"
        )
    else:
        await update.message.reply_text("یوزرنیم تکراریه! از اول شروع کن (/start)")
    context.user_data.clear()
    return ConversationHandler.END

# -------------------------------
# دکمه "ورود" — فرم ۲ فیلد
# -------------------------------
async def login_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    context.user_data['step'] = 'username_login'
    await query.edit_message_text("ورود 🔐\n\nیوزرنیم رو بفرست 📝")

async def get_login_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith('@'): text = text[1:]
    context.user_data['username_login'] = text
    context.user_data['step'] = 'password_login'
    await update.message.reply_text("پسورد رو بفرست 🔐")

async def get_login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    username = context.user_data['username_login']
    if check_login(username, text):
        await update.message.reply_text(
            "ورود موفق! 🎉\n\n"
            "به پنل کاربریت خوش اومدی 👤\n"
            "می‌تونی هر چی می‌خوای دانلود کنی\n\n"
            "💡 برای دانلود، لینک رو بفرست\n"
            "🔧 برای خدمات بیشتر، /start بزن"
        )
    else:
        await update.message.reply_text("یوزرنیم یا پسورد اشتباه! 😔\nدوباره امتحان کن")
        context.user_data['step'] = 'username_login'
    context.user_data.clear()
    return ConversationHandler.END

# -------------------------------
# راهنما
# -------------------------------
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "راهنما ❓\n\n"
        "👤 **ساخت حساب**: نام + یوزرنیم (بدون @, مثل mohammad) + پسورد (۸-۱۲ حرف/عدد, مثل MyPass123)\n"
        "🔐 **ورود**: یوزرنیم و پسورد\n"
        "📱 **دانلود**: بعد از ورود، لینک اینستاگرام/یوتیوب بفرست\n"
        "📂 **دانلودهای من**: لیست اخیرت رو ببین\n\n"
        "💡 نکته: بدون حساب هم می‌تونی لینک بفرستی و دانلود کنی (بدون ذخیره)\n\n"
        "برای شروع، /start بزن!"
    )

# -------------------------------
# دانلود (بدون حساب هم کار می‌کنه)
# -------------------------------
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    url = update.message.text.strip()

    if not user_exists(user_id):
        await update.message.reply_text("لینک بفرست تا دانلود کنم! (بدون حساب هم می‌تونی دانلود کنی)")
        return

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
# اجرای ربات با Polling
# -------------------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("ربات دانلودر بدون ایمیل فعال شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
