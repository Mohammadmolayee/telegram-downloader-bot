# bot.py
# فایل اصلی: بارگذاری تنظیمات، راه‌اندازی Application، handlers، منطق دانلود.
import logging
import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from settings import TOKEN, DOWNLOAD_DIR, LOGGING_LEVEL
import messages as MSG
import keyboards as KB
import downloader
import database as DB
from pathlib import Path

# Logging
logging.basicConfig(level=LOGGING_LEVEL)
logger = logging.getLogger(__name__)

# Helpers
def detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "youtube" in url_lower or "youtu.be" in url_lower:
        return "YouTube"
    if "tiktok" in url_lower:
        return "TikTok"
    if "instagram" in url_lower:
        return "Instagram"
    if "soundcloud" in url_lower:
        return "SoundCloud"
    if "spotify" in url_lower:
        return "Spotify"
    return "Unknown"

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = MSG.MESS['start']
    # if user has account -> show panel (auto-login)
    if DB.user_exists(user.id):
        await send_panel(update, context)
        return
    await update.message.reply_text(text, reply_markup=KB.start_reply_keyboard())

async def send_panel(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    # helper to send member panel; handles both Message and CallbackQuery contexts
    if isinstance(update_or_query, Update) and update_or_query.message:
        user = update_or_query.effective_user
        chat = update_or_query.message
        send_fn = chat.reply_text
    else:
        # from callback query
        cq = update_or_query.callback_query
        user = cq.from_user
        send_fn = cq.message.reply_text

    name = user.first_name or user.username or str(user.id)
    text = MSG.MESS['panel_welcome'].format(name=name, limit=DB.USER_DAILY_LIMIT)
    await send_fn(text, reply_markup=KB.user_panel_reply())

async def help_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # help in start
    await update.message.reply_text(MSG.MESS['help_start'], reply_markup=KB.inline_back())

async def main_menu_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG.MESS['main_menu'], reply_markup=KB.inline_back())

async def panel_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG.MESS['help_panel'], reply_markup=KB.inline_back())

async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # about from either message or callback
    if update.message:
        await update.message.reply_text(MSG.MESS['about'], reply_markup=KB.inline_back())
    else:
        await update.callback_query.message.reply_text(MSG.MESS['about'], reply_markup=KB.inline_back())

async def rules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(MSG.MESS['rules'], reply_markup=KB.inline_back())
    else:
        await update.callback_query.message.reply_text(MSG.MESS['rules'], reply_markup=KB.inline_back())

# Account creation simple (no password, just minimal)
async def create_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Step 1: ask for name
    context.user_data['create_step'] = 'name'
    await update.message.reply_text("لطفا نام کامل خود را ارسال کنید:", reply_markup=KB.cancel_inline())

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main router for text messages.
    If the user is in account creation steps, handle that.
    Otherwise, treat the message as a potential URL to download.
    """
    user = update.effective_user
    text = update.message.text.strip()

    # Cancel handling
    if context.user_data.get('create_step') == 'name' and text == '⛔️ لغو':
        context.user_data.clear()
        await update.message.reply_text("ساخت حساب لغو شد.", reply_markup=KB.start_reply_keyboard())
        return

    # Account creation flow
    step = context.user_data.get('create_step')
    if step == 'name':
        context.user_data['name'] = text
        context.user_data['create_step'] = 'username'
        await update.message.reply_text("لطفا یوزرنیم (بدون @) وارد کنید:", reply_markup=KB.cancel_inline())
        return
    elif step == 'username':
        username = text.lstrip('@')
        context.user_data['username'] = username
        # create user in DB
        created = DB.create_user(user.id, username, context.user_data.get('name'))
        context.user_data.clear()
        if created:
            await update.message.reply_text("حساب با موفقیت ساخته شد! برای ورود خودکار /start یا دکمه ورود خودکار را بزنید.", reply_markup=KB.start_reply_keyboard())
        else:
            await update.message.reply_text("خطا: ممکن است قبلاً حساب ساخته شده باشد.", reply_markup=KB.start_reply_keyboard())
        return

    # Otherwise treat as link to download
    # If text doesn't look like URL, ignore
    if not (text.startswith("http://") or text.startswith("https://")):
        await update.message.reply_text("برای دانلود، یک لینک معتبر ارسال کنید.", reply_markup=KB.start_reply_keyboard())
        return

    # Platform check & permission
    platform = detect_platform(text)

    # Guests restrictions
    if not DB.user_exists(user.id):
        # guest
        if platform not in ("Instagram", "Spotify"):
            await update.message.reply_text("❗ این پلتفرم برای مهمان غیرفعال است. برای دسترسی به YouTube/TikTok/SoundCloud لطفاً حساب بسازید.", reply_markup=KB.start_reply_keyboard())
            return
        # check limit
        if DB.downloads_count_today(user.id) >= DB.GUEST_DAILY_LIMIT:
            await update.message.reply_text(MSG.MESS['limit_exceeded'])
            return
    else:
        # member limit
        if DB.downloads_count_today(user.id) >= DB.USER_DAILY_LIMIT:
            await update.message.reply_text(MSG.MESS['limit_exceeded'])
            return

    # Start processing
    status_msg = await update.message.reply_text(MSG.MESS['processing'])
    try:
        # decide audio or video automatically (for simplicity: if spotify or soundcloud -> audio)
        audio_only = platform in ("Spotify", "SoundCloud")
        # call async downloader
        filepath, title, file_type = await downloader.download_url(text, audio_only=audio_only)
        # send file
        path_obj = Path(filepath)
        size = path_obj.stat().st_size
        # Use appropriate send method
        with open(filepath, 'rb') as f:
            if file_type == 'audio':
                # try to send as audio (telegram will detect mime)
                await update.message.reply_audio(f, caption=f"{platform}: {title}")
            else:
                # send as document to avoid automatic compression if large
                await update.message.reply_document(f, caption=f"{platform}: {title}")
        # Save to DB
        DB.save_download(user.id, platform, text, title, file_type)
        await status_msg.delete()
    except Exception as e:
        logger.exception("download error")
        try:
            await status_msg.edit_text(MSG.MESS['download_error'].format(err=str(e)))
        except Exception:
            pass
    finally:
        # cleanup file if exists
        try:
            if 'filepath' in locals() and Path(filepath).exists():
                downloader.safe_remove(filepath)
        except Exception:
            pass

# CallbackQuery handler for inline buttons
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "back":
        # send start or panel based on user
        if DB.user_exists(q.from_user.id):
            await send_panel(update, context)
        else:
            await q.message.reply_text(MSG.MESS['start'], reply_markup=KB.start_reply_keyboard())
    elif data.startswith("lang_"):
        # we will not implement full i18n here — placeholder
        await q.message.reply_text("زبان تغییر کرد.", reply_markup=KB.inline_back())
    elif data == "cancel":
        await q.message.reply_text("عملیات لغو شد.", reply_markup=KB.start_reply_keyboard())
    else:
        await q.message.reply_text("عملیات نامشخص.", reply_markup=KB.inline_back())

# Basic commands
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await help_start(update, context)

# Main runner
def main():
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))

    # Callback queries (inline)
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    # Other handlers (account creation)
    app.add_handler(CommandHandler("create_account", create_account_start))

    # Start polling (this manages the event loop internally)
    logger.info("Starting bot...")
    app.run_polling()

if __name__ == "__main__":
    main()
