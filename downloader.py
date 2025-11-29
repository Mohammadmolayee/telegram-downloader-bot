import asyncio, os, glob
from yt_dlp import YoutubeDL
from database import add_download, set_download_status
from telegram import InputFile

RUNNING = {}  # user_id -> asyncio.Task

def detect_platform(url: str):
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "tiktok.com" in u:
        return "tiktok"
    if "soundcloud.com" in u:
        return "soundcloud"
    if "instagram.com" in u or "instagr.am" in u:
        return "instagram"
    if "spotify.com" in u:
        return "spotify"
    return "unknown"

def _run_download_sync(url, outdir):
    opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestaudio/best",
        "outtmpl": os.path.join(outdir, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "merge_output_format": "mp4",
        "quiet": True,
        "retries": 3,
    }
    os.makedirs(outdir, exist_ok=True)
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return info

async def _download_task(user_id, url, bot, reply_message, dl_id):
    outdir = f"temp/{user_id}"
    try:
        info = await asyncio.to_thread(_run_download_sync, url, outdir)
        files = glob.glob(f"{outdir}/*")
        if not files:
            await reply_message.edit_text("❌ فایل یافت نشد.")
            set_download_status(dl_id, "error")
            return
        # pick largest file
        files.sort(key=lambda p: os.path.getsize(p), reverse=True)
        file_path = files[0]
        await bot.send_document(chat_id=user_id, document=InputFile(file_path),
                                caption=f"Downloaded by @professional_dawnloder_bot")
        set_download_status(dl_id, "done", os.path.basename(file_path))
        await reply_message.edit_text("✔ دانلود تمام شد.")
    except asyncio.CancelledError:
        set_download_status(dl_id, "cancelled")
        try: await reply_message.edit_text("❌ دانلود لغو شد.")
        except: pass
    except Exception as e:
        set_download_status(dl_id, "error")
        try: await reply_message.edit_text("❌ خطا در دانلود.")
        except: pass
    finally:
        # cleanup
        try:
            for f in glob.glob(f"{outdir}/*"): os.remove(f)
            os.rmdir(outdir)
        except Exception: pass
        RUNNING.pop(user_id, None)

async def start_download(user_id, url, bot, reply_message):
    if user_id in RUNNING:
        await reply_message.edit_text("⚠️ شما یک دانلود فعال دارید. ابتدا لغو کن.")
        return
    dl_id = add_download(user_id, url, detect_platform(url), "", "running")
    task = asyncio.create_task(_download_task(user_id, url, bot, reply_message, dl_id))
    RUNNING[user_id] = task
    return dl_id

def cancel_download(user_id):
    t = RUNNING.get(user_id)
    if not t: return False
    t.cancel(); return True
