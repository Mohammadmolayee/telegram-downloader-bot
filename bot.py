# bot.py
"""
فایل اصلی ربات — بوت کامل، با توضیحات فارسی
نکته مهم: قبل از اجرای ربات، متغیر محیطی TOKEN را در Railway یا local تنظیم کن.
"""

import os
import asyncio
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

import config
import database as db
import downloader
from messages import get_text
from utils import detect_platform, is_audio_platform, is_video_platform

# logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN را در متغیرهای محیطی قرار بده (Railway -> Variables).")

# Conversation states
(REG_NAME, REG_USERNAME, REG_PASSWORD, LOGIN_USER, LOGIN_PASS) = range(5)

# ------------- UI builders -------------
def welcome_keyboard(user_id: int):
    lang = db.get_user_lang(user_id)
    kb = [
        [InlineKeyboardButton(get_text("btn_help", lang), callback_data="help")],
        [InlineKeyboardButton(get_text("btn_main_menu", lang), callback_data="main_menu")],
        [InlineKeyboardButton(get_text("btn_set_lang", lang), callback_data="set_lang")],
    ]
    return InlineKeyboardMarkup(kb)

def main_menu_keyboard(user_id: int):
    lang = db.get_user_lang(user_id)
    kb = [
        [InlineKeyboardButton(get_text("btn_create_account", lang), callback_data="create_account")],
        [InlineKeyboardButton(get_text("btn_login", lang), callback_data="login")],
        [InlineKeyboardButton(get_text("btn_back", lang), callback_data="back")],
    ]
    return InlineKeyboardMarkup(kb)

def lang_keyboard():
    kb = [
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang:fa")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang:en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang:ar")],
    ]
    return InlineKeyboardMarkup(kb)

def user_panel_keyboard(user_id: int):
    lang = db.get_user_lang(user_id)
    kb = [
        [InlineKeyboardButton(get_text("btn_profile", lang), callback_data="profile")],
        [InlineKeyboardButton(get_text("btn_recent", lang), callback_data="recent")],
        [InlineKeyboardButton(get_text("btn_stats", lang), callback_data="stats")],
        [InlineKeyboardButton(get_text("btn_audio", lang), callback_data="download_audio"),
         InlineKeyboardButton(get_text("btn_video", lang), callback_data="download_video")],
        [InlineKeyboardButton(get_text("btn_queue_status", lang), callback_data="queue_status"),
         InlineKeyboardButton(get_text("btn_cancel_download", lang), callback_data="cancel_current")],
        [InlineKeyboardButton(get_text("btn_back", lang), callback_data="back")],
    ]
    return InlineKeyboardMarkup(kb)

# ------------- Handlers -------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # ensure user row exists? we allow guest so not necessary
    lang = db.get_user_lang(user_id)
    title = get_text("welcome_title", lang, bot_name=config.BOT_NAME)
    sub = get_text("welcome_sub", lang)
    await update.message.reply_text(f"{title}\n\n{sub}", reply_markup=welcome_keyboard(user_id))

# help
async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    lang = db.get_user_lang(user_id)
    await q.edit_message_text(get_text("help_full", lang), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text("btn_back", lang), callback_data="back")]]))

# set language
async def set_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("🌐 زبان را انتخاب کنید:", reply_markup=lang_keyboard())

async def lang_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    user_id = q.from_user.id
    try:
        _, code = data.split(":", 1)
    except Exception:
        return
    db.set_user_lang(user_id, code)
    await q.edit_message_text(get_text("welcome_sub", code), reply_markup=welcome_keyboard(user_id))

# main menu
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    await q.edit_message_text(get_text("main_menu_text", db.get_user_lang(user_id)), reply_markup=main_menu_keyboard(user_id))

async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    await q.edit_message_text(get_text("welcome_sub", db.get_user_lang(user_id)), reply_markup=welcome_keyboard(user_id))

# ---------------- Registration Conversation ----------------
async def create_account_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    if db.user_exists(user_id):
        await q.edit_message_text(get_text("create_fail", db.get_user_lang(user_id)), reply_markup=main_menu_keyboard(user_id))
        return ConversationHandler.END
    await q.edit_message_text(get_text("create_prompt_name", db.get_user_lang(user_id)))
    return REG_NAME

async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text(get_text("create_prompt_name", db.get_user_lang(update.effective_user.id)))
        return REG_NAME
    context.user_data["reg_fullname"] = text
    await update.message.reply_text(get_text("create_prompt_username", db.get_user_lang(update.effective_user.id)))
    return REG_USERNAME

async def reg_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text.startswith("@"):
        text = text[1:]
    if len(text) < 3:
        await update.message.reply_text(get_text("create_prompt_username", db.get_user_lang(update.effective_user.id)))
        return REG_USERNAME
    if db.get_user_by_username(text):
        await update.message.reply_text(get_text("create_fail", db.get_user_lang(update.effective_user.id)))
        return REG_USERNAME
    context.user_data["reg_username"] = text
    await update.message.reply_text(get_text("create_prompt_password", db.get_user_lang(update.effective_user.id)))
    return REG_PASSWORD

async def reg_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not (8 <= len(text) <= 12 and text.isalnum()):
        await update.message.reply_text(get_text("create_prompt_password", db.get_user_lang(update.effective_user.id)))
        return REG_PASSWORD
    user_id = update.effective_user.id
    fullname = context.user_data.get("reg_fullname")
    username = context.user_data.get("reg_username")
    ok = db.create_user(user_id, username, fullname, text, db.get_user_lang(user_id))
    context.user_data.clear()
    if ok:
        await update.message.reply_text(get_text("create_success", db.get_user_lang(user_id)), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text("btn_login", db.get_user_lang(user_id)), callback_data="login")]]))
    else:
        await update.message.reply_text(get_text("create_fail", db.get_user_lang(user_id)))
    return ConversationHandler.END

# ---------------- Login Conversation ----------------
async def login_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(get_text("login_prompt_username", db.get_user_lang(q.from_user.id)))
    return LOGIN_USER

async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text.startswith("@"):
        text = text[1:]
    context.user_data["login_username"] = text
    await update.message.reply_text(get_text("login_prompt_password", db.get_user_lang(update.effective_user.id)))
    return LOGIN_PASS

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pwd = (update.message.text or "").strip()
    username = context.user_data.get("login_username")
    context.user_data.clear()
    row = db.check_login(username, pwd)
    if row:
        # login success
        await update.message.reply_text(get_text("login_success", db.get_user_lang(update.effective_user.id)))
        # show user panel
        await send_user_panel(update.effective_user.id, context)
    else:
        await update.message.reply_text(get_text("login_fail", db.get_user_lang(update.effective_user.id)))
    return ConversationHandler.END

# ---------------- User Panel ----------------
async def send_user_panel(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    lang = db.get_user_lang(user_id)
    row = db.get_user_by_id(user_id)
    display = row[2] if row else str(user_id)
    count = db.get_daily_download_count(user_id)
    limit = config.REGISTERED_DAILY_LIMIT
    text = get_text("panel_welcome", lang, display_name=display, count=count, limit=limit)
    try:
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=user_panel_keyboard(user_id))
    except Exception:
        pass

async def panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    lang = db.get_user_lang(user_id)
    data = q.data

    if data == "profile":
        row = db.get_user_by_id(user_id)
        if row:
            total_count, total_bytes = db.get_user_stats(user_id)
            mb = total_bytes / (1024*1024) if total_bytes else 0
            await q.edit_message_text(f"👤 {row[2]}\n\n📥 دانلودها: {total_count}\n📦 حجم: {mb:.2f} MB", reply_markup=user_panel_keyboard(user_id))
        else:
            await q.edit_message_text("اطلاعاتی یافت نشد.", reply_markup=user_panel_keyboard(user_id))

    elif data == "recent":
        rows = db.get_user_downloads(user_id, limit=7)
        if not rows:
            await q.edit_message_text(get_text("invalid_link", lang), reply_markup=user_panel_keyboard(user_id))
            return
        lines = []
        for platform, title, size, at in rows:
            mb = size / (1024*1024) if size else 0
            lines.append(f"• {platform} — {title} — {mb:.2f} MB")
        await q.edit_message_text("\n".join(lines), reply_markup=user_panel_keyboard(user_id))

    elif data == "stats":
        total_count, total_bytes = db.get_user_stats(user_id)
        mb = total_bytes / (1024*1024) if total_bytes else 0
        await q.edit_message_text(f"📊 کل دانلودها: {total_count}\n📦 مجموع حجم: {mb:.2f} MB", reply_markup=user_panel_keyboard(user_id))

    elif data == "download_audio":
        await q.edit_message_text("🔊 برای دانلود صدا، لینک Spotify یا SoundCloud بفرستید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text("btn_back", lang), callback_data="back")]]))

    elif data == "download_video":
        await q.edit_message_text("🎬 برای دانلود ویدیو، لینک YouTube/Instagram/TikTok بفرستید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text("btn_back", lang), callback_data="back")]]))

    elif data == "queue_status":
        qsize = downloader.download_queue.qsize()
        await q.edit_message_text(f"🗂 تعداد در صف: {qsize}", reply_markup=user_panel_keyboard(user_id))

    elif data == "cancel_current":
        await q.edit_message_text(get_text("cancel_info", lang), reply_markup=user_panel_keyboard(user_id))

    elif data == "back":
        await q.edit_message_text(get_text("welcome_sub", lang), reply_markup=welcome_keyboard(user_id))

    else:
        await q.answer("در حال توسعه...")

# ---------------- Text message handler (enqueue) ----------------
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    این هندلر فقط وقتی اجرا می‌شود که ConversationHandlerها کاری نکنند.
    اگر user در وسط ثبت‌نام/ورود باشد، پیام‌ها توسط ConversationHandler مدیریت می‌شوند.
    """
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    text = (update.message.text or "").strip()

    # basic url check
    if not (text.startswith("http://") or text.startswith("https://")):
        await update.message.reply_text(get_text("invalid_link", lang))
        return

    platform = detect_platform(text)
    if not platform:
        await update.message.reply_text(get_text("invalid_link", lang))
        return

    # check permissions and limits
    registered = db.user_exists(user_id)
    daily = db.get_daily_download_count(user_id)

    if not registered:
        # guest rules: only instagram videos and spotify audio allowed
        if platform not in ("instagram", "spotify"):
            await update.message.reply_text(get_text("guest_must_register", lang))
            return
        if daily >= config.GUEST_DAILY_LIMIT:
            await update.message.reply_text(get_text("guest_limit", lang, config.GUEST_DAILY_LIMIT))
            return
    else:
        if daily >= config.REGISTERED_DAILY_LIMIT:
            await update.message.reply_text(get_text("registered_limit", lang, config.REGISTERED_DAILY_LIMIT))
            return

    # enqueue
    job_id = await downloader.enqueue_download(user_id, update.effective_chat.id, text)
    # store last job in chat_data to allow cancel
    context.chat_data["last_job"] = job_id

    # send confirmation with cancel button
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚫 لغو دانلود", callback_data=f"cancel:{job_id}")]])
    await update.message.reply_text(get_text("added_queue", lang), reply_markup=kb)

# ---------------- Cancel callback ----------------
async def cancel_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if not data.startswith("cancel:"):
        await q.answer()
        return
    job_id = data.split(":", 1)[1]
    downloader.canceled_jobs.add(job_id)
    lang = db.get_user_lang(q.from_user.id)
    try:
        await q.edit_message_text(get_text("cancelled", lang))
    except Exception:
        pass

# ---------------- Background tasks (post_init) ----------------
async def post_init(app: Application):
    # schedule worker and cleanup inside running loop (safe)
    app.create_task(downloader.worker_loop(app))
    app.create_task(downloader.cleanup_loop())
    logger.info("Background workers scheduled.")

# ---------------- Setup and run ----------------
def main():
    # init db
    db.init_db()

    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # basic handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(set_lang_callback, pattern="^set_lang$"))
    app.add_handler(CallbackQueryHandler(lang_select_callback, pattern="^lang:"))
    app.add_handler(CallbackQueryHandler(back_callback, pattern="^back$"))

    # conversations
    reg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_account_cb, pattern="^create_account$")],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_username)],
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_password)],
        },
        fallbacks=[]
    )
    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(login_cb, pattern="^login$")],
        states={
            LOGIN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            LOGIN_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[]
    )
    app.add_handler(reg_conv)
    app.add_handler(login_conv)

    # user panel callbacks
    app.add_handler(CallbackQueryHandler(panel_callback, pattern="^(profile|recent|stats|download_audio|download_video|queue_status|cancel_current|back)$"))

    # cancel job callback
    app.add_handler(CallbackQueryHandler(cancel_download_callback, pattern="^cancel:"))

    # admin stats (optional)
    # app.add_handler(CommandHandler("stats", stats_command))

    # main text handler (enqueue)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Bot starting (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()
