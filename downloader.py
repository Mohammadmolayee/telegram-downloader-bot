# downloader.py
import yt_dlp
import os
import uuid

async def download_media(url, bot, chat_id, lang):
    uid = str(uuid.uuid4())[:6]
    filename = f"dl_{uid}.mp4"

    ydl_opts = {
        "outtmpl": filename,
        "format": "mp4/bestaudio/best",
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as y:
            y.download([url])

        await bot.send_video(
            chat_id=chat_id,
            video=open(filename, "rb"),
            caption=f"✅ دانلود انجام شد!\n\n📥 Via @professional_dawnloder_bot"
        )

        os.remove(filename)
    except:
        await bot.send_message(chat_id, "❌ خطا در دانلود")
