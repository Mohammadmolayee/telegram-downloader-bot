import os
import yt_dlp
import tempfile
import glob
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("TOKEN not set")

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

user_quality = {}
temp_message = {}
cancel_flags = {}

# --- دستورات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! ربات دانلودر حرفه‌ای\n"
        "ویدیوهای زیر 45 مگابایت رو کامل دانلود می‌کنه\n"
        "برای ویدیوهای بزرگ: کیفیت پایین‌تر انتخاب کن\n"
        "/menu بزن"
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("720p", callback_data='q_720')],
        [InlineKeyboardButton("360p", callback_data='q_360')],
        [InlineKeyboardButton("صوت", callback_data='q_audio')],
    ]
    await update.message.reply_text("کیفیت رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(keyboard))

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

    qmap = {
        'q_720': {'format': 'best[height<=720]/best', 'name': '720p'},
        'q_360': {'format': 'best[height<=360]/best', 'name': '360p'},
        'q_audio': {'format': 'bestaudio/best', 'name': 'صوت'},
    }
    if q.data in qmap:
        user_quality[uid] = qmap[q.data]
        await q.edit_message_text(f"کیفیت {qmap[q.data]['name']} انتخاب شد. لینک بفرست")
    else:
        await q.edit_message_text("خطا")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    url = update.message.text.strip()

    if uid not in user_quality:
        await update.message.reply_text("اول /menu بزن")
        return

    msg = await update.message.reply_text(
        "در حال دانلود... ⏳",
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
        # فرمت کیفیت
        format_str = user_quality[uid]['format']
        name = user_quality[uid]['name']

        # اگر صوت باشه، حجم مهم نیست
        if 'audio' in format_str:
            final_format = format_str
        else:
            final_format = f'{format_str}[filesize<45M]/best[filesize<45M]'

        opts = {
            'format': final_format,
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'noplaylist': True,
            'cookiefile': cookies_path,
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',  # برای ویدیو
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'فایل')
            duration = info.get('duration', 0)

        # هشدار برای ویدیوهای طولانی
        if duration and duration > 900 and 'audio' not in format_str:  # 15 دقیقه
            await msg.edit_text(
                f"ویدیو {duration//60} دقیقه‌ای است!\n"
                f"کیفیت {name} ممکنه کامل نباشه (زیر 45 مگ)\n"
                f"برای کامل بودن: 360p انتخاب کن"
            )
            return

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
                if 'audio' in user_quality[uid]['format']:
                    await update.message.reply_audio(f, caption=title)
                else:
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

def cleanup(uid):
    temp_message.pop(uid, None)
    cancel_flags.pop(uid, None)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))

    print("Bot is running with polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
