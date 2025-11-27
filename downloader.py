# downloader.py
import os
import asyncio
import yt_dlp
from datetime import datetime
from database import save_download, get_user
from messages import t

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

download_tasks = {}   # { user_id: asyncio.Task }
cancel_flags = {}      # { user_id: bool }


async def download_media(user_id, url, bot, lang):
    """
    دانلود با yt-dlp – کیفیت 360p ثابت – پشتیبانی از:
    یوتیوب / اینستا / تیک‌تاک / اسپاتیفای / ساندکلود
    """

    cancel_flags[user_id] = False

    msg = await bot.send_message(chat_id=user_id, text=t({"language": lang}, "downloading"))

    ydl_opts = {
        "format": "best[height<=360]",
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(id)s.%(ext)s",
        "quiet": True,
        "nocheckcertificate": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        file_id = info.get("id")
        title = info.get("title", "video")
        ext = info.get("ext", "mp4")
        file_path = f"{DOWNLOAD_FOLDER}/{file_id}.{ext}"

        # اگر کاربر لغو کرده
        if cancel_flags.get(user_id):
            await msg.edit_text(t({"language": lang}, "cancel_download"))
            if os.path.exists(file_path):
                os.remove(file_path)
            return

        # ارسال فایل
        if ext in ["mp3", "m4a"]:
            await bot.send_audio(chat_id=user_id, audio=open(file_path, "rb"), caption=title)
        else:
            await bot.send_video(chat_id=user_id, video=open(file_path, "rb"), caption=title)

        await msg.delete()

        # ذخیره در دیتابیس
        save_download(user_id, url, title)

        os.remove(file_path)

    except Exception as e:
        await msg.edit_text(t({"language": lang}, "download_error"))


def cancel_download(user_id):
    if user_id in cancel_flags:
        cancel_flags[user_id] = True
