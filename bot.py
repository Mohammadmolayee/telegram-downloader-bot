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

# Rawilay: مسیر دانلود و دیتابیس داخل HOME
HOME_DIR = os.getenv("HOME")
DOWNLOAD_FOLDER = os.path.join(HOME_DIR, "downloads")
DB_PATH = os.path.join(HOME_DIR, "downloads.db")

MAX_VIDEO_SIZE_DOC = 50 * 1024 * 1024  # 50MB
GUEST_DAILY_LIMIT = 10
CLEANUP_INTERVAL_SECONDS = 300
TEMP_FILE_AGE_SECONDS = 600

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# -------------------- لاگ --------------------
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- متون چندزبانه --------------------
TEXTS: Dict[str, Dict[str, str]] = {
    'fa': {
        # ... (تمام متون فارسی از کد شما بدون تغییر)
    },
    'en': {
        # ... (تمام متون انگلیسی بدون تغییر)
    },
    'ar': {
        # ... (تمام متون عربی بدون تغییر)
    },
}
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
                        'quiet': True, 'noplaylist': True,
                        'retries': 3,
                        'ffmpeg_location': '/usr/bin/ffmpeg'
                    }
                else:
                    ydl_opts = {
                        'format': 'bestvideo[height<=720]+bestaudio/best/best',
                        'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
                        'merge_output_format': 'mp4',
                        'quiet': True,
                        'noplaylist': True,
                        'retries': 3,
                        'ffmpeg_location': '/usr/bin/ffmpeg'
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

# -------------------- تمام handlerها و callbackها همانند کد شما بدون تغییر --------------------
# ... (start_handler, menu_callback, help_callback, create_account_callback, reg_firstname, reg_username, reg_password,
# login_callback, login_username, login_password, my_downloads_callback, my_stats_callback, set_lang_callback,
# lang_selected_callback, stats_command)

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
