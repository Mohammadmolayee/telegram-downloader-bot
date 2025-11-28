import os
import yt_dlp
import requests

async def download_media(url, update, lang):
    msg = await update.message.reply_text("⏳ در حال دانلود..." if lang=="fa" else "⏳ Downloading...")

    try:
        ydl_opts = {
            "outtmpl": "file.%(ext)s",
            "format": "best"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        for f in os.listdir():
            if f.startswith("file."):
                await update.message.reply_document(open(f, "rb"))
                os.remove(f)

        await msg.edit_text("✔ دانلود انجام شد" if lang=="fa" else "✔ Done")

    except Exception as e:
        await msg.edit_text("❌ خطا در دانلود" if lang=="fa" else "❌ Error")
