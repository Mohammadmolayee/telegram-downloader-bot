import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

# توکن بات (واقعی رو بذار)
TOKEN = '7648405518:AAEHsa7g4syYA6_QIE-GJl3U_AKpTYSA4C4'

# فولدر دانلود
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# کیفیت انتخابی هر کاربر
user_quality = {}

# برای لغو دانلود
cancel_flags = {}  # {user_id: True/False}

# پیام موقت برای دکمه لغو
temp_message = {}


# دستور /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'سلام! بات دانلودر حرفه‌ای فعال شد!\n'
        'برای انتخاب کیفیت: /menu بزن'
    )


# دستور /menu
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("720p (کیفیت بالا)", callback_data='quality_720')],
        [InlineKeyboardButton("360p (حجم کم)", callback_data='quality_360')],
        [InlineKeyboardButton("صوت فقط (MP3)", callback_data='quality_audio')],
        [InlineKeyboardButton("راهنما", callback_data='help')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('کیفیت رو انتخاب کن:', reply_markup=reply_markup)


# دکمه‌ها (منو + لغو)
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

        # دکمه لغو
    if data.startswith('cancel_'):
        user_id = int(data.split('_')[1])
        cancel_flags[user_id] = True
        if user_id in temp_message:
            await temp_message[user_id].edit_text("در حال لغو دانلود...", reply_markup=None)
        return

    # دکمه‌های منو
    user_id = query.from_user.id
    if data == 'help':
        await query.edit_message_text('راهنما: کیفیت → لینک → لغو', reply_markup=None)
        return

    if data == 'quality_720':
        user_quality[user_id] = 'best[height<=720]/best'
        text = '720p انتخاب شد!'
    elif data == 'quality_360':
        user_quality[user_id] = 'best[height<=360]/best'
        text = '360p انتخاب شد!'
    elif data == 'quality_audio':
        user_quality[user_id] = 'bestaudio/best'
        text = 'صوت فقط انتخاب شد!'
    else:
        text = 'دستور نامعتبر!'

    await query.edit_message_text(text)

    # دکمه راهنما
    if query.data == 'help':
        await query.edit_message_text(
            'راهنما:\n'
            '1. کیفیت رو از منو انتخاب کن\n'
            '2. لینک ویدیو رو بفرست\n'
            '3. هر وقت خواستی "لغو" بزن!',
            reply_markup=None
        )
        return

    # ذخیره کیفیت
    if query.data == 'quality_720':
        user_quality[user_id] = 'best[height<=720]/best'
        text = '720p انتخاب شد! حالا لینک رو بفرست.'
    elif query.data == 'quality_360':
        user_quality[user_id] = 'best[height<=360]/best'
        text = '360p انتخاب شد! حالا لینک رو بفرست.'
    elif query.data == 'quality_audio':
        user_quality[user_id] = 'bestaudio/best'
        text = 'صوت فقط انتخاب شد! حالا لینک رو بفرست.'
    else:
        text = 'دستور نامعتبر!'

    await query.edit_message_text(text)


# دانلود در پس‌زمینه + قابلیت لغو
async def download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    url = update.message.text

    if user_id not in user_quality:
        await update.message.reply_text('اول کیفیت رو از /menu انتخاب کن!')
        return

    # پیام با دکمه لغو
    keyboard = [[InlineKeyboardButton("لغو", callback_data=f'cancel_{user_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = await update.message.reply_text(
        "در حال بررسی لینک... ⏳",
        reply_markup=reply_markup
    )
    temp_message[user_id] = msg
    cancel_flags[user_id] = False  # هنوز لغو نشده

    # --- مرحله ۱: اطلاعات بدون دانلود ---
    ydl_opts_info = {
        'format': user_quality[user_id],
        'skip_download': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        await msg.edit_text(f"خطا: {str(e)}", reply_markup=None)
        cleanup(user_id)
        return

    # --- مرحله ۲: چک حجم ---
    filesize = info.get('filesize') or info.get('filesize_approx')
    if filesize and filesize > 50 * 1024 * 1024:
        await msg.edit_text(
            f"فایل خیلی بزرگه!\nحجم: {filesize // (1024*1024)} مگابایت",
            reply_markup=None
        )
        cleanup(user_id)
        return

    await msg.edit_text("حجم OK! در حال دانلود... ⏳", reply_markup=reply_markup)

    # --- مرحله ۳: دانلود در پس‌زمینه ---
    def download_task():
        if cancel_flags.get(user_id, False):
            return

        ydl_opts_download = {
            'format': user_quality[user_id],
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'noplaylist': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                ydl.download([url])
            return True
        except:
            return False

    # اجرای دانلود در ترد جدا
    import threading
    thread = threading.Thread(target=download_task)
    thread.start()

    # چک کردن هر 1 ثانیه
    while thread.is_alive():
        if cancel_flags.get(user_id, False):
            await msg.edit_text("دانلود لغو شد!", reply_markup=None)
            cleanup(user_id)
            return
        await asyncio.sleep(1)

    # دانلود تموم شد
    if thread.result:  # موفق
        filename = f"{DOWNLOAD_FOLDER}/{info['title']}.{info['ext']}"
        if os.path.exists(filename):
            if 'bestaudio' in user_quality[user_id]:
                with open(filename, 'rb') as f:
                    await update.message.reply_audio(f, caption=info.get('title'))
            else:
                with open(filename, 'rb') as f:
                    await update.message.reply_video(f, caption=info.get('title'))
            os.remove(filename)
        await msg.delete()
    else:
        await msg.edit_text("خطا در دانلود!", reply_markup=None)

    cleanup(user_id)


def cleanup(user_id):
    if user_id in temp_message:
        del temp_message[user_id]
    if user_id in cancel_flags:
        del cancel_flags[user_id]


# شروع بات
if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()

    # دستورات و دکمه‌ها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button_click))  # همه دکمه‌ها (منو + لغو)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send))

    print("بات دانلودر حرفه‌ای آنلاین شد!")
    app.run_polling()