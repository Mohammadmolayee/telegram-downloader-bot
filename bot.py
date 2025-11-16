# ========================================
# ربات دانلودر حرفه‌ای - نسخه حرفه‌ای
# کد قبلی حفظ شده + منو + حساب کاربری + دیتابیس
# ========================================

import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# -------------------------------
# تنظیمات
# -------------------------------
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("TOKEN رو در Railway Variables بذار!")

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
            username TEXT,
            first_name TEXT,
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

init_db()  # دیتابیس رو بساز

# -------------------------------
# توابع دیتابیس
# -------------------------------
def create_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, created_at) VALUES (?, ?, ?, ?)',
                   (user_id, username, first_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def user_exists(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
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
# دستور /start — **کد قبلی حفظ شده + منو اضافه شد**
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # منو
    keyboard = [
        [InlineKeyboardButton("ساخت حساب کاربری", callback_data='create_account')],
        [InlineKeyboardButton("دانلودهای من", callback_data='my_downloads')],
        [InlineKeyboardButton("راهنما", callback_data='help')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # **متن خوش‌آمدگویی دقیقاً همون قبلی**
    await update.message.reply_text(
        "سلام! به ربات دانلودر حرفه‌ای خوش اومدی\n"
        "اینجا می‌تونی:\n"
        "ویدیو و اهنگ هر پلتفرمی دانلود کنی\n"
        "پشتیبانی از تمامی پلتفرم ها : یوتیوب,اینستاگرام,تیک‌تاک,توییتر,فیسبوک,ساندکلود,اسپاتیفای و....\n"
        "فقط لینک رو بفرست، بقیه‌ش با ماست!",
        reply_markup=reply_markup
    )

# -------------------------------
# دکمه‌ها — اضافه شده
# -------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'create_account':
        if user_exists(user_id):
            await query.edit_message_text("حساب شما قبلاً ساخته شده!")
        else:
            create_user(user_id, query.from_user.username, query.from_user.first_name)
            await query.edit_message_text(
                "حساب کاربری با موفقیت ساخته شد!\n"
                "حالا می‌تونی لینک بفرستی و دانلود کنی\n"
                "همه دانلودها در حسابت ذخیره می‌شن"
            )

    elif data == 'my_downloads':
        if not user_exists(user_id):
            await query.edit_message_text("اول حساب بساز!")
            return
        
        downloads = get_user_downloads(user_id)
        if not downloads:
            await query.edit_message_text("هنوز هیچ دانلودی نداری!")
            return
        
        text = "آخرین دانلودهای تو:\n\n"
        for plat, title, ftype, time in downloads:
            icon = "ویدیو" if ftype == "video" else "آهنگ"
            text += f"{icon} {plat}: {title}\n   {time.split('T')[0]} {time.split('T')[1][:5]}\n\n"
        
        await query.edit_message_text(text)

    elif data == 'help':
        await query.edit_message_text(
            "راهنما:\n"
            "1. حساب بساز\n"
            "2. لینک بفرست\n"
            "3. دانلود کن!\n"
            "همه چیز در حسابت ذخیره می‌شه"
        )

# -------------------------------
# اجرای ربات
# -------------------------------
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("ربات دانلودر با حساب کاربری فعال شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
