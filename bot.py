import os
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# فایل‌های پروژه
from database import (
    init_db, user_exists, create_user, login,
    get_user, set_language
)

from keyboards import (
    start_keyboard, panel_keyboard,
    language_inline
)

from downloader import download_media
from messages import t


# وضعیت ساخت حساب و ورود
user_state = {}
pending_data = {}


# -------------------------
# /start
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_exists(user_id):
        user = get_user(user_id)
        lang = user["language"]

        await update.message.reply_text(
            t(user, "start_member"),
            reply_markup=panel_keyboard(lang)
        )
    else:
        await update.message.reply_text(
            t({"language": "fa"}, "start_guest"),
            reply_markup=start_keyboard("fa")
        )


# -------------------------
# هندل پیام‌ها
# -------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = update.effective_user.id

    user = get_user(user_id)
    lang = user["language"] if user else "fa"

    # -------------------------
    # دکمه بازگشت
    # -------------------------
    if msg in ["🔙 بازگشت", "🔙 Back"]:
        if user:
            await update.message.reply_text(
                t(user, "start_member"),
                reply_markup=panel_keyboard(lang)
            )
        else:
            await update.message.reply_text(
                t({"language": "fa"}, "start_guest"),
                reply_markup=start_keyboard("fa")
            )
        return

    # -------------------------
    # دکمه‌های پنل مهمان
    # -------------------------
    if msg in ["📖 راهنما", "📖 Help"]:
        key = "help_guest" if not user else "help_member"
        await update.message.reply_text(t({"language": lang}, key))
        return

    if msg in ["📜 قوانین", "📜 Rules"]:
        await update.message.reply_text(t({"language": lang}, "rules"))
        return

    if msg in ["ℹ درباره ما", "ℹ About"]:
        await update.message.reply_text(t({"language": lang}, "about"))
        return

    if msg in ["🌐 زبان", "🌐 Language"]:
        await update.message.reply_text(
            t({"language": lang}, "choose_language"),
            reply_markup=language_inline()
        )
        return

    # -------------------------
    # ساخت حساب
    # -------------------------
    if msg in ["👤 ساخت حساب", "👤 Create Account"]:
        user_state[user_id] = "reg_name"
        await update.message.reply_text(t({"language": lang}, "reg_name"))
        return

    if user_state.get(user_id) == "reg_name":
        pending_data[user_id] = {"name": msg}
        user_state[user_id] = "reg_username"
        await update.message.reply_text(t({"language": lang}, "reg_username"))
        return

    if user_state.get(user_id) == "reg_username":
        pending_data[user_id]["username"] = msg
        user_state[user_id] = "reg_password"
        await update.message.reply_text(t({"language": lang}, "reg_password"))
        return

    if user_state.get(user_id) == "reg_password":
        info = pending_data[user_id]

        done = create_user(user_id, info["name"], info["username"], msg)
        user_state.pop(user_id, None)
        pending_data.pop(user_id, None)

        if done:
            await update.message.reply_text(
                t({"language": lang}, "reg_done"),
                reply_markup=panel_keyboard(lang)
            )
        else:
            await update.message.reply_text(
                t({"language": lang}, "reg_fail")
            )
        return

    # -------------------------
    # دانلود
    # -------------------------
    if msg.startswith("http"):
        await update.message.reply_text("⏳ فایل درحال پردازش است...")
        await download_media(update, context, msg, lang)
        return

    # اگر دستور ناشناخته بود
    await update.message.reply_text(
        t({"language": lang}, "unknown")
    )


# -------------------------
# کال‌بک برای انتخاب زبان
# -------------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data.startswith("lang_"):
        new_lang = data.split("_")[1]
        set_language(user_id, new_lang)

        await query.answer("زبان تغییر کرد")
        await query.edit_message_text(
            text=t({"language": new_lang}, "lang_changed")
        )


# -------------------------
# MAIN
# -------------------------
async def main():
    # دیتابیس
    init_db()

    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise Exception("❌ BOT_TOKEN در Railway تنظیم نشده!")

    app = Application.builder().token(TOKEN).build()

    # هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # اجرای ربات بدون بسته شدن لوپ
    await app.run_polling(close_loop=False)


if __name__ == "__main__":
    asyncio.run(main())
