# ========================================
# ربات دانلودر حرفه‌ای - نسخه ساده
# فقط خوش‌آمدگویی (متن آپدیت شده)
# ========================================

import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# -------------------------------
# تنظیمات
# -------------------------------
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("TOKEN رو در Railway Variables بذار!")

# -------------------------------
# دستور /start — خوش‌آمدگویی آپدیت شده
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی کاربر /start بزنه"""
    await update.message.reply_text(
        "سلام! به ربات دانلودر حرفه‌ای خوش اومدی\n"
        "اینجا می‌تونی:\n"
        "ویدیو و اهنگ هر پلتفرمی دانلود کنی\n"
        "پشتیبانی از تمامی پلتفرم ها : یوتیوب,اینستاگرام,تیک‌تاک,توییتر,فیسبوک,ساندکلود,اسپاتیفای و....\n"
        "فقط لینک رو بفرست، بقیه‌ش با ماست!"
    )

# -------------------------------
# اجرای ربات
# -------------------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("ربات دانلودر فعال شد...")
    app.run_polling()

if __name__ == '__main__':
    main()
