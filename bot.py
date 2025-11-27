# bot.py
import logging
from pathlib import Path
import asyncio

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

import settings
import database as DB
import downloader
import messages as MSG
import keyboards as KB
import utils

logging.basicConfig(level=getattr(logging, settings.LOGGING_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

# ---------- helpers ----------
def t(user_id: int, key: str) -> str:
    # get user lang (fallback fa)
    lang = DB.get_user_lang(user_id)
    return MSG.get(lang, key)

# send panel for member
async def send_panel_by_user(update_obj, context: ContextTypes.DEFAULT_TYPE):
    # called from message or callback
    if hasattr(update_obj, "message") and update_obj.message:
        user = update_obj.effective_user
        chat = update_obj.message
        send = chat.reply_text
    else:
        cq = update_obj.callback_query
        user = cq.from_user
        send = cq.message.reply_text

    name = user.first_name or user.username or str(user.id)
    limit = DB.get_limits(user.id)
    text = MSG.get(DB.get_user_lang(user.id), 'panel_welcome').format(name=name, limit=limit)
    # mark menu
    context.user_data['menu'] = 'user_panel'
    await send(text, reply_markup=KB.user_panel_reply())

async def send_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = DB.get_user_lang(user.id)
    text = MSG.get(lang, 'start')
    context.user_data['menu'] = 'start'
    await update.message.reply_text(text, reply_markup=KB.start_reply_keyboard())

async def send_guest_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['menu'] = 'main_menu'
    await update.message.reply_text(MSG.get(DB.get_user_lang(update.effective_user.id), 'main_menu'),
                                    reply_markup=KB.guest_main_reply())

# ---------- handlers ----------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Auto-login: if user exists -> panel, else start
    user = update.effective_user
    if DB.user_exists(user.id):
        await send_panel_by_user(update, context)
    else:
        await send_start_menu(update, context)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG.get(DB.get_user_lang(update.effective_user.id), 'help_start'),
                                    reply_markup=KB.inline_back())

# account creation flow (3 steps: name -> username)
async def create_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['create_flow'] = 'name'
    await update.message.reply_text("👤 لطفاً نام کامل خود را ارسال کنید:", reply_markup=KB.cancel_inline())

# process actual downloads + send file
async def process_download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    user = update.effective_user
    platform = utils.detect_platform(url)
    # decide audio only
    audio_only = platform in ("Spotify", "SoundCloud")
    status_msg = await update.message.reply_text(MSG.get(DB.get_user_lang(user.id), 'processing'))
    try:
        filepath, title, file_type = await downloader.download_url(url, audio_only=audio_only)
        p = Path(filepath)
        with open(filepath, 'rb') as f:
            if file_type == 'audio':
                await update.message.reply_audio(f, caption=f"{platform}: {title}")
            else:
                # send as document to avoid compression for large files
                await update.message.reply_document(f, caption=f"{platform}: {title}")
        DB.save_download(user.id, platform, url, title, file_type)
        await status_msg.delete()
    except Exception as e:
        logger.exception("download error")
        try:
            await status_msg.edit_text(MSG.get(DB.get_user_lang(user.id), 'download_error').format(err=str(e)))
        except Exception:
            pass
    finally:
        try:
            if 'filepath' in locals() and Path(filepath).exists():
                downloader.safe_remove(filepath)
        except Exception:
            pass

# message router
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # ---------- check for cancel in create flow ----------
    if text == '⛔️ لغو' and context.user_data.get('create_flow'):
        context.user_data.pop('create_flow', None)
        await update.message.reply_text("عملیات ساخت حساب لغو شد.", reply_markup=KB.start_reply_keyboard())
        return

    # ---------- account creation flow ----------
    if context.user_data.get('create_flow') == 'name':
        # receive name then ask username
        context.user_data['tmp_name'] = text
        context.user_data['create_flow'] = 'username'
        await update.message.reply_text("🆔 لطفا یک یوزرنیم (بدون @) وارد کنید:", reply_markup=KB.cancel_inline())
        return
    if context.user_data.get('create_flow') == 'username':
        username = text.lstrip('@')[:64]
        name = context.user_data.get('tmp_name') or update.effective_user.first_name
        created = DB.create_user(update.effective_user.id, username, name)
        context.user_data.pop('create_flow', None)
        context.user_data.pop('tmp_name', None)
        if created:
            await update.message.reply_text("🎉 حساب با موفقیت ساخته شد! برای ورود به پنل، /start یا دکمه 'ورود خودکار' را بزنید.",
                                            reply_markup=KB.start_reply_keyboard())
        else:
            await update.message.reply_text("⚠️ خطا یا یوزرنیم تکراری است. دوباره تلاش کنید.", reply_markup=KB.start_reply_keyboard())
        return

    # ---------- handle reply-keyboard button texts ----------
    # start menu buttons
    if text == "📖 راهنما":
        await update.message.reply_text(MSG.get(DB.get_user_lang(user.id), 'help_start'), reply_markup=KB.inline_back())
        return
    if text == "📜 قوانین":
        await update.message.reply_text(MSG.get(DB.get_user_lang(user.id), 'rules'), reply_markup=KB.inline_back())
        return
    if text == "ℐ درباره ما":
        await update.message.reply_text(MSG.get(DB.get_user_lang(user.id), 'about'), reply_markup=KB.inline_back())
        return
    if text == "🌐 زبان":
        await update.message.reply_text("لطفا زبان را انتخاب کنید:", reply_markup=KB.language_inline())
        return

    # guest main buttons
    if text == "🧰 منوی اصلی":
        await send_guest_main(update, context)
        return
    if text == "📘 راهنمای منوی اصلی":
        await update.message.reply_text(MSG.get(DB.get_user_lang(user.id), 'help_main_instructions'), reply_markup=KB.inline_back())
        return
    if text == "🔐 ساخت حساب":
        await create_account_start(update, context)
        return
    if text == "🤖 ورود خودکار":
        if DB.user_exists(user.id):
            await send_panel_by_user(update, context)
        else:
            await update.message.reply_text("❗ شما هنوز حساب ندارید. ابتدا ساخت حساب را بزنید.", reply_markup=KB.guest_main_reply())
        return
    if text == "🔙 بازگشت":
        # if user existed go to panel, else start
        if DB.user_exists(user.id):
            await send_panel_by_user(update, context)
        else:
            await send_start_menu(update, context)
        return

    # panel member buttons
    if text == "📘 راهنمای پنل کاربری":
        await update.message.reply_text(MSG.get(DB.get_user_lang(user.id), 'help_panel'), reply_markup=KB.inline_back())
        return
    if text == "📥 دانلودهای اخیر":
        rows = DB.get_downloads_recent(user.id)
        if not rows:
            await update.message.reply_text("🔍 هیچ دانلودی ثبت نشده.", reply_markup=KB.inline_back())
            return
        msg = "📥 دانلودهای اخیر:\n\n"
        for p,t,ft,dt in rows:
            msg += f"• {p} | {ft}\n{t}\n⏱ {dt}\n\n"
        await update.message.reply_text(msg, reply_markup=KB.inline_back())
        return
    if text == "📊 وضعیت حساب":
        cnt = DB.downloads_count_today(user.id)
        limit = DB.get_limits(user.id)
        await update.message.reply_text(f"📊 وضعیت حساب:\n\nدانلودهای امروز: {cnt}/{limit}\nپلتفرم‌های فعال: {'تمامی پلتفرم‌ها' if DB.user_exists(user.id) else 'Instagram, Spotify'}",
                                        reply_markup=KB.inline_back())
        return
    if text == "⚙️ تنظیمات":
        # settings only in panel
        await update.message.reply_text("تنظیمات:", reply_markup=KB.language_inline())
        return
    if text == "ℹ️ درباره ما":
        await update.message.reply_text(MSG.get(DB.get_user_lang(user.id), 'about'), reply_markup=KB.inline_back())
        return

    # ---------- if not a known button -> treat as link or plain text ----------
    if not utils.looks_like_url(text):
        await update.message.reply_text("برای دانلود، یک لینک معتبر ارسال کنید.", reply_markup=KB.start_reply_keyboard())
        return

    # ---------- LINK processing rules ----------
    # disallow downloads when in main_menu view (as requested)
    if context.user_data.get('menu') == 'main_menu':
        await update.message.reply_text("برای دانلود در این بخش امکان‌پذیر نیست. لطفاً به صفحه اصلی (استارت) یا پنل مراجعه کنید.", reply_markup=KB.start_reply_keyboard())
        return

    # check permission by platform (guest vs member)
    platform = utils.detect_platform(text)
    if not DB.user_exists(user.id):
        # guest case: only Instagram & Spotify allowed
        if platform not in ("Instagram", "Spotify"):
            await update.message.reply_text(MSG.get(DB.get_user_lang(user.id), 'guest_restriction'), reply_markup=KB.start_reply_keyboard())
            return
        if DB.downloads_count_today(user.id) >= DB.GUEST_DAILY_LIMIT:
            await update.message.reply_text(MSG.get(DB.get_user_lang(user.id), 'limit_exceeded'), reply_markup=KB.start_reply_keyboard())
            return
        # mark menu if came from start
        context.user_data['menu'] = 'guest_panel'
        # proceed to download
        await process_download_and_send(update, context, text)
        return
    else:
        # member
        if DB.downloads_count_today(user.id) >= DB.USER_DAILY_LIMIT:
            await update.message.reply_text(MSG.get(DB.get_user_lang(user.id), 'limit_exceeded'), reply_markup=KB.user_panel_reply())
            return
        context.user_data['menu'] = 'user_panel'
        await process_download_and_send(update, context, text)
        return

# callbacks for inline
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "back":
        if DB.user_exists(q.from_user.id):
            await send_panel_by_user(update, context)
        else:
            await send_start_menu(update, context)
        return
    if data.startswith("lang_"):
        lang = data.split("_",1)[1]
        # store user lang if user exists, else store in user_data
        if DB.user_exists(q.from_user.id):
            DB.set_user_lang(q.from_user.id, lang)
        else:
            context.user_data['lang'] = lang
        await q.message.reply_text("✅ زبان تغییر کرد.", reply_markup=KB.inline_back())
        return
    if data == "cancel":
        context.user_data.pop('create_flow', None)
        context.user_data.pop('tmp_name', None)
        await q.message.reply_text("✅ عملیات لغو شد.", reply_markup=KB.start_reply_keyboard())
        return

# start app
def main():
    app = Application.builder().token(settings.TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("create_account", create_account_start))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    logger.info("Starting bot...")
    app.run_polling()

if __name__ == "__main__":
    main()
