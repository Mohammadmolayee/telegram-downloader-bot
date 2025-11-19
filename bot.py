# =============================================
# ربات دانلودر حرفه‌ای - نسخه نهایی با کامنت فارسی
# کاملاً بهینه برای Railway رایگان (512MB RAM)
# =============================================

import os
import sqlite3
import yt_dlp
import glob
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ================= تنظیمات اصلی =================
TOKEN = os.getenv("TOKEN")  # توکن ربات رو از Railway → Variables بذار
DB_PATH = "downloads.db"                    # دیتابیس موقت (هر ری‌استارت پاک میشه یا قدیمی‌ها حذف میشن)
DOWNLOAD_FOLDER = "downloads"               # پوشه دانلود فایل‌ها
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True) # ساخت پوشه اگه وجود نداشته باشه

MAX_GUEST_DOWNLOADS_PER_DAY = 10  # محدودیت مهمان (بدون حساب)

# پاک‌سازی دانلودهای قدیمی‌تر از ۲۴ ساعت
def cleanup_old():
    try:
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        with sqlite3.connect(DB_PATH) as c:
            c.execute("DELETE FROM downloads WHERE downloaded_at < ?", (cutoff,))
            c.commit()
    except:
        pass  # اگه خطا داد مهم نیست

# ساخت دیتابیس و جدول‌ها
def init_db():
    cleanup_old()
    with sqlite3.connect(DB_PATH) as c:
        # جدول کاربران
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        full_name TEXT,
                        username TEXT UNIQUE,
                        password_hash TEXT,
                        last_seen TEXT)''')
        # جدول دانلودها
        c.execute('''CREATE TABLE IF NOT EXISTS downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        platform TEXT,
                        title TEXT,
                        downloaded_at TEXT)''')

init_db()

# هش کردن پسورد (امنیت)
def hash_password(pw): 
    return __import__('hashlib').sha256(pw.encode()).hexdigest()

# ساخت حساب کاربری جدید
def create_user(uid, full_name, username, pw):
    try:
        with sqlite3.connect(DB_PATH) as c:
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)",
                     (uid, full_name, username.lower(), hash_password(pw), datetime.now().isoformat()))
        return True
    except:
        return False

# گرفتن اطلاعات کاربر + به‌روزرسانی آخرین بازدید
def get_user(uid):
    with sqlite3.connect(DB_PATH) as c:
        row = c.execute("SELECT full_name, username, last_seen FROM users WHERE user_id=?", (uid,)).fetchone()
        if row:
            c.execute("UPDATE users SET last_seen=? WHERE user_id=?", (datetime.now().isoformat(), uid))
        return row

# چک کردن وجود حساب
def user_exists(uid):
    with sqlite3.connect(DB_PATH) as c:
        return c.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone() is not None

# ذخیره دانلود جدید
def save_download(uid, platform, title):
    cleanup_old()
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO downloads (user_id, platform, title, downloaded_at) VALUES (?,?,?,?)",
                 (uid, platform, title[:150], datetime.now().isoformat()))

# تعداد دانلود امروز
def get_today_count(uid):
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as c:
        return c.execute("SELECT COUNT(*) FROM downloads WHERE user_id=? AND substr(downloaded_at,1,10)=?", (uid, today)).fetchone()[0]

# آخرین دانلودها (حداکثر ۱۵ تا)
def get_recent_downloads(uid, limit=15):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("SELECT platform, title, downloaded_at FROM downloads WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit))
        return c.fetchall()

# ================= پیام خوش‌آمدگویی (/start) =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏠منوی اصلی", callback_data="main_menu")],
        [InlineKeyboardButton("راهنم📃ا", callback_data="help")]
    ]
    await update.message.reply_text(
        "به بات دانلودر حرفه‌ای خوش آمدید!🌹\n"
        "این ربات از یوتیوب، اینستاگرام، تیک‌تاک، توییتر و ... پشتیبانی می‌کند\n"
        "برای شروع لطفاً راهنمای ربات را مطالعه کنید📃\n"
        "با تشکر از شما که ما را انتخاب کردید❤️",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= هندلر دکمه‌ها =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qry = update.callback_query
    await qry.answer()
    uid = qry.from_user.id
    data = qry.data

    # دکمه برگشت به منوی اصلی (همه جا استفاده میشه)
    back_btn = [[InlineKeyboardButton("🏠برگشت به منوی اصلی", callback_data="main_menu")]]

    # راهنما
    if data == "help":
        await qry.edit_message_text(
            "😊با سلام و درود خدمت شما کاربر عزیز!\n\n"
            "🤖شما هم اکنون به بهترین ربات دانلودر تلگرامی مراجعه کردید\n"
            "😉شما می‌توانید با کلیک روی «منوی اصلی» و طی چند مرحله ساده، حساب کاربری بسازید و از امکانات نامحدود بهره‌مند شوید\n"
            "🤫یا بدون ساخت حساب به صورت محدود از ربات استفاده کنید\n\n"
            "با تشکر از همراهی شم🙏ا",
            reply_markup=InlineKeyboardMarkup(back_btn)
        )

    # منوی اصلی
    elif data == "main_menu":
        if user_exists(uid):
            user = get_user(uid)
            await qry.edit_message_text(
                f"🌹به پنل کاربری خود خوش آمدید {user[0]}!\n"
                "❓️چه کاری می‌خواهید انجام بدید؟",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥دانلودهای اخیر (۲۴ ساعت)", callback_data="my_downloads")],
                    [InlineKeyboardButton("📊آمار دانلودهای من", callback_data="my_stats")],
                    [InlineKeyboardButton("راهنم📃ا", callback_data="help")],
                    [InlineKeyboardButton("📱خروج از حساب کاربری", callback_data="logout")],
                    back_btn[0]
                ])
            )
        else:
            await qry.edit_message_text(
                "☺️سپاس از شما که عضو مجموعه ما می‌شوید!\n"
                "📲برای ادامه حساب کاربری خود را بسازید",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📲ساخت حساب کاربری", callback_data="register")],
                    back_btn[0]
                ])
            )

    # شروع ثبت‌نام
    elif data == "register":
        if user_exists(uid):
            await qry.edit_message_text("😉شما قبلاً حساب دارید!کاربرعزیز", reply_markup=InlineKeyboardMarkup(back_btn))
            return
        context.user_data["step"] = "get_name"
        await qry.edit_message_text("لطفاً نام و نام خانوادگی خود را وارد کنید", reply_markup=InlineKeyboardMarkup(back_btn))

    # نمایش دانلودهای اخیر
    elif data == "my_downloads":
        downloads = get_recent_downloads(uid, 15)
        if not downloads:
            text = "📥هنوز هیچ دانلودی در ۲۴ ساعت اخیر ندارید!"
        else:
            text = "📥دانلودهای اخیر شما (۲۴ ساعت):\n\n"
            for plat, title, dt in downloads:
                time = dt[11:16]
                text += f"{plat} | {time}\n{title}\n\n"
        await qry.edit_message_text(text, reply_markup=InlineKeyboardMarkup(back_btn))

    # آمار کاربر
    elif data == "my_stats":
        total = len(get_recent_downloads(uid, 999))
        user = get_user(uid)
        last = user[2][11:16] if user and user[2] else "نامشخص"
        await qry.edit_message_text(
            f"📊آمار دانلودهای شما\n\n"
            f"📥تعداد دانلودهای ۲۴ ساعت اخیر: {total}\n"
            f"👁آخرین بازدید: {last}\n"
            f"وضعیت: نامحدود",
            reply_markup=InlineKeyboardMarkup(back_btn)
        )

    # خروج از حساب
    elif data == "logout":
        await qry.edit_message_text(
            "🥺از حساب کاربری خود خارج شدید کاربر عزیز\n"
            "😁برای ورود دوباره لطفاً /start را بزنید",
            reply_markup=InlineKeyboardMarkup(back_btn)
        )

# ================= هندلر پیام‌های متنی =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()

    # تشخیص لینک و دانلود
    if any(x in text for x in ["youtube.com", "youtu.be", "instagram.com", "tiktok.com", "twitter.com", "x.com"]):
        if not user_exists(uid) and get_today_count(uid) >= MAX_GUEST_DOWNLOADS_PER_DAY:
            await update.message.reply_text("😉امروز به سقف دانلود رسیدید!\nحساب بسازید تا نامحدود شود")
            return
        await download_video(update, context, text, uid)
        return

    # مراحل ثبت‌نام
    step = context.user_data.get("step")
    back_btn = [[InlineKeyboardButton("لغو و برگشت", callback_data="main_menu")]]

    if step == "get_name":
        context.user_data["name"] = text
        context.user_data["step"] = "get_username"
        await update.message.reply_text("یک نام کاربری (یوزرنیم) انتخاب کنید\nلطفاً از @ استفاده نکنید", reply_markup=InlineKeyboardMarkup(back_btn))

    elif step == "get_username":
        if len(text) < 3:
            await update.message.reply_text("یوزرنیم خیلی کوتاهه!")
            return
        context.user_data["username"] = text.lower()
        context.user_data["step"] = "get_password"
        await update.message.reply_text("یک رمز عبور قوی (۸-۲۰ کاراکتر، فقط حروف و عدد انگلیسی) انتخاب کنید", reply_markup=InlineKeyboardMarkup(back_btn))

    elif step == "get_password":
        if not (8 <= len(text) <= 20 and text.isalnum()):
            await update.message.reply_text("رمز عبور باید ۸-۲۰ کاراکتر و فقط حروف و عدد انگلیسی باشد!")
            return
        if create_user(uid, context.user_data["name"], context.user_data["username"], text):
            await update.message.reply_text(
                "👍🏻حساب کاربری شما با موفقیت ساخته شد!\n"
                "🫡برای ورود به پنل خود لطفاً /start را بزنید",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ورود به پنل", callback_data="main_menu")]])
            )
        else:
            await update.message.reply_text("🥱این یوزرنیم قبلاً استفاده شده!")
        context.user_data.clear()

# ================= دانلود ویدیو =================
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, uid: int):
    msg = await update.message.reply_text("📥در حال دانلود...")
    platform = "YouTube" if "youtube" in url or "youtu.be" in url else "اینستاگرام/تیک‌تاک"

    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file = glob.glob(f"{DOWNLOAD_FOLDER}/{info.get('id')}.*")[0]
            title = info.get("title", "ویدیو")[:100]

        with open(file, "rb") as video:
            await update.message.reply_video(video, caption=title)

        save_download(uid, platform, title)
        os.remove(file)
        await msg.delete()
    except Exception as e:
        await msg.edit_text("⛓️‍💥دانلود نشد! لینک را چک کنید یا دوباره امتحان کنید")

# ================= اجرای ربات =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("ربات دانلودر حرفه‌ای با موفقیت راه‌اندازی شد!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
