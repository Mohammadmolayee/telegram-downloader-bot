# ========================================
# ربات دانلودر اینستاگرام - نسخه حرفه‌ای
# نویسنده: حاجی (با کمک هوش مصنوعی)
# تاریخ: 16 نوامبر 2025
# ========================================

import os
import yt_dlp
import glob
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# -------------------------------
# تنظیمات اصلی (اینجا تغییر بده)
# -------------------------------
TOKEN = os.getenv('TOKEN')  # توکن ربات (از BotFather)
if not TOKEN:
    raise ValueError("TOKEN رو در Railway Variables بذار!")

DOWNLOAD_FOLDER = "downloads"  # پوشه موقت دانلود
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)  # اگه نبود، بساز

# متغیرهای موقت برای هر کاربر
temp_message = {}   # پیام "در حال دانلود..." رو ذخیره می‌کنه
cancel_flags = {}   # آیا کاربر دکمه لغو رو زده؟

# -------------------------------
# دستور /start — خوش‌آمدگویی
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی کاربر /start بزنه"""
    await update.message.reply_text(
        "ربات دانلودر اینستاگرام\n"
        "فقط لینک ریل یا پست بفرست\n"
        "کیفیت: بهترین mp4 موجود\n"
        "شروع کن!"
    )

# -------------------------------
# تابع دانلود — قلب ربات
# -------------------------------
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هر وقت کاربر لینک بفرسته"""
    user_id = update.message.from_user.id
    url = update.message.text.strip()

    # فقط لینک اینستاگرام قبول کن
    if "instagram.com" not in url:
        await update.message.reply_text("لطفاً فقط لینک اینستاگرام بفرست")
        return

    # پیام "در حال دانلود..." با دکمه لغو
    msg = await update.message.reply_text(
        "در حال دانلود از اینستاگرام... ⏳",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("لغو", callback_data=f'cancel_{user_id}')]
        ])
    )
    temp_message[user_id] = msg
    cancel_flags[user_id] = False  # هنوز لغو نشده

    # کوکی (برای دسترسی بهتر به اینستاگرام)
    cookies_path = None
    if os.getenv('COOKIES_FILE'):
        tmp = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False)
        tmp.write(os.getenv('COOKIES_FILE'))
        tmp.close()
        cookies_path = tmp.name

    try:
        # تنظیمات yt-dlp برای اینستاگرام
        ydl_opts = {
            'format': 'best[ext=mp4]/best',           # بهترین mp4
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',  # اسم فایل: ID ویدیو
            'noplaylist': True,
            'cookiefile': cookies_path,
            'quiet': True,
            'no_warnings': True,
            'merge_output_format': 'mp4',
            'retries': 5,
            'fragment_retries': 5,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id', 'unknown')
            title = info.get('title', 'ویدیو اینستاگرام')

        # فایل دانلود شده
        file_path = glob.glob(f"{DOWNLOAD_FOLDER}/{video_id}.*")[0]

    except Exception as e:
        # خطا در دانلود
        if not cancel_flags.get(user_id, False):
            await msg.edit_text(f"خطا در دانلود:\n{str(e)[:100]}")
        cleanup(user_id, cookies_path)
        return

    # کاربر لغو کرده؟
    if cancel_flags.get(user_id, False):
        cleanup(user_id, cookies_path)
        return

    # ارسال ویدیو
    try:
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video_file, caption=title)
        os.remove(file_path)  # پاک کردن فایل
        await msg.delete()    # پاک کردن پیام "در حال دانلود"
    except Exception as e:
        await msg.edit_text(f"خطا در ارسال: {e}")

    cleanup(user_id, cookies_path)

# -------------------------------
# دکمه لغو
# -------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی کاربر دکمه لغو رو بزنه"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data.startswith('cancel_'):
        clicked_user_id = int(query.data.split('_')[1])
        if clicked_user_id == user_id and clicked_user_id in temp_message:
            cancel_flags[clicked_user_id] = True
            await temp_message[clicked_user_id].edit_text("لغو شد!")

# -------------------------------
# تابع پاکسازی
# -------------------------------
def cleanup(user_id, cookies_path=None):
    """پاک کردن فایل‌ها و متغیرها"""
    temp_message.pop(user_id, None)
    cancel_flags.pop(user_id, None)
    if cookies_path and os.path.exists(cookies_path):
        os.unlink(cookies_path)

# -------------------------------
# اجرای ربات (polling)
# -------------------------------
def main():
    app = Application.builder().token(TOKEN).build()

    # هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))

    print("ربات دانلودر اینستاگرام فعال شد...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
