# downloader.py — queue, worker, yt-dlp logic
import os
import glob
import asyncio
import logging
from typing import Tuple
import yt_dlp
from telegram.ext import Application
from db import save_download

DOWNLOAD_FOLDER = "downloads"
MAX_VIDEO_SIZE_DOC = 50 * 1024 * 1024
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

logger = logging.getLogger(__name__)

download_queue: asyncio.Queue = asyncio.Queue()

async def enqueue_download(update, context):
    url = (update.message.text or "").strip()
    user_id = update.message.from_user.id
    if not url:
        lang = context.user_data.get('lang') or 'fa'
        await update.message.reply_text("لینک نامعتبر است.")
        return
    await download_queue.put((update, user_id, url))
    # quick confirmation text (use user's lang if available)
    await update.message.reply_text("✅ لینک شما به صف اضافه شد. لطفاً صبور باشید.")

async def _process_item(app: Application, update, user_id: int, url: str):
    chat_id = update.effective_chat.id
    status_msg = await app.bot.send_message(chat_id=chat_id, text="⏳ در حال پردازش دانلود...")
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
            await app.bot.edit_message_text("❌ دانلود ناموفق: اطلاعات دریافت نشد.", chat_id, status_msg.message_id)
            return
        file_pattern = f"{DOWNLOAD_FOLDER}/{info.get('id')}.*"
        matches = glob.glob(file_pattern)
        if not matches:
            matches = sorted(glob.glob(f"{DOWNLOAD_FOLDER}/*"), key=os.path.getmtime, reverse=True)[:1]
        if not matches:
            await app.bot.edit_message_text("❌ خطا: فایل دانلود شده پیدا نشد.", chat_id, status_msg.message_id)
            return
        file_path = matches[0]
        title = info.get('title') or os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        if is_audio or file_size > MAX_VIDEO_SIZE_DOC:
            with open(file_path, 'rb') as f:
                await app.bot.send_document(chat_id, f, caption=f"🔹 {title}")
            save_download(user_id, 'Audio' if is_audio else 'Video', url, title, 'audio' if is_audio else 'video', file_size)
        else:
            with open(file_path, 'rb') as f:
                await app.bot.send_video(chat_id, f, caption=f"🔹 {title}")
            save_download(user_id, 'Video', url, title, 'video', file_size)
    except Exception as e:
        logger.exception("error processing download")
        try:
            await app.bot.edit_message_text(f"❌ خطا در دانلود: {e}", chat_id, status_msg.message_id)
        except Exception:
            pass
    finally:
        try:
            os.remove(file_path)
        except Exception:
            pass
        try:
            await app.bot.delete_message(chat_id, status_msg.message_id)
        except Exception:
            pass

async def worker_loop(app: Application):
    while True:
        try:
            update, user_id, url = await download_queue.get()
            await _process_item(app, update, user_id, url)
            download_queue.task_done()
        except Exception:
            logger.exception("worker crashed; sleeping 1s")
            await asyncio.sleep(1)

async def cleanup_loop():
    import glob, os, time
    while True:
        now = time.time()
        for path in glob.glob(f"{DOWNLOAD_FOLDER}/*"):
            try:
                if now - os.path.getmtime(path) > 600:
                    os.remove(path)
            except Exception:
                pass
        await asyncio.sleep(300)

def start_background_workers(app: Application):
    # create background tasks for worker + cleanup
    app.create_task(worker_loop(app))
    app.create_task(cleanup_loop())
