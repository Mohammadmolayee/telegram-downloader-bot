# downloader.py
import os
import asyncio
import shutil
import yt_dlp
from database import save_download
from messages import t

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
_cancel_flags = {}

def _has_ffmpeg():
    return shutil.which("ffmpeg") is not None

def _opts(outtmpl):
    opts = {"format": "best[ext=mp4]/best", "outtmpl": outtmpl, "noplaylist": True, "nopart": True, "quiet": True, "no_warnings": True}
    if _has_ffmpeg():
        opts["merge_output_format"] = "mp4"
    return opts

def _blocking_download(url, outtmpl):
    with yt_dlp.YoutubeDL(_opts(outtmpl)) as ydl:
        info = ydl.extract_info(url, download=True)
    return info

async def download_and_send(user_id, url, bot, lang):
    status_msg = await bot.send_message(chat_id=user_id, text=t({"language": lang}, "downloading"))
    outtmpl = os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s")
    try:
        info = await asyncio.to_thread(_blocking_download, url, outtmpl)
    except Exception:
        try:
            await bot.edit_message_text(chat_id=user_id, message_id=status_msg.message_id, text=t({"language": lang}, "download_error"))
        except Exception:
            pass
        return

    if _cancel_flags.get(user_id):
        _cancel_flags.pop(user_id, None)
        try:
            await bot.edit_message_text(chat_id=user_id, message_id=status_msg.message_id, text=t({"language": lang}, "cancel_download"))
        except Exception:
            pass
        return

    file_id = info.get("id")
    title = info.get("title") or "file"
    ext = info.get("ext") or "mp4"
    file_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.{ext}")
    if not os.path.exists(file_path):
        cand = [f for f in os.listdir(DOWNLOAD_DIR) if f.startswith(file_id)]
        if cand:
            file_path = os.path.join(DOWNLOAD_DIR, cand[0])
        else:
            await bot.edit_message_text(chat_id=user_id, message_id=status_msg.message_id, text=t({"language": lang}, "download_error"))
            return

    try:
        bot_username = bot.username or "@professional_dawnloder_bot"
    except Exception:
        bot_username = "@professional_dawnloder_bot"

    by_line = t({"language": lang}, "download_by").format(bot_username=bot_username)
    details = t({"language": lang}, "download_details_line").format(title=title, url=url, by_line=by_line)

    try:
        audio_exts = {"mp3", "m4a", "aac", "opus", "wav"}
        if ext in audio_exts or (info.get("acodec") and not info.get("vcodec")):
            with open(file_path, "rb") as fh:
                await bot.send_audio(chat_id=user_id, audio=fh, caption=details)
            ftype = "audio"
        else:
            try:
                with open(file_path, "rb") as fh:
                    await bot.send_video(chat_id=user_id, video=fh, caption=details)
                ftype = "video"
            except Exception:
                with open(file_path, "rb") as fh:
                    await bot.send_document(chat_id=user_id, document=fh, caption=details)
                ftype = "document"
    except Exception:
        try:
            await bot.edit_message_text(chat_id=user_id, message_id=status_msg.message_id, text=t({"language": lang}, "download_error"))
        except Exception:
            pass
        try:
            os.remove(file_path)
        except Exception:
            pass
        return

    try:
        await bot.edit_message_text(chat_id=user_id, message_id=status_msg.message_id, text=t({"language": lang}, "download_finished"))
    except Exception:
        pass

    try:
        save_download(user_id, url, title, ftype)
    except Exception:
        pass

    try:
        os.remove(file_path)
    except Exception:
        pass

async def start_download_task(application, user_id, url, lang):
    async def job():
        bot = application.bot
        await download_and_send(user_id, url, bot, lang)
    try:
        application.create_task(job())
    except Exception:
        asyncio.create_task(job())

def cancel_download(user_id):
    _cancel_flags[user_id] = True
