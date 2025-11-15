import os
import yt_dlp
import glob
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("TOKEN not set")

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

temp_message = {}
cancel_flags = {}

# --- دستورات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ربات دانلودر اینستاگرام\n"
        "فقط لینک ریل یا پست بفرست\n"
        "کیفیت: بهترین ممکن (mp4)\n"
        "شروع کن!"
    )

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    url = update.message.text.strip()

    # چک کن لینک اینستاگرام باشه
    if "instagram.com" not in url:
        await update.message.reply_text("لطفاً فقط لینک اینستاگرام بفرست")
        return

    msg = await update.message.reply_text(
        "در حال دانلود از اینستاگرام... ⏳",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data=f'cancel_{uid}')]])
    )
    temp_message[uid] = msg
    cancel_flags[uid] = False

    # کوکی (اختیاری)
    cookies_path = None
    if os.getenv('COOKIES_FILE'):
        tmp = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
        tmp.write(os.getenv('COOKIES_FILE'))
        tmp.close()
        cookies_path = tmp.name

    try:
        # تنظیمات مخصوص اینستاگرام
        opts = {
            'format': 'best[ext=mp4]/best',  # بهترین mp4 موجود
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'noplaylist': True,
            'cookiefile': cookies_path,
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',  # همیشه به mp4 تبدیل کن
            'retries': 5,
            'fragment_retries': 5,
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'ویدیو اینستاگرام')

    except Exception as e:
        if not cancel_flags.get(uid, False):
            await msg.edit_text(f"خطا: {str(e)[:100]}")
        cleanup(uid)
        if cookies_path and os.path.exists(cookies_path):
            os.unlink(cookies_path)
        return

    if cancel_flags.get(uid, False):
        cleanup(uid)
        if cookies_path and os.path.exists(cookies_path):
            os.unlink(cookies_path)
        return

    files = glob.glob(f"{DOWNLOAD_FOLDER}/*")
    if files:
        fpath = files[0]
        try:
            with open(fpath, 'rb') as f:
                await update.message.reply_video(f, caption=title)
            os.remove(fpath)
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"خطا در ارسال: {e}")
    else:
        await msg.edit_text("فایل پیدا نشد!")

    cleanup(uid)
    if cookies_path and os.path.exists(cookies_path):
        os.unlink(cookies_path)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data.startswith('cancel_'):
        uid2 = int(q.data.split('_')[1])
        if uid2 == uid and uid2 in temp_message:
            cancel_flags[uid2] = True
            await temp_message[uid2].edit_text("لغو شد!")
        return

def cleanup(uid):
    temp_message.pop(uid, None)
    cancel_flags.pop(uid, None)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))

    print("Instagram Downloader Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
