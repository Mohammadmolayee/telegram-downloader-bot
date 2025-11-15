import os
import json
import yt_dlp
import tempfile
import glob
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("TOKEN not set")

user_quality = {}
temp_message = {}
cancel_flags = {}

DOWNLOAD_FOLDER = "/tmp/downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! /menu بزن")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("720p", callback_data='q_720')],
        [InlineKeyboardButton("360p", callback_data='q_360')],
        [InlineKeyboardButton("صوت", callback_data='q_audio')],
    ]
    await update.message.reply_text("کیفیت:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data.startswith('cancel_'):
        uid2 = int(q.data.split('_')[1])
        if uid2 == uid:
            cancel_flags[uid2] = True
            if uid2 in temp_message:
                await temp_message[uid2].edit_text("لغو شد!")
        return

    qmap = {'q_720': 'best[height<=720]', 'q_360': 'best[height<=360]', 'q_audio': 'bestaudio'}
    if q.data in qmap:
        user_quality[uid] = qmap[q.data]
        await q.edit_message_text("لینک بفرست")
    else:
        await q.edit_message_text("خطا")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    url = update.message.text.strip()

    if uid not in user_quality:
        await update.message.reply_text("اول /menu")
        return

    msg = await update.message.reply_text(
        "دانلود... ⏳",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data=f'cancel_{uid}')]])
    )
    temp_message[uid] = msg
    cancel_flags[uid] = False

    cookies_path = None
    if os.getenv('COOKIES_FILE'):
        tmp = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
        tmp.write(os.getenv('COOKIES_FILE'))
        tmp.close()
        cookies_path = tmp.name

    try:
        opts = {
            'format': user_quality[uid],
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'noplaylist': True,
            'cookiefile': cookies_path,
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        if not cancel_flags.get(uid, False):
            await msg.edit_text(f"خطا: {str(e)}")
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
                if 'audio' in user_quality[uid]:
                    await update.message.reply_audio(f, caption=info.get('title', 'صوت'))
                else:
                    await update.message.reply_video(f, caption=info.get('title', 'ویدیو'))
            os.remove(fpath)
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"خطا در ارسال: {e}")
    else:
        await msg.edit_text("فایل نیست!")

    cleanup(uid)
    if cookies_path and os.path.exists(cookies_path):
        os.unlink(cookies_path)

def cleanup(uid):
    temp_message.pop(uid, None)
    cancel_flags.pop(uid, None)

# --- Vercel handler ---
async def handler(request):
    if request.method != 'POST':
        return {'statusCode': 405, 'body': 'Method not allowed'}

    body = request.get_json() or json.loads(request.body.decode('utf-8'))
    update = Update.de_json(body, bot)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))

    await app.process_update(update)
    return {'statusCode': 200, 'body': 'OK'}

def main(request):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(handler(request))

# Vercel exports
__all__ = ['main']
