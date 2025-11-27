# bot.py (fixed - event loop / run_polling issues resolved)
import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# imports from your modules (assumed present)
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        lang = user.get("language", "fa")
        await update.message.reply_text(
            t(user, "start_member") if hasattr(t, "__call__") else t({"language": lang}, "start"),
            reply_markup=panel_keyboard(lang)
        )
    else:
        # guest: use fa default or context lang if set
        lang = context.user_data.get("language", "fa")
        await update.message.reply_text(
            t({"language": lang}, "start_guest") if hasattr(t, "__call__") else t({"language": "fa"}, "start"),
            reply_markup=start_keyboard(lang)
        )


# ---------------------------
# پیام‌ها
# ---------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    msg = update.message.text.strip()
    user_id = update.effective_user.id

    user = get_user(user_id)
    lang = user.get("language", "fa") if user else context.user_data.get("language", "fa")

    # بک ریپلی
    if msg in ["🔙 بازگشت", "🔙 Back"]:
        if user:
            await update.message.reply_text(
                t({"language": lang}, "start_member"),
                reply_markup=panel_keyboard(lang)
            )
        else:
            await update.message.reply_text(
                t({"language": lang}, "start_guest"),
                reply_markup=start_keyboard(lang)
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
    # ساخت حساب (3-step: name, username, password)
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
        pending_data[user_id]["username"] = msg.strip().lstrip("@")
        user_state[user_id] = "register_password"
        await update.message.reply_text(t({"language": lang}, "reg_password"))
        return

    if user_state.get(user_id) == "register_password":
        info = pending_data.get(user_id, {})
        name = info.get("name", update.effective_user.first_name)
        username = info.get("username", f"user{user_id}")
        password = msg
        ok = create_user(user_id, name, username, password)
        if ok:
            user_state.pop(user_id, None)
            pending_data.pop(user_id, None)
            await update.message.reply_text(
                t({"language": lang}, "reg_done"),
                reply_markup=panel_keyboard(lang)
            )
        else:
            await update.message.reply_text(t({"language": lang}, "reg_fail"))
        return

    # --------------------
    # ورود (login)
    # --------------------
    if msg in ["🔐 ورود", "🔐 Login"]:
        user_state[user_id] = "login_username"
        await update.message.reply_text(t({"language": lang}, "login_username"))
        return

    if user_state.get(user_id) == "login_username":
        pending_data[user_id] = {"username": msg.strip().lstrip("@")}
        user_state[user_id] = "login_password"
        await update.message.reply_text(t({"language": lang}, "login_password"))
        return

    if user_state.get(user_id) == "login_password":
        username = pending_data.get(user_id, {}).get("username")
        uid = login(username, msg)
        if uid:
            user_state.pop(user_id, None)
            pending_data.pop(user_id, None)
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
    # دانلود (فقط لینک‌ها)
    # --------------------
    if msg.startswith("http"):
        # schedule download as application task (safe)
        # check permission: if in main menu, disallow (your requirement)
        current_menu = context.user_data.get("menu")
        if current_menu == "main_menu":
            await update.message.reply_text(t({"language": lang}, "guest_download_block"))
            return

        # if guest and platform restriction etc. (you can add checks here)
        # schedule task via context.application.create_task
        try:
            context.application.create_task(download_media(user_id, msg, context.bot, lang))
        except Exception as e:
            logger.exception("Failed to create download task")
            await update.message.reply_text(t({"language": lang}, "download_error"))
        return

    # unknown text
    await update.message.reply_text(t({"language": lang}, "unknown"))


# ---------------------------
# کال‌بک‌ها (inline)
# ---------------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    data = q.data
    user_id = q.from_user.id
    user = get_user(user_id)
    lang = user.get("language", "fa") if user else context.user_data.get("language", "fa")

    # انتخاب زبان
    if data.startswith("lang_"):
        new_lang = data.split("_", 1)[1]
        # for model B store in context for guest, DB for members
        if user:
            set_language(user_id, new_lang)
        else:
            context.user_data["language"] = new_lang
        await q.edit_message_text(t({"language": new_lang}, "language_changed"))
        return

    # تم
    if data.startswith("theme_"):
        theme = data.split("_", 1)[1]
        if user:
            set_theme(user_id, theme)
        else:
            context.user_data["theme"] = theme
        await q.edit_message_text(t({"language": lang}, "theme_changed"))
        return

    # cancel download (if you send such callback)
    if data == "cancel_download":
        cancel_download(user_id)
        await q.edit_message_text(t({"language": lang}, "cancel_download"))
        return


# ---------------------------
# MAIN - run safely (no asyncio.run around app.run_polling)
# ---------------------------
def main():
    init_db()
    token = os.getenv("TOKEN") or os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot starting with Application.run_polling() (safe mode)...")
    app.run_polling()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    main()
