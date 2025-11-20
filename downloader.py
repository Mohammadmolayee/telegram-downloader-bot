# downloader.py
import os
import glob
import asyncio
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from config import DOWNLOAD_FOLDER, MAX_VIDEO_DOC_SIZE, YTDL_DEFAULT_VIDEO_FORMAT, YTDL_DEFAULT_AUDIO_FORMAT
import database as db

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# asyncio queue for jobs
download_queue: asyncio.Queue = asyncio.Queue()
# canceled job ids
canceled_jobs: set = set()

# executor for blocking yt-dlp calls
_executor = ThreadPoolExecutor(max_workers=1)

async def enqueue_download(user_id: int, chat_id: int, url: str):
    """
    called by bot when user sends link.
    returns job_id
    """
    job_id = os.urandom(8).hex()
    await download_queue.put({"id": job_id, "user_id": user_id, "chat_id": chat_id, "url": url})
    return job_id

def _run_yt_dlp(ydl_opts, url, tmpdir):
    """
    blocking call executed in threadpool
    returns path to file and info dict
    """
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # find file
        files = glob.glob(os.path.join(tmpdir, "*"))
        # pick newest
        if not files:
            # sometimes ydl writes to cwd with id.ext
            files = glob.glob(os.path.join(".", "*"))
        files = sorted(files, key=os.path.getmtime, reverse=True)
        return files[0] if files else None, info

async def _process_job(bot, item):
    job_id = item["id"]
    user_id = item["user_id"]
    chat_id = item["chat_id"]
    url = item["url"]

    status_msg = None
    try:
        status_msg = await bot.send_message(chat_id, "⏳ در حال پردازش دانلود...")
    except Exception:
        pass

    # check cancel before heavy work
    if job_id in canceled_jobs:
        try:
            if status_msg:
                await bot.send_message(chat_id, "🚫 دانلود لغو شد.")
        except Exception:
            pass
        return

    tmpdir = tempfile.mkdtemp(dir=DOWNLOAD_FOLDER)
    out_path = None
    info = None
    try:
        lower = url.lower()
        is_audio = any(x in lower for x in ("soundcloud", "spotify"))
        if is_audio:
            ydl_opts = {
                "format": YTDL_DEFAULT_AUDIO_FORMAT,
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                "noplaylist": True,
            }
        else:
            ydl_opts = {
                "format": YTDL_DEFAULT_VIDEO_FORMAT,
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                "merge_output_format": "mp4",
                "noplaylist": True,
            }

        loop = asyncio.get_running_loop()
        out_path, info = await loop.run_in_executor(_executor, _run_yt_dlp, ydl_opts, url, tmpdir)

        if job_id in canceled_jobs:
            # user canceled during download
            try:
                await bot.send_message(chat_id, "🚫 دانلود لغو شد.")
            except Exception:
                pass
            return

        if not out_path or not os.path.exists(out_path):
            try:
                await bot.send_message(chat_id, "❌ فایل دانلود نشد یا قابل پیدا کردن نیست.")
            except Exception:
                pass
            return

        size = os.path.getsize(out_path)
        title = info.get("title", "video")

        # choose send method
        if is_audio or size > MAX_VIDEO_DOC_SIZE:
            # send as document (safer for big files)
            try:
                with open(out_path, "rb") as f:
                    await bot.send_document(chat_id, f, caption=f"{title}")
            except Exception:
                pass
        else:
            try:
                with open(out_path, "rb") as f:
                    await bot.send_video(chat_id, f, caption=f"{title}")
            except Exception:
                pass

        # save record in DB
        db.save_download(user_id, info.get("extractor", "unknown"), url, title, size)

    except Exception as e:
        try:
            await bot.send_message(chat_id, f"❌ خطا در دانلود: {e}")
        except Exception:
            pass
    finally:
        # cleanup
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
        if status_msg:
            try:
                await status_msg.delete()
            except Exception:
                pass

async def worker_loop(app):
    """
    main worker loop — scheduled from bot.post_init (safe)
    """
    bot = app.bot
    while True:
        try:
            item = await download_queue.get()
            # skip canceled
            if item["id"] in canceled_jobs:
                download_queue.task_done()
                continue
            await _process_job(bot, item)
            download_queue.task_done()
        except Exception:
            # never crash — sleep and continue
            await asyncio.sleep(1)

async def cleanup_loop():
    """
    periodically cleanup lingering files (safety)
    """
    import time
    while True:
        try:
            now = time.time()
            for p in os.listdir(DOWNLOAD_FOLDER):
                full = os.path.join(DOWNLOAD_FOLDER, p)
                try:
                    if os.path.isdir(full):
                        # check age of directory
                        m = os.path.getmtime(full)
                        if now - m > 3600:  # 1 hour
                            shutil.rmtree(full, ignore_errors=True)
                except Exception:
                    pass
        except Exception:
            pass
        await asyncio.sleep(600)
