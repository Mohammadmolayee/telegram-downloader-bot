# bot.py
import os
import glob
import asyncio
import sqlite3
import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
import yt_dlp

# -------------------- تنظیمات --------------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("توکن ربات را در ENV با نام TOKEN قرار دهید.")

ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None

DOWNLOAD_FOLDER = "downloads"
DB_PATH = "downloads.db"
MAX_VIDEO_SIZE_DOC = 50 * 1024 * 1024  # 50MB
GUEST_DAILY_LIMIT = 10
CLEANUP_INTERVAL_SECONDS = 300
TEMP_FILE_AGE_SECONDS = 600

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# -------------------- لاگ --------------------
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- متون چندزبانه --------------------
# فارسی، انگلیسی و عربی ترجمه شده؛ بقیه زبان‌ها از متن انگلیسی استفاده می‌کنند.
TEXTS: Dict[str, Dict[str, str]] = {
    'fa': {
        'welcome': "✨ سلام! به ربات دانلودر حرفه‌ای خوش اومدی ✨\n\n"
                   "📹 تمام ویدیوها با کیفیت 720p دانلود می‌شوند.\n"
                   "🎵 صوت‌ها با بهترین کیفیت دریافت می‌شوند.\n\n"
                   "برای دانلود، لینک ارسال کن.",
        'menu_title': "منو اصلی 🔧\nانتخاب کن:",
        'btn_create': "👤 ساخت حساب",
        'btn_login': "🔐 ورود",
        'btn_my_downloads': "📂 دانلودهای من",
        'btn_my_stats': "📊 آمار من",
        'btn_help': "❓ راهنما",
        'btn_set_lang': "🌐 تغییر زبان",
        'added_queue': "✅ لینک شما به صف دانلود اضافه شد. لطفا صبور باشید — دانلودها یکی‌یکی انجام می‌شوند.",
        'invalid_link': "لینک نامعتبر است. لطفاً یک لینک بفرستید.",
        'guest_limit': f"⚠️ به عنوان مهمان امروز {GUEST_DAILY_LIMIT} دانلود انجام داده‌اید. برای افزایش محدودیت ثبت‌نام کنید.",
        'processing': "⏳ در حال پردازش دانلود...",
        'download_failed': "❌ دانلود ناموفق: {}",
        'no_downloads': "📂 شما هنوز دانلودی ندارید.",
        'my_downloads_header': "📂 دانلودهای اخیر:",
        'my_stats': "📊 آمار شما:\n• کل دانلودها: {}\n• حجم کل دانلودها: {:.2f} MB\n• دانلودهای ۲۴ ساعت گذشته: {}",
        'create_prompt_name': "🔹 ساخت حساب\nلطفاً نام و نام‌خانوادگی خود را ارسال کنید:",
        'create_prompt_username': "یوزرنیم دلخواه را وارد کنید (بدون @):",
        'create_prompt_password': "پسورد (۸-۱۲ کاراکتر، حرف/عدد، بدون فاصله) را وارد کنید:",
        'create_success': "🎉 حساب با موفقیت ساخته شد! اکنون می‌توانید وارد شده و دانلود کنید.",
        'create_fail': "خطا: یوزرنیم تکراری یا مشکل پایگاه داده. دوباره تلاش کنید.",
        'login_prompt_username': "🔐 ورود\nلطفاً یوزرنیم خود را ارسال کنید:",
        'login_prompt_password': "پسورد خود را ارسال کنید:",
        'login_success': "✅ ورود موفق! اکنون می‌توانید لینک‌ها را بفرستید.",
        'login_fail': "یوزرنیم یا پسورد اشتباه است.",
        'help_text': "📘 راهنما\n\n"
                     "• ساخت حساب: نام + یوزرنیم + پسورد (۸-۱۲ حرف/عدد)\n"
                     "• ورود: یوزرنیم و پسورد\n"
                     "• دانلود: بعد از ورود یا بدون حساب لینک بفرست\n"
                     f"• محدودیت مهمان: {GUEST_DAILY_LIMIT} دانلود در روز\n\n"
                     "لینک‌ها در صف قرار می‌گیرند و یکی‌یکی پردازش می‌شوند.",
        'lang_changed': "زبان با موفقیت تغییر کرد.",
        'set_lang_prompt': "زبان را انتخاب کن / Choose your language:",
    },
    'en': {
        'welcome': "✨ Welcome to the professional downloader bot ✨\n\n"
                   "📹 All videos will be downloaded at 720p.\n"
                   "🎵 Audio files are fetched in best quality.\n\n"
                   "Send a link to download.",
        'menu_title': "Main Menu 🔧\nChoose:",
        'btn_create': "👤 Create Account",
        'btn_login': "🔐 Login",
        'btn_my_downloads': "📂 My Downloads",
        'btn_my_stats': "📊 My Stats",
        'btn_help': "❓ Help",
        'btn_set_lang': "🌐 Set Language",
        'added_queue': "✅ Your link was added to the download queue. Please wait — items are processed one by one.",
        'invalid_link': "Invalid link. Please send a proper URL.",
        'guest_limit': f"⚠️ As a guest you have reached the daily limit of {GUEST_DAILY_LIMIT} downloads. Register to increase limit.",
        'processing': "⏳ Processing download...",
        'download_failed': "❌ Download failed: {}",
        'no_downloads': "📂 You have no downloads yet.",
        'my_downloads_header': "📂 Recent downloads:",
        'my_stats': "📊 Your stats:\n• Total downloads: {}\n• Total size: {:.2f} MB\n• Downloads last 24h: {}",
        'create_prompt_name': "🔹 Create Account\nPlease send your full name:",
        'create_prompt_username': "Send desired username (without @):",
        'create_prompt_password': "Send password (8-12 alnum chars):",
        'create_success': "🎉 Account created successfully! You can now login and download.",
        'create_fail': "Error: username exists or DB error. Try again.",
        'login_prompt_username': "🔐 Login\nPlease send your username:",
        'login_prompt_password': "Send your password:",
        'login_success': "✅ Login successful! You can now send links.",
        'login_fail': "Username or password incorrect.",
        'help_text': "📘 Help\n\n"
                     "• Create account: name + username + password (8-12 alnum)\n"
                     "• Login: username + password\n"
                     "• Download: send link (logged or guest)\n"
                     f"• Guest limit: {GUEST_DAILY_LIMIT} downloads/day\n\n"
                     "Links are queued and processed one by one.",
        'lang_changed': "Language changed successfully.",
        'set_lang_prompt': "Choose your language / زبان را انتخاب کنید:",
    },
    'ar': {
        'welcome': "✨ أهلاً بك في بوت التحميل الاحترافي ✨\n\n"
                   "📹 سيتم تحميل جميع الفيديوهات بجودة 720p.\n"
                   "🎵 سيتم الحصول على الصوت بأعلى جودة.\n\n"
                   "أرسل رابطًا للتحميل.",
        'menu_title': "القائمة الرئيسية 🔧\nاختر:",
        'btn_create': "👤 إنشاء حساب",
        'btn_login': "🔐 تسجيل الدخول",
        'btn_my_downloads': "📂 تنزيلاتي",
        'btn_my_stats': "📊 احصاءاتي",
        'btn_help': "❓ مساعدة",
        'btn_set_lang': "🌐 تغيير اللغة",
        'added_queue': "✅ تمت إضافة رابطك إلى قائمة التحميل. الرجاء الانتظار — ستتم المعالجة واحدًا تلو الآخر.",
        'invalid_link': "رابط غير صالح. الرجاء إرسال رابط صحيح.",
        'guest_limit': f"⚠️ بصفتك ضيفًا وصلت إلى حد التنزيل اليومي {GUEST_DAILY_LIMIT}. سجّل لزيادة الحد.",
        'processing': "⏳ جاري معالجة التحميل...",
        'download_failed': "❌ فشل التنزيل: {}",
        'no_downloads': "📂 ليس لديك تنزيلات بعد.",
        'my_downloads_header': "📂 التنزيلات الأخيرة:",
        'my_stats': "📊 احصائياتك:\n• إجمالي التنزيلات: {}\n• إجمالي الحجم: {:.2f} MB\n• التنزيلات خلال 24 ساعة: {}",
        'create_prompt_name': "🔹 إنشاء حساب\nالرجاء إرسال الاسم الكامل:",
        'create_prompt_username': "أرسل اسم المستخدم المطلوب (بدون @):",
        'create_prompt_password': "أرسل كلمة المرور (8-12 حرف/رقم):",
        'create_success': "🎉 تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول والتحميل.",
        'create_fail': "خطأ: اسم المستخدم موجود أو خطأ في قاعدة البيانات. حاول مرة أخرى.",
        'login_prompt_username': "🔐 تسجيل الدخول\nأرسل اسم المستخدم:",
        'login_prompt_password': "أرسل كلمة المرور:",
        'login_success': "✅ تم تسجيل الدخول! يمكنك الآن إرسال الروابط.",
        'login_fail': "اسم المستخدم أو كلمة المرور غير صحيحة.",
        'help_text': "📘 مساعدة\n\n"
                     "• إنشاء حساب: اسم + اسم المستخدم + كلمة المرور (8-12 حرف/رقم)\n"
                     f"• حد الضيف: {GUEST_DAILY_LIMIT} تنزيلات/يوم\n\n"
                     "ستتم معالجة الروابط واحدًا تلو الآخر.",
        'lang_changed': "تم تغيير اللغة بنجاح.",
        'set_lang_prompt': "اختر لغتك / زبان را انتخاب کنید:",
    },
}
# برای زبان‌های اضافه (tr, ru, es, hi) از متن انگلیسی پایه استفاده می‌کنیم
for code in ('tr', 'ru', 'es', 'hi'):
    TEXTS.setdefault(code, TEXTS['en'])

LANG_OPTIONS = [('fa', 'فارسی'), ('en', 'English'), ('ar', 'العربية'),
                ('tr', 'Türkçe'), ('ru', 'Русский'), ('es', 'Español'), ('hi', 'हिंदी')]

# -------------------- دیتابیس init --------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('PRAGMA journal_mode=WAL;')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            first_name TEXT,
            password_hash BLOB,
            lang TEXT DEFAULT 'fa',
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
            file_type TEXT,
            file_size INTEGER,
            downloaded_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -------------------- توابع دیتابیس و کاربر --------------------
def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    except Exception:
        return False

def create_user(user_id: int, username: str, first_name: str, password: str, lang: str = 'fa') -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        hashed = hash_password(password)
        c.execute('''
            INSERT INTO users (user_id, username, first_name, password_hash, lang, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, sqlite3.Binary(hashed), lang, datetime.utcnow().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_username(username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, username, first_name, password_hash, lang FROM users WHERE username=?', (username,))
    row = c.fetchone()
    conn.close()
    return row

def user_exists(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE user_id=?', (user_id,))
    r = c.fetchone() is not None
    conn.close()
    return r

def get_user_lang(user_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT lang FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 'fa'

def set_user_lang(user_id: int, lang: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET lang=? WHERE user_id=?', (lang, user_id))
    conn.commit()
    conn.close()

# -------------------- رکورد دانلود --------------------
def save_download(user_id: int, platform: str, url: str, title: str, file_type: str, file_size: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO downloads (user_id, platform, url, title, file_type, file_size, downloaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, platform, url, title, file_type, file_size, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_user_downloads(user_id: int, limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT platform, title, file_type, file_size, downloaded_at
        FROM downloads WHERE user_id=? ORDER BY downloaded_at DESC LIMIT ?
    ''', (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def get_daily_download_count(user_id: int) -> int:
    since = datetime.utcnow() - timedelta(days=1)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM downloads WHERE user_id=? AND downloaded_at>=?', (user_id, since.isoformat()))
    row = c.fetchone()
    conn.close()
    return int(row[0]) if row else 0

def get_user_stats(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*), COALESCE(SUM(file_size),0) FROM downloads WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return int(row[0]), int(row[1])

# -------------------- Queue دانلود --------------------
download_queue: asyncio.Queue = asyncio.Queue()

async def enqueue_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()
    user_id = update.message.from_user.id
    lang = get_user_lang(user_id)
    t = lambda k, *a, **kw: TEXTS[lang][k].format(*a, **kw)

    if not url:
        await update.message.reply_text(t('invalid_link'))
        return

    if not user_exists(user_id):
        cnt = get_daily_download_count(user_id)
        if cnt >= GUEST_DAILY_LIMIT:
            await update.message.reply_text(t('guest_limit'))
            return

    await download_queue.put((update, user_id, url))
    await update.message.reply_text(t('added_queue'))

async def process_queue_worker(app: Application):
    while True:
        try:
            update, user_id, url = await download_queue.get()
            chat = update.effective_chat
            lang = get_user_lang(user_id)
            t = lambda k, *a, **kw: TEXTS[lang][k].format(*a, **kw)
            status_msg = await app.bot.send_message(chat_id=chat.id, text=t('processing'))
            try:
                lower = url.lower()
                is_audio = any(x in lower for x in ("soundcloud", "spotify")) or lower.endswith(('.mp3', '.wav'))

                if is_audio:
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
                        'quiet': True, 'noplaylist': True, 'retries': 3
                    }
                else:
                    ydl_opts = {
                        'format': 'bestvideo[height<=720]+bestaudio/best/best',
                        'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
                        'merge_output_format': 'mp4',
                        'quiet': True, 'noplaylist': True, 'retries': 3
                    }

                info = None
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)

                if not info:
                    await app.bot.edit_message_text(t('download_failed').format("info empty"), chat.id, status_msg.message_id)
                    download_queue.task_done()
                    continue

                file_pattern = f"{DOWNLOAD_FOLDER}/{info.get('id')}.*"
                matches = glob.glob(file_pattern)
                if not matches:
                    matches = sorted(glob.glob(f"{DOWNLOAD_FOLDER}/*"), key=os.path.getmtime, reverse=True)[:1]

                if not matches:
                    await app.bot.edit_message_text(t('download_failed').format("file not found"), chat.id, status_msg.message_id)
                    download_queue.task_done()
                    continue

                file_path = matches[0]
                title = info.get('title') or os.path.basename(file_path)
                file_size = os.path.getsize(file_path)

                if is_audio or file_size > MAX_VIDEO_SIZE_DOC:
                    with open(file_path, 'rb') as f:
                        await app.bot.send_document(chat.id, f, caption=f"🔹 {title}")
                    save_download(user_id, 'Audio' if is_audio else 'Video', url, title, 'audio' if is_audio else 'video', file_size)
                else:
                    with open(file_path, 'rb') as f:
                        await app.bot.send_video(chat.id, f, caption=f"🔹 {title}")
                    save_download(user_id, 'Video', url, title, 'video', file_size)

                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"remove file failed: {e}")

                try:
                    await app.bot.delete_message(chat.id, status_msg.message_id)
                except Exception:
                    pass

            except Exception as e:
                logger.exception("error while processing download")
                try:
                    await app.bot.edit_message_text(t('download_failed').format(str(e)), chat.id, status_msg.message_id)
                except Exception:
                    pass
                if ADMIN_ID:
                    try:
                        await app.bot.send_message(ADMIN_ID, f"Error processing {url} for user {user_id}:\n{e}")
                    except Exception:
                        pass
            finally:
                download_queue.task_done()
        except Exception:
            logger.exception("worker crashed unexpectedly")
            await asyncio.sleep(1)

# -------------------- پاکسازی پوشه دانلود --------------------
async def cleanup_download_folder_periodically(app: Application):
    while True:
        try:
            now = datetime.utcnow()
            for path in glob.glob(f"{DOWNLOAD_FOLDER}/*"):
                try:
                    mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
                    age = (now - mtime).total_seconds()
                    if age > TEMP_FILE_AGE_SECONDS:
                        logger.info(f"cleaning old file: {path}")
                        try:
                            os.remove(path)
                        except Exception as e:
                            logger.warning(f"failed to remove {path}: {e}")
                except FileNotFoundError:
                    continue
        except Exception:
            logger.exception("cleanup error")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

# -------------------- منوها و Conversation --------------------
(
    REG_FIRSTNAME, REG_USERNAME, REG_PASSWORD,
    LOGIN_USERNAME, LOGIN_PASSWORD
) = range(5)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    kb = [
        [InlineKeyboardButton(TEXTS[lang]['btn_create'], callback_data='create_account')],
        [InlineKeyboardButton(TEXTS[lang]['btn_login'], callback_data='login')],
        [InlineKeyboardButton(TEXTS[lang]['btn_my_downloads'], callback_data='my_downloads')],
        [InlineKeyboardButton(TEXTS[lang]['btn_my_stats'], callback_data='my_stats')],
        [InlineKeyboardButton(TEXTS[lang]['btn_set_lang'], callback_data='set_lang')],
        [InlineKeyboardButton(TEXTS[lang]['btn_help'], callback_data='help')],
    ]
    await update.message.reply_text(TEXTS[lang]['welcome'], reply_markup=InlineKeyboardMarkup(kb))

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    kb = [
        [InlineKeyboardButton(TEXTS[lang]['btn_create'], callback_data='create_account')],
        [InlineKeyboardButton(TEXTS[lang]['btn_login'], callback_data='login')],
        [InlineKeyboardButton(TEXTS[lang]['btn_my_downloads'], callback_data='my_downloads')],
        [InlineKeyboardButton(TEXTS[lang]['btn_my_stats'], callback_data='my_stats')],
        [InlineKeyboardButton(TEXTS[lang]['btn_set_lang'], callback_data='set_lang')],
        [InlineKeyboardButton(TEXTS[lang]['btn_help'], callback_data='help')],
    ]
    await q.answer()
    await q.edit_message_text(TEXTS[lang]['menu_title'], reply_markup=InlineKeyboardMarkup(kb))

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    await q.edit_message_text(TEXTS[lang]['help_text'])

# ساخت حساب
async def create_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    if user_exists(user_id):
        await q.edit_message_text(TEXTS[lang]['create_fail'])
        return
    context.user_data.clear()
    await q.edit_message_text(TEXTS[lang]['create_prompt_name'])
    return

async def reg_firstname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text(TEXTS[lang]['create_prompt_name'])
        return REG_FIRSTNAME
    context.user_data['first_name'] = text
    await update.message.reply_text(TEXTS[lang]['create_prompt_username'])
    return REG_USERNAME

async def reg_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = (update.message.text or "").strip()
    if text.startswith('@'):
        text = text[1:]
    if len(text) < 3:
        await update.message.reply_text(TEXTS[lang]['create_prompt_username'])
        return REG_USERNAME
    if get_user_by_username(text):
        await update.message.reply_text(TEXTS[lang]['create_fail'])
        return REG_USERNAME
    context.user_data['username'] = text
    await update.message.reply_text(TEXTS[lang]['create_prompt_password'])
    return REG_PASSWORD

async def reg_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = (update.message.text or "").strip()
    if not (8 <= len(text) <= 12 and text.isalnum()):
        await update.message.reply_text(TEXTS[lang]['create_prompt_password'])
        return REG_PASSWORD
    username = context.user_data.get('username')
    first_name = context.user_data.get('first_name')
    ok = create_user(user_id, username, first_name, text, lang)
    context.user_data.clear()
    if ok:
        await update.message.reply_text(TEXTS[lang]['create_success'])
    else:
        await update.message.reply_text(TEXTS[lang]['create_fail'])
    return ConversationHandler.END

# ورود
async def login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    context.user_data.clear()
    await q.edit_message_text(TEXTS[lang]['login_prompt_username'])
    return

async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = (update.message.text or "").strip()
    if text.startswith('@'):
        text = text[1:]
    context.user_data['login_username'] = text
    await update.message.reply_text(TEXTS[lang]['login_prompt_password'])
    return LOGIN_PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = (update.message.text or "").strip()
    username = context.user_data.get('login_username')
    row = get_user_by_username(username)
    context.user_data.clear()
    if not row:
        await update.message.reply_text(TEXTS[lang]['login_fail'])
        return ConversationHandler.END
    stored_hash = row[3]
    if check_password(text, stored_hash):
        await update.message.reply_text(TEXTS[lang]['login_success'])
    else:
        await update.message.reply_text(TEXTS[lang]['login_fail'])
    return ConversationHandler.END

# دانلودهای من
async def my_downloads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    rows = get_user_downloads(user_id, limit=10)
    if not rows:
        await q.edit_message_text(TEXTS[lang]['no_downloads'])
        return
    lines = [TEXTS[lang]['my_downloads_header']]
    for platform, title, file_type, file_size, downloaded_at in rows:
        mb = file_size / (1024*1024) if file_size else 0
        lines.append(f"• {platform} — {title}\n  نوع: {file_type} — {mb:.2f} MB — {downloaded_at}")
    await q.edit_message_text("\n\n".join(lines))

# آمار من
async def my_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    total_count, total_bytes = get_user_stats(user_id)
    daily = get_daily_download_count(user_id)
    mb = total_bytes / (1024*1024)
    await q.edit_message_text(TEXTS[lang]['my_stats'].format(total_count, mb, daily))

# انتخاب زبان
async def set_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    kb = [[InlineKeyboardButton(label, callback_data=f"lang:{code}")] for code, label in LANG_OPTIONS]
    await q.edit_message_text(TEXTS[lang]['set_lang_prompt'], reply_markup=InlineKeyboardMarkup(kb))

async def lang_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    data = q.data
    try:
        _, code = data.split(':', 1)
    except Exception:
        await q.answer()
        return
    set_user_lang(user_id, code)
    await q.answer()
    await q.edit_message_text(TEXTS[code]['lang_changed'])

# ادمین آمار
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ فقط ادمین می‌تواند این دستور را اجرا کند.")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    users_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM downloads')
    downloads_count = c.fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 کاربران ثبت‌شده: {users_count}\n📥 تعداد دانلودها: {downloads_count}")

# -------------------- راه‌اندازی اپ --------------------
def main():
    app = Application.builder().token(TOKEN).build()

    # Handlers پایه و منوها
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern='^menu$'))
    app.add_handler(CallbackQueryHandler(create_account_callback, pattern='^create_account$'))
    app.add_handler(CallbackQueryHandler(login_callback, pattern='^login$'))
    app.add_handler(CallbackQueryHandler(my_downloads_callback, pattern='^my_downloads$'))
    app.add_handler(CallbackQueryHandler(my_stats_callback, pattern='^my_stats$'))
    app.add_handler(CallbackQueryHandler(help_callback, pattern='^help$'))
    app.add_handler(CallbackQueryHandler(set_lang_callback, pattern='^set_lang$'))
    app.add_handler(CallbackQueryHandler(lang_selected_callback, pattern='^lang:'))

    # Conversation برای ثبت‌نام و ورود
    reg_conv = ConversationHandler(
        entry_points=[],
        states={
            REG_FIRSTNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_firstname)],
            REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_username)],
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_password)],
            LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[]
    )
    app.add_handler(reg_conv)

    # پیام‌های متنی -> اضافه به صف دانلود
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, enqueue_download))

    # دستورات مدیریتی
    app.add_handler(CommandHandler("stats", stats_command))

    # کارهای پس‌زمینه: worker و پاکسازی
    app.create_task(process_queue_worker(app))
    app.create_task(cleanup_download_folder_periodically(app))

    logger.info("Advanced downloader (multilang) bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
