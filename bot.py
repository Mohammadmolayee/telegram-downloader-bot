# bot.py
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

import config
import database as db
import downloader
from messages import get_text

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN را در متغیرهای محیطی قرار بده.")

# Conversation states
(REG_NAME, REG_USERNAME, REG_PASSWORD) = range(3)

# ---- UI builders ----
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
        [InlineKeyboardButton(get_text("btn_profile", lang), callback_data="profile"),
         InlineKeyboardButton(get_text("btn_recent", lang), callback_data="recent")],
        [InlineKeyboardButton(get_text("btn_stats", lang), callback_data="stats")],
        [InlineKeyboardButton(get_text("btn_queue_status", lang), callback_data="queue_status"),
         InlineKeyboardButton(get_text("btn_cancel_download", lang), callback_data="cancel_current")],
        [InlineKeyboardButton(get_text("btn_back", lang), callback_data="back")],
    ]
    return InlineKeyboardMarkup(kb)

# ---- Handlers ----
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    # Auto-login: اگر کاربر در دیتابیس وجود دارد مستقیماً پنل را ارسال می‌کنیم
    if db.user_exists(user_id):
        await send_user_panel(user_id, context)
        return
    # در غیر این صورت خوش‌آمدگویی معمولی
    title = get_text("welcome_title", lang, bot_name=config.BOT_NAME)
    sub = get_text("welcome_sub", lang)
    await update.message.reply_text(f"{title}\n\n{sub}", reply_markup=welcome_keyboard(user_id))

# help
async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    lang = db.get_user_lang(uid)
    await q.edit_message_text(get_text("help_full", lang), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text("btn_back", lang), callback_data="back")]]))

# set language
async def set_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("🌐 زبان را انتخاب کنید:", reply_markup=lang_keyboard())

async def lang_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    try:
        _, code = q.data.split(":", 1)
    except:
        return
    db.set_user_lang(user_id, code)
    await q.edit_message_text(get_text("welcome_sub", code), reply_markup=welcome_keyboard(user_id))

# main menu
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    await q.edit_message_text(get_text("main_menu_text", db.get_user_lang(uid)), reply_markup=main_menu_keyboard(uid))

async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    await q.edit_message_text(get_text("welcome_sub", db.get_user_lang(uid)), reply_markup=welcome_keyboard(uid))

# ---- Registration Conversation ----
async def create_account_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if db.user_exists(uid):
        await q.edit_message_text(get_text("create_fail", db.get_user_lang(uid)), reply_markup=main_menu_keyboard(uid))
        return ConversationHandler.END
    await q.edit_message_text(get_text("create_prompt_name", db.get_user_lang(uid)))
    return REG_NAME

async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if not txt:
        await update.message.reply_text(get_text("create_prompt_name", db.get_user_lang(update.effective_user.id)))
        return REG_NAME
    context.user_data["reg_fullname"] = txt
    await update.message.reply_text(get_text("create_prompt_username", db.get_user_lang(update.effective_user.id)))
    return REG_USERNAME

async def reg_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if txt.startswith("@"):
        txt = txt[1:]
    if len(txt) < 3:
        await update.message.reply_text(get_text("create_prompt_username", db.get_user_lang(update.effective_user.id)))
        return REG_USERNAME
    if db.get_user_by_username(txt):
        await update.message.reply_text(get_text("create_fail", db.get_user_lang(update.effective_user.id)))
        return REG_USERNAME
    context.user_data["reg_username"] = txt
    await update.message.reply_text(get_text("create_prompt_password", db.get_user_lang(update.effective_user.id)))
    return REG_PASSWORD

async def reg_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if not (8 <= len(txt) <= 12 and txt.isalnum()):
        await update.message.reply_text(get_text("create_prompt_password", db.get_user_lang(update.effective_user.id)))
        return REG_PASSWORD
    uid = update.effective_user.id
    fullname = context.user_data.get("reg_fullname")
    username = context.user_data.get("reg_username")
    ok = db.create_user(uid, username, fullname, txt, db.get_user_lang(uid))
    context.user_data.clear()
    if ok:
        await update.message.reply_text(get_text("create_success", db.get_user_lang(uid)))
    else:
        await update.message.reply_text(get_text("create_fail", db.get_user_lang(uid)))
    return ConversationHandler.END

# ---- User panel ----
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
    uid = q.from_user.id
    lang = db.get_user_lang(uid)
    data = q.data

    if data == "profile":
        row = db.get_user_by_id(uid)
        if row:
            total_count, total_bytes = db.get_user_stats(uid)
            mb = total_bytes / (1024*1024) if total_bytes else 0
            await q.edit_message_text(f"👤 {row[2]}\n\n📥 دانلودها: {total_count}\n📦 حجم: {mb:.2f} MB", reply_markup=user_panel_keyboard(uid))
        else:
            await q.edit_message_text("اطلاعاتی یافت نشد.", reply_markup=user_panel_keyboard(uid))

    elif data == "recent":
        rows = db.get_user_downloads(uid, limit=7)
        if not rows:
            await q.edit_message_text(get_text("invalid_link", lang), reply_markup=user_panel_keyboard(uid))
            return
        lines = []
        for platform, title, size, at in rows:
            mb = size / (1024*1024) if size else 0
            lines.append(f"• {platform} — {title} — {mb:.2f} MB")
        await q.edit_message_text("\n".join(lines), reply_markup=user_panel_keyboard(uid))

    elif data == "stats":
        total_count, total_bytes = db.get_user_stats(uid)
        mb = total_bytes / (1024*1024) if total_bytes else 0
        await q.edit_message_text(f"📊 کل دانلودها: {total_count}\n📦 مجموع حجم: {mb:.2f} MB", reply_markup=user_panel_keyboard(uid))

    elif data == "queue_status":
        qsize = downloader.download_queue.qsize()
        await q.edit_message_text(f"🗂 تعداد در صف: {qsize}", reply_markup=user_panel_keyboard(uid))

    elif data == "cancel_current":
        await q.edit_message_text(get_text("cancel_info", lang), reply_markup=user_panel_keyboard(uid))

    elif data == "back":
        await q.edit_message_text(get_text("welcome_sub", lang), reply_markup=welcome_keyboard(uid))

    else:
        await q.answer("در حال توسعه...")

# ---- Text handler (auto-download) ----
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = db.get_user_lang(uid)
    text = (update.message.text or "").strip()

    if context.user_data:
        # اگر کاربر در وسط Conversation است، اجازه بده Conversation ادامه پیدا کند
        return

    if not (text.startswith("http://") or text.startswith("https://")):
        await update.message.reply_text(get_text("invalid_link", lang))
        return

    platform = None
    # detect platform quickly (lightweight)
    l = text.lower()
    if "youtube.com" in l or "youtu.be" in l:
        platform = "youtube"
    elif "tiktok.com" in l:
        platform = "tiktok"
    elif "instagram.com" in l or "instagram" in l:
        platform = "instagram"
    elif "soundcloud.com" in l:
        platform = "soundcloud"
    elif "spotify.com" in l:
        platform = "spotify"
    else:
        await update.message.reply_text(get_text("invalid_link", lang))
        return

    registered = db.user_exists(uid)
    daily = db.get_daily_download_count(uid)

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

    # enqueue job
    job_id = await downloader.enqueue_download(uid, update.effective_chat.id, text)
    context.chat_data["last_job"] = job_id

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚫 لغو دانلود", callback_data=f"cancel:{job_id}")]])
    await update.message.reply_text(get_text("added_queue", lang), reply_markup=kb)

# ---- Cancel callback ----
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
    except:
        pass

# ---- post_init: schedule background workers safely ----
async def post_init(app: Application):
    app.create_task(downloader.worker_loop(app))
    app.create_task(downloader.cleanup_loop())
    logger.info("Background workers scheduled.")

# ---- setup and run ----
def main():
    db.init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(set_lang_callback, pattern="^set_lang$"))
    app.add_handler(CallbackQueryHandler(lang_select_callback, pattern="^lang:"))
    app.add_handler(CallbackQueryHandler(back_callback, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(panel_callback, pattern="^(profile|recent|stats|queue_status|cancel_current|back)$"))
    app.add_handler(CallbackQueryHandler(cancel_download_callback, pattern="^cancel:"))

    # registration conv
    reg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_account_cb, pattern="^create_account$")],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_username)],
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_password)],
        },
        fallbacks=[]
    )
    app.add_handler(reg_conv)

    # main text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Bot starting (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()
