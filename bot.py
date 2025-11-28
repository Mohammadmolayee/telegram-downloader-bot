# bot.py
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
from messages import t
import keyboards as kb
import database as db
import downloader as dl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# state holders
_user_state = {}    # {user_id: step}
_pending = {}       # {user_id: {...}}

# helpers
def lang_for_user(user_id, context):
    user = db.get_user(user_id)
    if user:
        return user.get("language", "fa")
    return context.user_data.get("language", "fa") or "fa"

def theme_for_user(user_id, context):
    user = db.get_user(user_id)
    if user:
        return user.get("theme", "light")
    return context.user_data.get("theme", "light") or "light"

# start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if db.user_exists(uid):
        user = db.get_user(uid)
        lang = user.get("language", "fa")
        text = t(user, "panel_welcome", user_name=user.get("name"), username=user.get("username"),
                 theme=user.get("theme"), language=user.get("language"))
        await update.message.reply_text(text, reply_markup=kb.panel_reply(lang))
        context.user_data['menu'] = 'panel'
    else:
        lang = context.user_data.get("language", "fa")
        await update.message.reply_text(t({"language": lang}, "start_guest"), reply_markup=kb.start_reply(lang))
        context.user_data['menu'] = 'start'

# message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    uid = update.effective_user.id
    user = db.get_user(uid)
    lang = lang_for_user(uid, context)

    # universal back button (reply keyboard)
    if text in ["🔙 بازگشت", "🔙 Back"]:
        menu = context.user_data.get("menu", "start")
        if menu == "panel" and db.user_exists(uid):
            await update.message.reply_text(t({"language": lang}, "panel_welcome",
                                              user_name=user.get("name"), username=user.get("username"),
                                              theme=user.get("theme"), language=user.get("language")),
                                            reply_markup=kb.panel_reply(lang))
            context.user_data['menu'] = 'panel'
            return
        # default to start
        await update.message.reply_text(t({"language": lang}, "start_guest"), reply_markup=kb.start_reply(lang))
        context.user_data['menu'] = 'start'
        return

    # start menu buttons (guest)
    if text in ["📖 راهنما", "📖 Help"]:
        key = "help_member" if user else "help_guest"
        await update.message.reply_text(t({"language": lang}, key), reply_markup=kb.start_reply(lang) if not user else kb.panel_reply(lang))
        return

    if text in ["📜 قوانین", "📜 Rules"]:
        await update.message.reply_text(t({"language": lang}, "rules"), reply_markup=kb.start_reply(lang) if not user else kb.panel_reply(lang))
        return

    if text in ["ℹ درباره ما", "ℹ About"]:
        await update.message.reply_text(t({"language": lang}, "about"), reply_markup=kb.start_reply(lang) if not user else kb.panel_reply(lang))
        return

    if text in ["🌐 زبان", "🌐 Language"]:
        await update.message.reply_text(t({"language": lang}, "choose_language"), reply_markup=kb.language_inline())
        return

    # create account (in guest panel)
    if text in ["👤 ساخت حساب", "👤 Create Account"]:
        _user_state[uid] = "reg_name"
        await update.message.reply_text(t({"language": lang}, "reg_name"))
        return

    # registration flow
    if _user_state.get(uid) == "reg_name":
        _pending[uid] = {"name": text}
        _user_state[uid] = "reg_username"
        await update.message.reply_text(t({"language": lang}, "reg_username"))
        return

    if _user_state.get(uid) == "reg_username":
        _pending[uid]["username"] = text.lstrip("@")
        _user_state[uid] = "reg_password"
        await update.message.reply_text(t({"language": lang}, "reg_password"))
        return

    if _user_state.get(uid) == "reg_password":
        info = _pending.get(uid, {})
        name = info.get("name") or update.effective_user.first_name
        username = info.get("username") or f"user{uid}"
        password = text
        ok = db.create_user(uid, name, username, password)
        _user_state.pop(uid, None)
        _pending.pop(uid, None)
        if ok:
            # auto login: send panel
            user = db.get_user(uid)
            await update.message.reply_text(t({"language": lang}, "reg_done"), reply_markup=kb.panel_reply(lang))
            # send panel details
            await update.message.reply_text(t(user, "panel_welcome", user_name=user.get("name"),
                                              username=user.get("username"),
                                              theme=user.get("theme"),
                                              language=user.get("language")),
                                            reply_markup=kb.panel_reply(lang))
            context.user_data['menu'] = 'panel'
        else:
            await update.message.reply_text(t({"language": lang}, "reg_fail"), reply_markup=kb.start_reply(lang))
        return

    # panel buttons (for logged users) and guest download button
    if text in ["📥 دانلود", "📥 Download", "📥 دانلود (مهمان)", "📥 Download (Guest)"]:
        # if in main start area and guest, allow guest download or instruct
        if not db.user_exists(uid):
            # allow guest limited: Instagram & Spotify
            await update.message.reply_text(t({"language": lang}, "guest_download"), reply_markup=kb.start_reply(lang))
            context.user_data['menu'] = 'start'
            return
        else:
            await update.message.reply_text(t({"language": lang}, "downloading"), reply_markup=kb.panel_reply(lang))
            context.user_data['menu'] = 'panel'
            return

    if text in ["📖 راهنمای پنل", "📖 Panel Help"]:
        await update.message.reply_text(t({"language": lang}, "help_member"), reply_markup=kb.panel_reply(lang))
        return

    if text in ["🎨 تنظیمات", "🎨 Settings"]:
        await update.message.reply_text(t({"language": lang}, "settings"), reply_markup=kb.settings_reply(lang))
        return

    if text in ["🌐 تغییر زبان", "🌐 Change Language"]:
        await update.message.reply_text(t({"language": lang}, "choose_language"), reply_markup=kb.language_inline())
        return

    if text in ["🎨 تغییر تم", "🎨 Theme"]:
        await update.message.reply_text(t({"language": lang}, "choose_theme"), reply_markup=kb.theme_inline())
        return

    # If message is a URL -> attempt download
    if text.startswith("http"):
        # check menu block: if user in "start" but pressed non-guest-download button we block
        cur_menu = context.user_data.get("menu", "start")
        # Allow download in start (guest) and panel
        if cur_menu == "main_menu":
            await update.message.reply_text(t({"language": lang}, "guest_download_block"))
            return
        # schedule background download using downloader.start_download_task
        try:
            # schedule: user-specific language
            user_lang = lang
            await dl.start_download_task(context.application, uid, text, user_lang)
            await update.message.reply_text(t({"language": user_lang}, "downloading"), reply_markup=kb.cancel_inline(user_lang))
        except Exception as e:
            logger.exception("Failed to start download task")
            await update.message.reply_text(t({"language": lang}, "download_error"))
        return

    # unknown
    await update.message.reply_text(t({"language": lang}, "unknown"), reply_markup=kb.start_reply(lang))


# callback handler for inline keyboards (language/theme/cancel)
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    data = q.data
    uid = q.from_user.id
    user = db.get_user(uid)
    lang = lang_for_user(uid, context)

    if data.startswith("lang_"):
        new = data.split("_", 1)[1]
        if user:
            db.set_language(uid, new)
        else:
            context.user_data["language"] = new
        await q.edit_message_text(t({"language": new}, "lang_changed"))
        return

    if data.startswith("theme_"):
        new = data.split("_", 1)[1]
        if user:
            db.set_theme(uid, new)
        else:
            context.user_data["theme"] = new
        await q.edit_message_text(t({"language": lang}, "theme_changed"))
        return

    if data == "cancel_download":
        dl.cancel_download(uid)
        await q.edit_message_text(t({"language": lang}, "cancel_download"))
        return

# main (synchronous run_polling)
def main():
    db.init_db()
    token = os.getenv("TOKEN") or os.getenv("BOT_TOKEN") or ""
    if not token:
        logger.error("TOKEN environment variable not set. Set TOKEN in Railway variables.")
        return
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(callbacks))

    logger.info("Bot is starting (run_polling)...")
    app.run_polling()
    logger.info("Bot stopped.")

if __name__ == "__main__":
    main()
