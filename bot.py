# ========================================
# ربات دانلودر حرفه‌ای - با حساب کاربری + تأیید ایمیل
# ========================================

import os
import random
import smtplib
from email.mime.text import MIMEText
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- تنظیمات ---
TOKEN = os.getenv('TOKEN')
GMAIL_CLIENT_ID = os.getenv('GMAIL_CLIENT_ID')
GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET')
GMAIL_REFRESH_TOKEN = os.getenv('GMAIL_REFRESH_TOKEN')
GMAIL_SENDER = os.getenv('GMAIL_SENDER')

if not all([TOKEN, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, GMAIL_SENDER]):
    raise ValueError("متغیرها رو در Railway بذار!")

# --- دیتابیس (SQLite) ---
DB_PATH = "downloads.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            password TEXT,
            verified BOOLEAN DEFAULT False,
            verification_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- ارسال ایمیل با Gmail API ---
def send_email(to_email, code):
    credentials = Credentials(
        token=None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        id_token=None,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET
    )

    service = build('gmail', 'v1', credentials=credentials)

    message = MIMEText(f"کد تأیید حساب شما: {code}")
    message['to'] = to_email
    message['from'] = GMAIL_SENDER
    message['subject'] = "کد تأیید ربات دانلودر"

    create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    try:
        service.users().messages().send(userId="me", body=create_message).execute()
    except HttpError as error:
        print(f'خطا در ارسال ایمیل: {error}')

# --- دستور /start — منو اصلی ---
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

# --- هندلر دکمه‌ها و فرم‌ها ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'create_account':
        context.user_data['step'] = 'first_name'
        await query.edit_message_text("نام و نام خانوادگی رو بفرست")

    elif data == 'login':
        context.user_data['step'] = 'username_login'
        await query.edit_message_text("یوزرنیم رو بفرست")

    elif data == 'my_downloads':
        if not user_exists(user_id):
            await query.edit_message_text("اول حساب بساز یا وارد شو!")
            return
        
        downloads = get_user_downloads(user_id, limit=5)
        if not downloads:
            await query.edit_message_text("هنوز هیچ دانلودی نداری!")
            return

        text = "آخرین دانلودهای تو:\n\n"
        for plat, title, ftype, time in downloads:
            icon = "ویدیو" if ftype == "video" else "آهنگ"
            text += f"{icon} {plat}: {title}\n   {time}\n\n"
        
        await query.edit_message_text(text)

    elif data == 'help':
        await query.edit_message_text(
            "راهنما:\n"
            "1. حساب بساز (نام, یوزرنیم, پسورد, ایمیل)\n"
            "2. کد تأیید رو از ایمیل وارد کن\n"
            "3. لینک بفرست و دانلود کن\n"
            "4. دانلودها در حسابت ذخیره می‌شن"
        )

# --- هندلر پیام‌ها (فرم ثبت‌نام و ورود) ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    step = context.user_data.get('step', None)

    if step == 'first_name':
        context.user_data['first_name'] = text
        context.user_data['step'] = 'username'
        await update.message.reply_text("یوزرنیم رو بفرست (مثل @user)")

    elif step == 'username':
        context.user_data['username'] = text
        context.user_data['step'] = 'password'
        await update.message.reply_text("پسورد رو بفرست (حداقل ۶ حرف)")

    elif step == 'password':
        context.user_data['password'] = text
        context.user_data['step'] = 'email'
        await update.message.reply_text("ایمیل (جیمیل) رو بفرست")

    elif step == 'email':
        context.user_data['email'] = text
        code = str(random.randint(100000, 999999))
        context.user_data['verification_code'] = code
        context.user_data['step'] = 'verify_code'
        send_email(text, code)
        await update.message.reply_text("کد تأیید به ایمیلت فرستاده شد. کد رو بفرست")

    elif step = 'verify_code':
        if text == context.user_data['verification_code']:
            create_user(user_id, context.user_data['username'], context.user_data['first_name'], context.user_data['email'], context.user_data['password'])
            await update.message.reply_text("حساب با موفقیت ساخته شد!")
            context.user_data.clear()
        else:
            await update.message.reply_text("کد اشتباه! دوباره بفرست")

    elif step == 'username_login':
        context.user_data['username_login'] = text
        context.user_data['step'] = 'password_login'
        await update.message.reply_text("پسورد رو بفرست")

    elif step == 'password_login':
        if check_login(context.user_data['username_login'], text):
            await update.message.reply_text("ورود موفق! حالا می‌تونی دانلود کنی")
            context.user_data.clear()
        else:
            await update.message.reply_text("یوزرنیم یا پسورد اشتباه! دوباره امتحان کن")

    else:
        await update.message.reply_text("اول حساب بساز یا وارد شو!")

# --- توابع دیتابیس (اضافه شده) ---
def create_user(user_id, username, first_name, email, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, email, password, verified)
        VALUES (?, ?, ?, ?, ?, True)
    ''', (user_id, username, first_name, email, password))  # پسورد رو اینجا هش کن اگر خواستی (با bcrypt)
    conn.commit()
    conn.close()

def check_login(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE username = ? AND password = ?', (username, password))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# --- اجرای ربات ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("ربات دانلودر با حساب کاربری فعال شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
