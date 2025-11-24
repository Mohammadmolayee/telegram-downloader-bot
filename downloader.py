# downloader.py
import os
import glob
import tempfile
import shutil
import asyncio
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
import shutil as shmod

from config import DOWNLOAD_FOLDER, MAX_VIDEO_DOC_SIZE, YTDL_DEFAULT_VIDEO_FORMAT, YTDL_DEFAULT_AUDIO_FORMAT
import database as db

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

download_queue: asyncio.Queue = asyncio.Queue()
canceled_jobs: set = set()

_executor = ThreadPoolExecutor(max_workers=1)

def _has_ffmpeg() -> bool:
    return shmod.which("ffmpeg") is not None

def _run_yt_dlp(ydl_opts, url, tmpdir):
    """
    Blocking call - executed in threadpool
    Returns (file_path, info_dict)
    """
    # ensure outtmpl directory exists in opts
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    # try to find the downloaded file in tmpdir
    files = glob.glob(os.path.join(tmpdir, "*"))
    files = sorted(files, key=lambda p: os.path.getmtime(p), reverse=True)
    return (files[0] if files else None, info)

async def enqueue_download(user_id: int, chat_id: int, url: str):
    job_id = os.urandom(8).hex()
    await download_queue.put({"id": job_id, "user_id": user_id, "chat_id": chat_id, "url": url})
    return job_id

async def _process_job(bot, item):
    job_id = item["id"]
    user_id = item["user_id"]
    chat_id = item["chat_id"]
    url = item["url"]

    # notify
    try:
        status = await bot.send_message(chat_id, "⏳ در حال پردازش دانلود...")
    except Exception:
        status = None

    # check cancel
    if job_id in canceled_jobs:
        if status:
            try: await bot.send_message(chat_id, "🚫 دانلود لغو شد."); await status.delete() 
            except: pass
        return

    tmpdir = tempfile.mkdtemp(dir=DOWNLOAD_FOLDER)
    out_path = None
    info = None
    try:
        lower = url.lower()
        is_audio = any(x in lower for x in ("soundcloud", "spotify"))
        has_ffmpeg = _has_ffmpeg()

        if is_audio:
            # audio options
            if has_ffmpeg:
                ydl_opts = {
                    "format": YTDL_DEFAULT_AUDIO_FORMAT,
                    "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                    "noplaylist": True,
                    "quiet": True,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }]
                }
            else:
                ydl_opts = {
                    "format": YTDL_DEFAULT_AUDIO_FORMAT,
                    "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                    "noplaylist": True,
                    "quiet": True,
                }
        else:
            # video options - add headers for tiktok/user-agent to improve extraction
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            if has_ffmpeg:
                ydl_opts = {
                    "format": YTDL_DEFAULT_VIDEO_FORMAT,
                    "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                    "merge_output_format": "mp4",
                    "noplaylist": True,
                    "quiet": True,
                    "headers": headers,
                }
            else:
                # fallback when no ffmpeg: try produce mp4 directly
                ydl_opts = {
                    "format": "mp4/best",
                    "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                    "noplaylist": True,
                    "quiet": True,
                    "headers": headers,
                }

        loop = asyncio.get_running_loop()
        out_path, info = await loop.run_in_executor(_executor, _run_yt_dlp, ydl_opts, url, tmpdir)

        if job_id in canceled_jobs:
            if status:
                try: await bot.send_message(chat_id, "🚫 دانلود لغو شد."); await status.delete()
                except: pass
            return

        if not out_path or not os.path.exists(out_path):
            try:
                await bot.send_message(chat_id, "❌ فایل دانلود نشد یا پیدا نشد.")
            except:
                pass
            return

        size = os.path.getsize(out_path)
        title = info.get("title", "file")
        extractor = info.get("extractor", "unknown")

        # send file: if audio preferred as mp3 and ffmpeg used, file ext likely .mp3
        ext = os.path.splitext(out_path)[1].lower()
        try:
            if ext in (".mp3",) or any(x in out_path.lower() for x in [".mp3"]):
                with open(out_path, "rb") as f:
                    await bot.send_audio(chat_id, f, caption=title)
            else:
                # for video or other audio formats, send as document if large or as video if mp4
                if ext in (".mp4", ".mkv", ".webm"):
                    with open(out_path, "rb") as f:
                        # if mp4 send as video, else document
                        if ext == ".mp4":
                            await bot.send_video(chat_id, f, caption=title)
                        else:
                            await bot.send_document(chat_id, f, caption=title)
                else:
                    # fallback: send as document
                    with open(out_path, "rb") as f:
                        await bot.send_document(chat_id, f, caption=title)
        except Exception as e:
            try:
                await bot.send_message(chat_id, f"❌ خطا در ارسال فایل: {e}")
            except:
                pass

        # save to db
        db.save_download(user_id, extractor, url, title, size)

    except Exception as e:
        try:
            await bot.send_message(chat_id, f"❌ خطا در دانلود: {e}")
        except:
            pass
    finally:
        try:
            shutil.rmtree(tmpdir)
        except:
            pass
        if status:
            try:
                await status.delete()
            except:
                pass

async def worker_loop(app):
    bot = app.bot
    while True:
        try:
            item = await download_queue.get()
            if item["id"] in canceled_jobs:
                download_queue.task_done()
                continue
            await _process_job(bot, item)
            download_queue.task_done()
        except Exception:
            await asyncio.sleep(1)

async def cleanup_loop():
    while True:
        try:
            now = asyncio.get_event_loop().time()
            for name in os.listdir(DOWNLOAD_FOLDER):
                full = os.path.join(DOWNLOAD_FOLDER, name)
                try:
                    if os.path.isdir(full):
                        # remove directories older than 1 hour
                        if (asyncio.get_event_loop().time() - os.path.getmtime(full)) > 3600:
                            shutil.rmtree(full, ignore_errors=True)
                except:
                    pass
        except:
            pass
        await asyncio.sleep(600)
