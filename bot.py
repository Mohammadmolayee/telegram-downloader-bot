# ========================================
# ربات دانلودر حرفه‌ای - نسخه نهایی با ایموجی‌های خفن
# فقط فارسی + دانلود + حساب + تاریخچه موقت + بدون هیچ دردسر
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

MAX_GUEST_DOWNLOADS_PER_DAY = 10

# پاک کردن دانلودهای قدیمی‌تر از 24 ساعت
def cleanup_old():
    try:
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        with sqlite3.connect(DB_PATH) as c:
            c.execute("DELETE FROM downloads WHERE downloaded_at < ?", (cutoff,))
            c.commit()
    except:
        pass

def init_db():
    cleanup_old()
    with sqlite3.connect(DB_PATH) as c:
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                first_name TEXT,
                password TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                platform TEXT,
                title TEXT,
                downloaded_at TEXT
            )
        ''')

init_db()

def create_user(uid, username, name, pw):
    try:
        with sqlite3.connect(DB_PATH) as c:
            c.execute("INSERT INTO users VALUES (?,?,?,?)", (uid, username, name, pw))
        return True
    except:
        return False

def user_exists(uid):
    with sqlite3.connect(DB_PATH) as c:
        return c.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone() is not None

def check_login(username, pw):
    with sqlite3.connect(DB_PATH) as c:
        row = c.execute("SELECT 1 FROM users WHERE username=? AND password=?", (username, pw)).fetchone()
        return row is not None

def save_download(uid, platform, title):
    cleanup_old()
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO downloads (user_id,platform,title,downloaded_at) VALUES (?,?,?,?)",
                 (uid, platform, title[:150], datetime.now().isoformat()))

def get_today_count(uid):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as c:
        return c.execute("SELECT COUNT(*) FROM downloads WHERE user_id=? AND substr(downloaded_at,1,10)=?", (uid, today)).fetchone()[0]

def get_recent_downloads(uid, limit=10):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("SELECT platform, title, downloaded_at FROM downloads WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit))
        return c.fetchall()

# /start — خوش‌آمدگویی با ایموجی خفن
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("منو اصلی", callback_data="show_menu")]]
    await update.message.reply_text(
        "به ربات دانلودر حرفه‌ای خوش اومدی!\n\n"
        "ویدیو و آهنگ از یوتیوب، اینستاگرام، تیک‌تاک و همه جا دانلود کن\n\n"
        "لینک رو بفرست تا برات دانلود کنم!\n"
        "برای امکانات بیشتر (تاریخچه، آمار، نامحدود) دکمه زیر رو بزن",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# نمایش منو — با ایموجی
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    back_kb = [[InlineKeyboardButton("برگشت به منو", callback_data="show_menu")]]

    if user_exists(uid):
        kb = [
            [InlineKeyboardButton("دانلودهای من (24 ساعت)", callback_data="my_downloads")],
            [InlineKeyboardButton("آمار من", callback_data="my_stats")],
            [InlineKeyboardButton("خروج از حساب", callback_data="logout")],
            [InlineKeyboardButton("راهنما", callback_data="help")],
        ]
        text = "به پنل کاربریت خوش اومدی"
    else:
        kb = [
            [InlineKeyboardButton("ساخت حساب (نامحدود)", callback_data="register")],
            [InlineKeyboardButton("راهنما", callback_data="help")],
        ]
        text = "برای امکانات بیشتر، اول حساب بساز"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb + back_kb))

# دکمه‌ها — با ایموجی
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    back_kb = [[InlineKeyboardButton("برگشت به منو", callback_data="show_menu")]]

    if data == "my_downloads":
        downloads = get_recent_downloads(uid, 10)
        if not downloads:
            text = "هنوز هیچ دانلودی در ۲۴ ساعت اخیر نداری!"
        else:
            text = "آخرین دانلودها:\n\n"
            for plat, title, dt in downloads:
                time = dt[11:16] if "T" in dt else "نامشخص"
                text += f"{plat} | {time}\n{title}\n\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(back_kb))

    elif data == "my_stats":
        total = len(get_recent_downloads(uid, 999))
        today = get_today_count(uid)
        await query.edit_message_text(
            f"آمار دانلودت\n\nکل (24 ساعت): {total}\nامروز: {today}\nوضعیت: نامحدود",
            reply_markup=InlineKeyboardMarkup(back_kb)
        )

    elif data == "logout":
        await query.edit_message_text("با موفقیت از حساب خارج شدی!\n/start بزن", reply_markup=InlineKeyboardMarkup(back_kb))

    elif data == "register":
        if user_exists(uid):
            await query.edit_message_text("شما قبلاً حساب دارید!", reply_markup=InlineKeyboardMarkup(back_kb))
            return
        context.user_data["step"] = "reg_name"
        await query.edit_message_text("نام و نام خانوادگی رو بفرست", reply_markup=InlineKeyboardMarkup(back_kb))

    elif data == "help":
        await query.edit_message_text(
            "راهنما\n\n"
            "• بدون حساب: حداکثر ۱۰ دانلود در روز\n"
            "• با حساب: نامحدود + تاریخچه\n"
            "• ساخت حساب → نام → یوزرنیم → پسورد (۸-۱۲)\n"
            "• هر سوالی داشتی /start بزن!",
            reply_markup=InlineKeyboardMarkup(back_kb)
        )

# پیام‌ها
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()

    if any(site in text for site in ["youtube.com", "youtu.be", "instagram.com", "tiktok.com", "twitter.com", "x.com"]):
        if not user_exists(uid) and get_today_count(uid) >= MAX_GUEST_DOWNLOADS_PER_DAY:
            await update.message.reply_text("امروز ۱۰ تا دانلود کردی!\nحساب بساز تا نامحدود بشه")
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
            await update.message.reply_text("حساب ساخته شد!\n/start بزن")
        else:
            await update.message.reply_text("این یوزرنیم قبلاً استفاده شده!")
        context.user_data.clear()

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, uid: int):
    msg = await update.message.reply_text("در حال دانلود...")
    plat = "YouTube" if "youtube" in url or "youtu.be" in url else "اینستا/تیک‌تاک"

    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file = glob.glob(f"{DOWNLOAD_FOLDER}/{info.get('id')}.*")[0]
            title = info.get("title", "ویدیو")[:100]

        with open(file, "rb") as v:
            await update.message.reply_video(v, caption=title)

        save_download(uid, plat, url, title)
        os.remove(file)
        await msg.delete()
    except Exception as e:
        await msg.edit_message_text("دانلود نشد! لینک رو چک کن")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_menu, pattern="^show_menu$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("ربات دانلودر نهایی فعال شد...")
    app.run_polling()

if __name__ == "__main__":
    main
