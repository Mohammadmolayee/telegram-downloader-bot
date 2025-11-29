import asyncio, os, glob
from yt_dlp import YoutubeDL
from database import add_download, set_download_status
from telegram import InputFile

# نگهداری task های درحال اجرا {user_id: asyncio.Task}
RUNNING = {}

# helper to pick platform from url
def detect_platform(url):
    url = url.lower()
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "tiktok.com" in url:
        return "tiktok"
    if "soundcloud.com" in url:
        return "soundcloud"
    if "instagram.com" in url or "instagr.am" in url:
        return "instagram"
    if "spotify.com" in url:
        return "spotify"
    return "unknown"

async def download_media_task(user_id, url, bot, lang, reply_message):
    dl_id = add_download(user_id, url, detect_platform(url), "", "running")
    try:
        # use to_thread to not block
        def run_download():
            outtmpl = f"temp/{user_id}_%(id)s.%(ext)s"
            opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "outtmpl": outtmpl,
                "noplaylist": True,
                "merge_output_format": "mp4",
                "postprocessors": [{"key": "FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}],
            }
            os.makedirs("temp", exist_ok=True)
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info
        info = await asyncio.to_thread(run_download)

        # find file
        files = glob.glob(f"temp/{user_id}_*.*")
        if not files:
            await reply_message.edit_text("❌ فایل پیدا نشد.")
            set_download_status(dl_id, "error"); return
        file_path = files[0]
        await bot.send_document(chat_id=user_id, document=InputFile(file_path),
                                caption=f"Downloaded by @professional_dawnloder_bot")
        set_download_status(dl_id, "done")
        reply_message and await reply_message.edit_text("✔ دانلود تمام شد.")
        # cleanup
        for f in files:
            try: os.remove(f)
            except: pass
    except asyncio.CancelledError:
        set_download_status(dl_id, "cancelled")
        try: await reply_message.edit_text("❌ دانلود لغو شد.")
        except: pass
    except Exception as e:
        set_download_status(dl_id, "error")
        try: await reply_message.edit_text("❌ خطا در دانلود.")
        except: pass

async def start_download(user_id, url, bot, lang, reply_message):
    # stop existing
    if user_id in RUNNING:
        # do not start if already running (or you may queue)
        await reply_message.edit_text("⚠️ شما یک دانلود فعال دارید. برای لغو /cancel را بزنید.")
        return
    task = asyncio.create_task(download_media_task(user_id, url, bot, lang, reply_message))
    RUNNING[user_id] = task
    def _on_done(t):
        RUNNING.pop(user_id, None)
    task.add_done_callback(_on_done)

def cancel_download(user_id):
    t = RUNNING.get(user_id)
    if not t: return False
    t.cancel(); return True
