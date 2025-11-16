# ========================================
# ربات دانلودر حرفه‌ای - نسخه کامل
# حساب کاربری + فرم ثبت‌نام + تأیید ایمیل + ورود
# فقط کپی کن و در Railway آپلود کن
# ========================================

import os
import sqlite3
import random
import base64
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# -------------------------------
# تنظیمات (از Railway Variables)
# -------------------------------
TOKEN = os.getenv('TOKEN')
GMAIL_CLIENT_ID = os.getenv('GMAIL_CLIENT_ID')
GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET')
GMAIL_REFRESH_TOKEN = os.getenv('GMAIL_REFRESH_TOKEN')
GMAIL_SENDER = os.getenv('GMAIL_SENDER')

if not all([TOKEN, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, GMAIL_SENDER]):
    raise ValueError("متغیرهای Gmail رو در Railway Variables بذار!")

DB_PATH = "downloads.db"

# -------------------------------
# دیتابیس — ساخت جداول
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            first_name TEXT,
            email TEXT,
            password TEXT,
            verified BOOLEAN DEFAULT False,
            verification_code TEXT,
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
# ارسال ایمیل با Gmail API
# -------------------------------
def send_email(to_email, code):
    credentials = Credentials(
        token=None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET
    )
    service = build('gmail', 'v1', credentials=credentials)
    message = MIMEText(f"کد تأیید حساب شما:\n\n{code}\n\nاین کد ۱۰ دقیقه اعتبار دارد.")
    message['to'] = to_email
    message['from'] = GMAIL_SENDER
    message['subject'] = "کد تأیید ربات دانلودر"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        service.users().messages().send(userId="me", body={'raw': raw}).execute()
    except HttpError as e:
        print(f"خطا در ارسال ایمیل: {e}")

# -------------------------------
# توابع دیتابیس
# -------------------------------
def create_user(user_id, username, first_name, email, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, username, first_name, email, password, verified, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, email, password, True, datetime.now().isoformat()))
    conn.commit()
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
    cursor.execute('SELECT 1 FROM users WHERE username = ? AND password = ?', (username, password))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

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
# دستور /start — منو
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ساخت حساب کاربری", callback_data='create_account')],
        [InlineKeyboardButton("ورود به حساب", callback_data='login')],
        [InlineKeyboardButton("دانلودهای من", callback_data='my_downloads')],
        [InlineKeyboardButton("راهنما", callback_data='help')],
    ]
    await update.message.reply_text(
        "سلام! به ربات دانلودر حرفه‌ای خوش اومدی\n"
        "اینجا می‌تونی:\n"
        "ویدیو و اهنگ هر پلتفرمی دانلود کنی\n"
        "پشتیبانی از تمامی پلتفرم ها : یوتیوب,اینستاگرام,تیک‌تاک,توییتر,فیسبوک,ساندکلود,اسپاتیفای و....\n"
        "فقط لینک رو بفرست، بقیه‌ش با ماست!",
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

    if data == 'create_account':
        if user_exists(user_id):
            await query.edit_message_text("شما قبلاً حساب دارید!")
            return
        context.user_data['step'] = 'first_name'
        context.user_data['user_id'] = user_id
        await query.edit_message_text("نام و نام خانوادگی رو بفرست")

    elif data == 'login':
        context.user_data['step'] = 'username_login'
        await query.edit_message_text("یوزرنیم رو بفرست")

    elif data == 'my_downloads':
        if not user_exists(user_id):
            await query.edit_message_text("اول حساب بساز یا وارد شو!")
            return
        downloads = get_user_downloads(user_id)
        if not downloads:
            await query.edit_message_text("هنوز هیچ دانلودی نداری!")
            return
        text = "آخرین دانلودهای تو:\n\n"
        for plat, title, ftype, time in downloads:
            icon = "ویدیو" if ftype == "video" else "آهنگ"
            text += f"{icon} {plat}: {title}\n   {time.split('T')[0]}\n\n"
        await query.edit_message_text(text)

    elif data == 'help':
        await query.edit_message_text(
            "راهنما:\n"
            "1. حساب بساز\n"
            "2. کد تأیید رو از ایمیل وارد کن\n"
            "3. لینک بفرست و دانلود کن"
        )

# -------------------------------
# پیام‌ها (فرم)
# -------------------------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    step = context.user_data.get('step')

    if not step:
        await update.message.reply_text("از منو شروع کن!")
        return

    # --- ثبت‌نام ---
    if step == 'first_name':
        context.user_data['first_name'] = text
        context.user_data['step'] = 'username'
        await update.message.reply_text("یوزرنیم رو بفرست (مثل @mohammad)")

    elif step == 'username':
        if text.startswith('@'): text = text[1:]
        context.user_data['username'] = text
        context.user_data['step'] = 'password'
        await update.message.reply_text("پسورد رو بفرست (حداقل ۶ حرف)")

    elif step == 'password':
        if len(text) < 6:
            await update.message.reply_text("پسورد کوتاهه! حداقل ۶ حرف")
            return
        context.user_data['password'] = text
        context.user_data['step'] = 'email'
        await update.message.reply_text("ایمیل (جیمیل) رو بفرست")

    elif step == 'email':
        if not text.endswith('@gmail.com'):
            await update.message.reply_text("فقط جیمیل قبول می‌کنم!")
            return
        context.user_data['email'] = text
        code = str(random.randint(100000, 999999))
        context.user_data['verification_code'] = code
        context.user_data['step'] = 'verify_code'
        send_email(text, code)
        await update.message.reply_text("کد تأیید به ایمیلت فرستاده شد. کد ۶ رقمی رو بفرست")

    elif step == 'verify_code':
        if text == context.user_data.get('verification_code'):
            create_user(
                user_id=context.user_data['user_id'],
                username=context.user_data['username'],
                first_name=context.user_data['first_name'],
                email=context.user_data['email'],
                password=context.user_data['password']
            )
            await update.message.reply_text("حساب با موفقیت ساخته شد!")
            context.user_data.clear()
        else:
            await update.message.reply_text("کد اشتباه! دوباره بفرست")

    # --- ورود ---
    elif step == 'username_login':
        context.user_data['username_login'] = text
        context.user_data['step'] = 'password_login'
        await update.message.reply_text("پسورد رو بفرست")

    elif step == 'password_login':
        if check_login(context.user_data['username_login'], text):
            await update.message.reply_text("ورود موفق!")
            context.user_data.clear()
        else:
            await update.message.reply_text("یوزرنیم یا پسورد اشتباه!")
            context.user_data['step'] = 'username_login'

# -------------------------------
# اجرای ربات
# -------------------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("ربات دانلودر با حساب کاربری فعال شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
