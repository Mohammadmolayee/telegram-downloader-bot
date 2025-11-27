# bot.py
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from database import (
    init_db, user_exists, create_user, login,
    get_user, set_language, set_theme
)
from keyboards import (
    start_keyboard, main_menu_keyboard, panel_keyboard,
    settings_keyboard, language_inline, theme_inline
)
from downloader import download_media, cancel_download
from messages import t


# حافظه وضعیت
user_state = {}      # مرحله ساخت حساب / ورود
pending_data = {}    # اطلاعات موقت کاربر


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
# پیام‌ها
# ---------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = update.effective_user.id

    user = get_user(user_id)
    lang = user["language"] if user else "fa"

    # بک ریپلی
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

    # دکمه‌های منوی استارت
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
        await update.message.reply_text(t({"language": lang}, "choose_language"),
                                       reply_markup=language_inline())
        return

    if msg in ["🧰 منوی اصلی", "🧰 Main Menu"]:
        await update.message.reply_text(
            t({"language": lang}, "menu_main"),
            reply_markup=main_menu_keyboard(lang)
        )
        return

    # --------------------
    # ساخت حساب
    # --------------------
    if msg in ["👤 ساخت حساب", "👤 Create Account"]:
        user_state[user_id] = "register_name"
        await update.message.reply_text(t({"language": lang}, "reg_name"))
        return

    if user_state.get(user_id) == "register_name":
        pending_data[user_id] = {"name": msg}
        user_state[user_id] = "register_username"
        await update.message.reply_text(t({"language": lang}, "reg_username"))
        return

    if user_state.get(user_id) == "register_username":
        pending_data[user_id]["username"] = msg
        user_state[user_id] = "register_password"
        await update.message.reply_text(t({"language": lang}, "reg_password"))
        return

    if user_state.get(user_id) == "register_password":
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
            await update.message.reply_text(t({"language": lang}, "reg_fail"))
        return

    # --------------------
    # ورود
    # --------------------
    if msg in ["🔐 ورود", "🔐 Login"]:
        user_state[user_id] = "login_username"
        await update.message.reply_text(t({"language": lang}, "login_username"))
        return

    if user_state.get(user_id) == "login_username":
        pending_data[user_id] = {"username": msg}
        user_state[user_id] = "login_password"
        await update.message.reply_text(t({"language": lang}, "login_password"))
        return

    if user_state.get(user_id) == "login_password":
        username = pending_data[user_id]["username"]
        uid = login(username, msg)
        if uid:
            user_state.pop(user_id)
            pending_data.pop(user_id)
            await update.message.reply_text(
                t({"language": lang}, "login_success"),
                reply_markup=panel_keyboard(lang)
            )
        else:
            await update.message.reply_text(t({"language": lang}, "login_fail"))
        return

    # --------------------
    # تنظیمات
    # --------------------
    if msg in ["🎨 تنظیمات", "🎨 Settings"]:
        await update.message.reply_text(
            t({"language": lang}, "settings"),
            reply_markup=settings_keyboard(lang)
        )
        return

    if msg in ["🌐 تغییر زبان", "🌐 Change Language"]:
        await update.message.reply_text(
            t({"language": lang}, "choose_language"),
            reply_markup=language_inline()
        )
        return

    if msg in ["🎨 تغییر تم", "🎨 Theme"]:
        await update.message.reply_text(
            t({"language": lang}, "choose_theme"),
            reply_markup=theme_inline()
        )
        return

    # --------------------
    # دانلود
    # --------------------
    if msg.startswith("http"):
        if not user:
            await update.message.reply_text(
                t({"language": "fa"}, "guest_download")
            )
        await do_download(update, context)
        return

    await update.message.reply_text(t({"language": lang}, "unknown"))
    

# ---------------------------
# دانلود
# ---------------------------
async def do_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.effective_user.id
    user = get_user(user_id)
    lang = user["language"] if user else "fa"

    task = asyncio.create_task(
        download_media(user_id, url, context.bot, lang)
    )


# ---------------------------
# کال‌بک‌ها
# ---------------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    user_id = update.effective_user.id
    user = get_user(user_id)
    lang = user["language"] if user else "fa"

    # انتخاب زبان
    if data.startswith("lang_"):
        new_lang = data.split("_")[1]
        set_language(user_id, new_lang)
        await update.callback_query.answer("Language changed.")
        await update.callback_query.edit_message_text(
            t({"language": new_lang}, "lang_changed")
        )

    # تم
    elif data.startswith("theme_"):
        theme = data.split("_")[1]
        set_theme(user_id, theme)
        await update.callback_query.answer("Theme changed.")
        await update.callback_query.edit_message_text(
            t({"language": lang}, "theme_changed")
        )


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
