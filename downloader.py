# downloader.py
import os
import shutil
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from database import save_download, get_user
from messages import t

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# cancel flags
_cancel_flags = {}

def _has_ffmpeg():
    return shutil.which("ffmpeg") is not None

def _build_opts(outtmpl):
    # Prefer single-file mp4 if available to avoid needing ffmpeg merge.
    opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "nopart": True,
        "quiet": True,
        "no_warnings": True,
    }
    # If ffmpeg present, allow merging if necessary
    if _has_ffmpeg():
        opts["merge_output_format"] = "mp4"
    return opts

def _blocking_download(url, outtmpl):
    ydl_opts = _build_opts(outtmpl)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return info

async def download_and_send(user_id, url, bot, lang):
    """
    Downloads content in a thread and sends it via bot (works for audio/video/files).
    """
    # create a temporary outtmpl: downloads/{id}.%(ext)s
    outtmpl = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
    loop = asyncio.get_running_loop()

    try:
        # run blocking download in thread
        info = await asyncio.to_thread(_blocking_download, url, outtmpl)
    except Exception as e:
        # send error message
        try:
            await bot.send_message(chat_id=user_id, text=t({"language": lang}, "download_error"))
        except Exception:
            pass
        return

    # if user canceled
    if _cancel_flags.get(user_id):
        _cancel_flags.pop(user_id, None)
        try:
            await bot.send_message(chat_id=user_id, text=t({"language": lang}, "cancel_download"))
        except Exception:
            pass
        return

    # find file
    file_id = info.get("id")
    ext = info.get("ext") or "mp4"
    title = info.get("title") or "file"
    file_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.{ext}")
    if not os.path.exists(file_path):
        # try to search
        candidates = [f for f in os.listdir(DOWNLOAD_DIR) if f.startswith(file_id)]
        if candidates:
            file_path = os.path.join(DOWNLOAD_DIR, candidates[0])
        else:
            await bot.send_message(chat_id=user_id, text=t({"language": lang}, "download_error"))
            return

    # send file (choose audio if audio-only)
    try:
        # get mimetype from ext heuristics
        audio_exts = {"mp3", "m4a", "aac", "opus", "wav"}
        if ext in audio_exts or info.get("acodec") and not info.get("vcodec"):
            await bot.send_audio(chat_id=user_id, audio=open(file_path, "rb"), caption=title)
            ftype = "audio"
        else:
            # use send_video for typical mp4
            await bot.send_video(chat_id=user_id, video=open(file_path, "rb"), caption=title)
            ftype = "video"
    except Exception:
        # fallback: send as document
        try:
            await bot.send_document(chat_id=user_id, document=open(file_path, "rb"), caption=title)
            ftype = "document"
        except Exception:
            await bot.send_message(chat_id=user_id, text=t({"language": lang}, "download_error"))
            return
    finally:
        # remove file
        try:
            os.remove(file_path)
        except Exception:
            pass

    # save record
    save_download(user_id, url, title, ftype)


# exposed API
async def start_download_task(application, user_id, url, lang):
    """
    Schedules a background download task that uses application.bot
    """
    # schedule via application.create_task or asyncio.create_task
    # wrapper to call download_and_send with bot
    bot = application.bot
    async def _job():
        await bot.send_message(chat_id=user_id, text=t({"language": lang}, "downloading"))
        await download_and_send(user_id, url, bot, lang)
    task = application.create_task(_job())
    return task

def cancel_download(user_id):
    _cancel_flags[user_id] = True
