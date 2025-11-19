# bot.py — main entry
import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from db import (
    init_db, create_user, user_exists, get_user_by_username,
    get_user_lang, set_user_lang, get_user_downloads,
    get_user_stats, get_daily_download_count
)
from messages import TEXTS, LANG_OPTIONS
from downloader import enqueue_download, start_background_workers

# ---------------- settings ----------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("توکن ربات را در ENV با نام TOKEN قرار دهید.")

ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None

# logging
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
(REG_FIRSTNAME, REG_USERNAME, REG_PASSWORD, LOGIN_USERNAME, LOGIN_PASSWORD) = range(5)

def t(user_id: int, key: str, *a, **kw):
    lang = get_user_lang(user_id)
    return TEXTS.get(lang, TEXTS['en'])[key].format(*a, **kw)

# --- Handlers ---
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    kb = [
        [InlineKeyboardButton(TEXTS['fa']['btn_create'], callback_data='create_account')],
        [InlineKeyboardButton(TEXTS['fa']['btn_login'], callback_data='login')],
        [InlineKeyboardButton(TEXTS['fa']['btn_my_downloads'], callback_data='my_downloads')],
        [InlineKeyboardButton(TEXTS['fa']['btn_my_stats'], callback_data='my_stats')],
        [InlineKeyboardButton(TEXTS['fa']['btn_set_lang'], callback_data='set_lang')],
        [InlineKeyboardButton(TEXTS['fa']['btn_help'], callback_data='help')],
    ]
    # If user exists, show in their language
    lang = get_user_lang(user_id)
    kb = [
        [InlineKeyboardButton(TEXTS[lang]['btn_create'], callback_data='create_account')],
        [InlineKeyboardButton(TEXTS[lang]['btn_login'], callback_data='login')],
        [InlineKeyboardButton(TEXTS[lang]['btn_my_downloads'], callback_data='my_downloads')],
        [InlineKeyboardButton(TEXTS[lang]['btn_my_stats'], callback_data='my_stats')],
        [InlineKeyboardButton(TEXTS[lang]['btn_set_lang'], callback_data='set_lang')],
        [InlineKeyboardButton(TEXTS[lang]['btn_help'], callback_data='help')],
    ]
    await update.message.reply_text(TEXTS[lang]['welcome'], reply_markup=InlineKeyboardMarkup(kb))

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    kb = [
        [InlineKeyboardButton(TEXTS[lang]['btn_create'], callback_data='create_account')],
        [InlineKeyboardButton(TEXTS[lang]['btn_login'], callback_data='login')],
        [InlineKeyboardButton(TEXTS[lang]['btn_my_downloads'], callback_data='my_downloads')],
        [InlineKeyboardButton(TEXTS[lang]['btn_my_stats'], callback_data='my_stats')],
        [InlineKeyboardButton(TEXTS[lang]['btn_set_lang'], callback_data='set_lang')],
        [InlineKeyboardButton(TEXTS[lang]['btn_help'], callback_data='help')],
    ]
    await q.answer()
    await q.edit_message_text(TEXTS[lang]['menu_title'], reply_markup=InlineKeyboardMarkup(kb))

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    await q.edit_message_text(TEXTS[lang]['help_text'])

# create account flow
async def create_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    if user_exists(user_id):
        await q.edit_message_text(TEXTS[lang]['create_already'])
        return
    context.user_data.clear()
    await q.edit_message_text(TEXTS[lang]['create_prompt_name'])
    return

async def reg_firstname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text(TEXTS[lang]['create_prompt_name'])
        return REG_FIRSTNAME
    context.user_data['first_name'] = text
    await update.message.reply_text(TEXTS[lang]['create_prompt_username'])
    return REG_USERNAME

async def reg_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = (update.message.text or "").strip()
    if text.startswith('@'):
        text = text[1:]
    if len(text) < 3:
        await update.message.reply_text(TEXTS[lang]['create_prompt_username'])
        return REG_USERNAME
    if get_user_by_username(text):
        await update.message.reply_text(TEXTS[lang]['create_fail'])
        return REG_USERNAME
    context.user_data['username'] = text
    await update.message.reply_text(TEXTS[lang]['create_prompt_password'])
    return REG_PASSWORD

async def reg_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = (update.message.text or "").strip()
    if not (8 <= len(text) <= 12 and text.isalnum()):
        await update.message.reply_text(TEXTS[lang]['create_prompt_password'])
        return REG_PASSWORD
    username = context.user_data.get('username')
    first_name = context.user_data.get('first_name')
    ok = create_user(user_id, username, first_name, text, lang)
    context.user_data.clear()
    if ok:
        await update.message.reply_text(TEXTS[lang]['create_success'])
    else:
        await update.message.reply_text(TEXTS[lang]['create_fail'])
    return ConversationHandler.END

# login flow
async def login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    context.user_data.clear()
    await q.edit_message_text(TEXTS[lang]['login_prompt_username'])
    return

async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text.startswith('@'):
        text = text[1:]
    context.user_data['login_username'] = text
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    await update.message.reply_text(TEXTS[lang]['login_prompt_password'])
    return LOGIN_PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    text = (update.message.text or "").strip()
    username = context.user_data.get('login_username')
    row = get_user_by_username(username)
    context.user_data.clear()
    if not row:
        await update.message.reply_text(TEXTS[lang]['login_fail'])
        return ConversationHandler.END
    stored_hash = row[3]
    if stored_hash and (isinstance(stored_hash, (bytes, bytearray)) and __import__('bcrypt').checkpw(text.encode(), stored_hash)):
        await update.message.reply_text(TEXTS[lang]['login_success'])
    else:
        await update.message.reply_text(TEXTS[lang]['login_fail'])
    return ConversationHandler.END

# my downloads & stats
async def my_downloads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    rows = get_user_downloads(user_id, limit=10)
    if not rows:
        await q.edit_message_text(TEXTS[lang]['no_downloads'])
        return
    lines = [TEXTS[lang]['my_downloads_header']]
    for platform, title, file_type, file_size, downloaded_at in rows:
        mb = file_size / (1024*1024) if file_size else 0
        lines.append(f"• {platform} — {title}\n  {TEXTS[lang]['label_type']}: {file_type} — {mb:.2f} MB — {downloaded_at}")
    await q.edit_message_text("\n\n".join(lines))

async def my_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    total_count, total_bytes = get_user_stats(user_id)
    daily = get_daily_download_count(user_id)
    mb = total_bytes / (1024*1024)
    await q.edit_message_text(TEXTS[lang]['my_stats'].format(total_count, mb, daily))

# language
async def set_lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    lang = get_user_lang(user_id)
    await q.answer()
    kb = [[InlineKeyboardButton(label, callback_data=f"lang:{code}")] for code, label in LANG_OPTIONS]
    await q.edit_message_text(TEXTS[lang]['set_lang_prompt'], reply_markup=InlineKeyboardMarkup(kb))

async def lang_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    data = q.data
    try:
        _, code = data.split(':', 1)
    except Exception:
        await q.answer()
        return
    set_user_lang(user_id, code)
    await q.answer()
    await q.edit_message_text(TEXTS[code]['lang_changed'])

# enqueue download (text messages) — uses downloader.enqueue_download
# enqueue_download returns immediate confirmation to user
# already implemented in downloader.py
# admin stats command
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ فقط ادمین می‌تواند این دستور را اجرا کند.")
        return
    import sqlite3
    conn = sqlite3.connect('downloads.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    users_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM downloads')
    downloads_count = c.fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 کاربران ثبت‌شده: {users_count}\n📥 تعداد دانلودها: {downloads_count}")

# ----------------- main -----------------
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # basic handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern='^menu$'))
    app.add_handler(CallbackQueryHandler(create_account_callback, pattern='^create_account$'))
    app.add_handler(CallbackQueryHandler(login_callback, pattern='^login$'))
    app.add_handler(CallbackQueryHandler(my_downloads_callback, pattern='^my_downloads$'))
    app.add_handler(CallbackQueryHandler(my_stats_callback, pattern='^my_stats$'))
    app.add_handler(CallbackQueryHandler(help_callback, pattern='^help$'))
    app.add_handler(CallbackQueryHandler(set_lang_callback, pattern='^set_lang$'))
    app.add_handler(CallbackQueryHandler(lang_selected_callback, pattern='^lang:'))

    # conversation for signup/login
    reg_conv = ConversationHandler(
        entry_points=[],
        states={
            REG_FIRSTNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_firstname)],
            REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_username)],
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_password)],
            LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[]
    )
    app.add_handler(reg_conv)

    # enqueue download (text messages)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, enqueue_download))

    # admin
    app.add_handler(CommandHandler("stats", stats_command))

    # background workers (queue worker + cleanup)
    start_background_workers(app)

    logger.info("Bot starting (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()
