# downloader.py

import os
import yt_dlp
import asyncio
from config import DOWNLOAD_FOLDER
from db import add_download

queue = {}        # صف دانلود
cancel_flags = {} # وضعیت لغو هر دانلود

# ساخت پوشه دانلود
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


async def download_worker(bot):
    """کارگر دانلود که همیشه در پس‌زمینه اجرا می‌شود"""
    while True:
        if not queue:
            await asyncio.sleep(0.5)
            continue

        user_id, task = queue.popitem()

        if cancel_flags.get(user_id):
            cancel_flags[user_id] = False
            continue

        url = task["url"]
        chat_id = task["chat_id"]

        try:
            await bot.send_message(chat_id, "⏳ دانلود آغاز شد...")

            ydl_opts = {
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "outtmpl": f"{DOWNLOAD_FOLDER}/%(id)s.%(ext)s",
                "quiet": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            await bot.send_video(chat_id, open(filename, "rb"))
            add_download(user_id)

            os.remove(filename)

        except Exception as e:
            try:
                await bot.send_message(chat_id, f"❌ خطا در دانلود: {e}")
            except:
                pass


def add_to_queue(user_id, chat_id, url):
    """افزودن به صف"""
    queue[user_id] = {"url": url, "chat_id": chat_id}


def cancel_download(user_id):
    """لغو دانلود"""
    cancel_flags[user_id] = True
