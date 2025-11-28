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

from database import (
    init_db, user_exists, create_user, get_user,
    set_language, set_theme, login
)

from keyboards import (
    start_keyboard, panel_keyboard, language_inline,
    back_keyboard, settings_keyboard
)

from messages import t
from downloader import download_media


# ---------------------------
# حافظه وضعیت
# ---------------------------
user_state = {}     # مراحل ثبت‌نام / ورود
pending_data = {}   # ذخیره موقت اطلاعات ثبت‌نام


# ---------------------------
# /start
# ---------------------------
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


# ---------------------------
# پیام‌های معمولی
# ---------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text

    user = get_user(user_id)
    lang = user["language"] if user else "fa"

    # ---------------- BACK ----------------
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

    # ---------------- راهنما ----------------
    if msg in ["📖 راهنما", "📖 Help"]:
        key = "help_guest" if not user else "help_member"
        await update.message.reply_text(
            t({"language": lang}, key),
            reply_markup=back_keyboard(lang)
        )
        return

    # ---------------- قوانین ----------------
    if msg in ["📜 قوانین", "📜 Rules"]:
        await update.message.reply_text(
            t({"language": lang}, "rules"),
            reply_markup=back_keyboard(lang)
        )
        return

    # ---------------- درباره ما ----------------
    if msg in ["ℹ درباره ما", "ℹ About"]:
        await update.message.reply_text(
            t({"language": lang}, "about"),
            reply_markup=back_keyboard(lang)
        )
        return

    # ---------------- تغییر زبان ----------------
    if msg in ["🌐 زبان", "🌐 Language"]:
        await update.message.reply_text(
            t({"language": lang}, "choose_language"),
            reply_markup=language_inline()
        )
        return

    # ---------------- ساخت حساب ----------------
    if msg in ["👤 ساخت حساب", "👤 Create Account"]:
        user_state[user_id] = "reg_name"
        await update.message.reply_text(
            t({"language": lang}, "reg_name"),
            reply_markup=back_keyboard(lang)
        )
        return

    if user_state.get(user_id) == "reg_name":
        pending_data[user_id] = {"name": msg}
        user_state[user_id] = "reg_username"
        await update.message.reply_text(
            t({"language": lang}, "reg_username"),
            reply_markup=back_keyboard(lang)
        )
        return

    if user_state.get(user_id) == "reg_username":
        pending_data[user_id]["username"] = msg
        user_state[user_id] = "reg_password"
        await update.message.reply_text(
            t({"language": lang}, "reg_password"),
            reply_markup=back_keyboard(lang)
        )
        return

    if user_state.get(user_id) == "reg_password":
        info = pending_data[user_id]
        ok = create_user(user_id, info["name"], info["username"], msg)

        if ok:
            user_state.pop(user_id)
            pending_data.pop(user_id)
            await update.message.reply_text(
                t({"language": lang}, "reg_done"),
                reply_markup=panel_keyboard(lang)
            )
        else:
            await update.message.reply_text(
                t({"language": lang}, "reg_fail"),
                reply_markup=back_keyboard(lang)
            )
        return

    # ---------------- دانلود ----------------
    if msg.startswith("http"):
        await update.message.reply_text(
            t({"language": lang}, "downloading")
        )
        asyncio.create_task(
            download_media(user_id, msg, context.bot, lang)
        )
        return

    await update.message.reply_text(t({"language": lang}, "unknown"))


# ---------------------------
# Callback Handler
# ---------------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    user_id = query.from_user.id
    user = get_user(user_id)
    lang = user["language"] if user else "fa"

    # تغییر زبان
    if data.startswith("lang_"):
        new_lang = data.split("_")[1]
        set_language(user_id, new_lang)

        await query.answer("Language Updated")
        await query.edit_message_text(
            t({"language": new_lang}, "lang_changed")
        )
        return

    await query.answer("Unknown action")


# ---------------------------
# MAIN
# ---------------------------
async def main():
    init_db()

    app = Application.builder().token("YOUR_BOT_TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
