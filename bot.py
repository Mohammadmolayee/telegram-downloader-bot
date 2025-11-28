# bot.py
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import database as db
import keyboards as kb
import downloader as dl
import translator as tr
from messages import t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_user_state = {}
_pending = {}

def _lang(uid, context):
    u = db.get_user(uid)
    if u:
        return u.get("language", "fa")
    return context.user_data.get("language", "fa") or "fa"

def _set_guest_lang(context, lang):
    context.user_data["language"] = lang

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    if user:
        lang = user.get("language", "fa")
        await update.message.reply_text(t(user, "panel_welcome", user_name=user.get("name"), username=user.get("username"), theme=user.get("theme"), language=user.get("language")), reply_markup=kb.panel_reply(lang))
        context.user_data["menu"] = "panel"
    else:
        lang = context.user_data.get("language", "fa")
        await update.message.reply_text(t({"language": lang}, "start_guest"), reply_markup=kb.start_reply(lang))
        context.user_data["menu"] = "start"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    txt = update.message.text.strip()
    uid = update.effective_user.id
    user = db.get_user(uid)
    lang = _lang(uid, context)

    # universal back (compare with translated BTN_BACK)
    if txt == tr.btn(lang, "BTN_BACK"):
        if user:
            await update.message.reply_text(t(user, "panel_welcome", user_name=user.get("name"), username=user.get("username"), theme=user.get("theme"), language=user.get("language")), reply_markup=kb.panel_reply(lang))
            context.user_data["menu"] = "panel"
        else:
            glang = context.user_data.get("language", "fa")
            await update.message.reply_text(t({"language": glang}, "start_guest"), reply_markup=kb.start_reply(glang))
            context.user_data["menu"] = "start"
        return

    # Guest buttons (compare translated labels)
    if txt == tr.btn(lang, "BTN_HELP"):
        await update.message.reply_text(t({"language": lang}, "help_guest" if not user else "help_member"), reply_markup=kb.back_only(lang))
        return
    if txt == tr.btn(lang, "BTN_RULES"):
        await update.message.reply_text(t({"language": lang}, "rules"), reply_markup=kb.back_only(lang))
        return
    if txt == tr.btn(lang, "BTN_ABOUT"):
        await update.message.reply_text(t({"language": lang}, "about"), reply_markup=kb.back_only(lang))
        return
    if txt == tr.btn(lang, "BTN_FEATURES"):
        await update.message.reply_text(t({"language": lang}, "features_text"), reply_markup=kb.back_only(lang))
        return
    if txt == tr.btn(lang, "BTN_LANGUAGE"):
        await update.message.reply_text(t({"language": lang}, "choose_language"), reply_markup=kb.language_inline())
        return
    if txt == tr.btn(lang, "BTN_CREATE"):
        _user_state[uid] = "reg_name"
        await update.message.reply_text(t({"language": lang}, "reg_name"))
        return

    # registration flow
    if _user_state.get(uid) == "reg_name":
        _pending[uid] = {"name": txt}
        _user_state[uid] = "reg_username"
        await update.message.reply_text(t({"language": lang}, "reg_username"))
        return
    if _user_state.get(uid) == "reg_username":
        _pending[uid]["username"] = txt.lstrip("@")
        _user_state[uid] = "reg_password"
        await update.message.reply_text(t({"language": lang}, "reg_password"))
        return
    if _user_state.get(uid) == "reg_password":
        info = _pending.pop(uid, {})
        _user_state.pop(uid, None)
        name = info.get("name") or update.effective_user.first_name
        username = info.get("username") or f"user{uid}"
        password = txt
        ok = db.create_user(uid, name, username, password)
        if ok:
            user = db.get_user(uid)
            await update.message.reply_text(t({"language": lang}, "reg_done"), reply_markup=kb.panel_reply(lang))
            await update.message.reply_text(t(user, "panel_welcome", user_name=user.get("name"), username=user.get("username"), theme=user.get("theme"), language=user.get("language")), reply_markup=kb.panel_reply(lang))
            context.user_data["menu"] = "panel"
        else:
            await update.message.reply_text(t({"language": lang}, "reg_fail"), reply_markup=kb.start_reply(lang))
        return

    # Panel buttons (user)
    if user:
        if txt == tr.btn(lang, "BTN_DOWNLOAD"):
            await update.message.reply_text(t({"language": lang}, "send_link"), reply_markup=kb.panel_reply(lang))
            return
        if txt == tr.btn(lang, "BTN_SETTINGS"):
            await update.message.reply_text(t({"language": lang}, "settings"), reply_markup=kb.settings_reply(lang))
            return
        if txt == tr.btn(lang, "BTN_PANEL_HELP"):
            await update.message.reply_text(t({"language": lang}, "help_member"), reply_markup=kb.back_only(lang))
            return

    # settings shortcuts (reply keyboard entries)
    if txt == tr.btn(lang, "BTN_LANGUAGE"):
        await update.message.reply_text(t({"language": lang}, "choose_language"), reply_markup=kb.language_inline())
        return
    if txt == tr.btn(lang, "BTN_SETTINGS"):
        await update.message.reply_text(t({"language": lang}, "choose_theme"), reply_markup=kb.theme_inline())
        return

    # URL handling
    if txt.startswith("http"):
        if not user:
            # guest allowed only instagram & spotify
            if ("instagram" in txt) or ("instagr" in txt) or ("spotify" in txt):
                guest_lang = context.user_data.get("language", "fa")
                await dl.start_download_task(context.application, uid, txt, guest_lang)
                await update.message.reply_text(tr.t(guest_lang, "downloading"), reply_markup=kb.cancel_inline(guest_lang))
                return
            else:
                await update.message.reply_text(t({"language": _lang(uid, context)}, "guest_block_download"), reply_markup=kb.start_reply(_lang(uid, context)))
                return
        else:
            await dl.start_download_task(context.application, uid, txt, _lang(uid, context))
            await update.message.reply_text(tr.t(_lang(uid, context), "downloading"), reply_markup=kb.cancel_inline(_lang(uid, context)))
            return

    await update.message.reply_text(t({"language": lang}, "unknown"), reply_markup=kb.start_reply(lang) if not user else kb.panel_reply(lang))

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    uid = q.from_user.id
    data = q.data
    user = db.get_user(uid)
    lang = _lang(uid, context)

    if data.startswith("lang_"):
        new = data.split("_", 1)[1]
        if user:
            db.set_language(uid, new)
        else:
            _set_guest_lang(context, new)
        # notify and re-show appropriate menu
        await q.edit_message_text(tr.t(new, "lang_changed"))
        if user:
            await q.message.reply_text(t(user, "panel_welcome", user_name=user.get("name"), username=user.get("username"), theme=user.get("theme"), language=new), reply_markup=kb.panel_reply(new))
            context.user_data["menu"] = "panel"
        else:
            await q.message.reply_text(t({"language": new}, "start_guest"), reply_markup=kb.start_reply(new))
            context.user_data["menu"] = "start"
        return

    if data.startswith("theme_"):
        new = data.split("_", 1)[1]
        if user:
            db.set_theme(uid, new)
        else:
            context.user_data["theme"] = new
        await q.edit_message_text(tr.t(lang, "theme_changed"))
        return

    if data == "cancel_download":
        dl.cancel_download(uid)
        await q.edit_message_text(tr.t(lang, "cancel_download"))
        return

def main():
    db.init_db()
    token = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        logger.error("TOKEN env var missing")
        return
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot starting...")
    app.run_polling()
    logger.info("Bot stopped.")

if __name__ == "__main__":
    main()
