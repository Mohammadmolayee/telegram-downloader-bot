# bot.py – نسخه اصلاح‌شده بدون باگ
import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

import database as db
import keyboards as kb
import downloader as dl
from messages import t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_user_state = {}
_pending = {}


def get_lang(uid, context):
    user = db.get_user(uid)
    if user:
        return user["language"]
    return context.user_data.get("lang", "fa")


def set_lang_guest(context, lang):
    context.user_data["lang"] = lang


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if db.user_exists(uid):
        user = db.get_user(uid)
        lang = user["language"]
        await update.message.reply_text(
            t(user, "panel_welcome",
              user_name=user["name"],
              username=user["username"],
              theme=user["theme"],
              language=user["language"]),
            reply_markup=kb.panel_reply(lang)
        )
        context.user_data["menu"] = "panel"
    else:
        lang = "fa"
        set_lang_guest(context, "fa")
        await update.message.reply_text(
            t({"language": lang}, "start_guest"),
            reply_markup=kb.start_reply(lang)
        )
        context.user_data["menu"] = "start"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    txt = update.message.text
    uid = update.effective_user.id
    user = db.get_user(uid)
    lang = get_lang(uid, context)

    # ---------- دکمه برگشت ----------
    if txt in ["🔙 بازگشت", "🔙 Back"]:
        menu = context.user_data.get("menu", "start")

        # مهمان برگشت → منوی مهمان
        if not user:
            await update.message.reply_text(
                t({"language": lang}, "start_guest"),
                reply_markup=kb.start_reply(lang)
            )
            context.user_data["menu"] = "start"
            return

        # عضو برگشت
        user = db.get_user(uid)
        await update.message.reply_text(
            t(user, "panel_welcome",
              user_name=user["name"],
              username=user["username"],
              theme=user["theme"],
              language=user["language"]),
            reply_markup=kb.panel_reply(lang)
        )
        context.user_data["menu"] = "panel"
        return

    # ---------- دکمه‌ها ----------
    if txt in ["📖 راهنما", "📖 Help"]:
        key = "help_member" if user else "help_guest"
        await update.message.reply_text(
            t({"language": lang}, key),
            reply_markup=kb.back_only(lang)
        )
        return

    if txt in ["📜 قوانین", "📜 Rules"]:
        await update.message.reply_text(
            t({"language": lang}, "rules"),
            reply_markup=kb.back_only(lang)
        )
        return

    if txt in ["ℹ درباره ما", "ℹ About"]:
        await update.message.reply_text(
            t({"language": lang}, "about"),
            reply_markup=kb.back_only(lang)
        )
        return

    if txt in ["🌐 زبان", "🌐 Language"]:
        await update.message.reply_text(
            t({"language": lang}, "choose_language"),
            reply_markup=kb.language_inline()
        )
        return

    # ---------- ساخت حساب ----------
    if txt in ["👤 ساخت حساب", "👤 Create Account"]:
        _user_state[uid] = "reg_name"
        await update.message.reply_text(t({"language": lang}, "reg_name"))
        return

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
        info = _pending[uid]
        ok = db.create_user(uid, info["name"], info["username"], txt)

        _user_state.pop(uid)
        _pending.pop(uid)

        if not ok:
            await update.message.reply_text(
                t({"language": lang}, "reg_fail"),
                reply_markup=kb.start_reply(lang)
            )
            return

        # Auto-login
        user = db.get_user(uid)
        await update.message.reply_text(
            t({"language": lang}, "reg_done"),
            reply_markup=kb.panel_reply(lang)
        )
        await update.message.reply_text(
            t(user, "panel_welcome",
              user_name=user["name"],
              username=user["username"],
              theme=user["theme"],
              language=user["language"]),
            reply_markup=kb.panel_reply(lang)
        )
        context.user_data["menu"] = "panel"
        return

    # ---------- تنظیمات ----------
    if txt in ["🎨 تنظیمات", "🎨 Settings"]:
        await update.message.reply_text(
            t({"language": lang}, "settings"),
            reply_markup=kb.settings_reply(lang)
        )
        return

    if txt in ["🌐 تغییر زبان", "🌐 Change Language"]:
        await update.message.reply_text(
            t({"language": lang}, "choose_language"),
            reply_markup=kb.language_inline()
        )
        return

    if txt in ["🎨 تغییر تم", "🎨 Theme"]:
        await update.message.reply_text(
            t({"language": lang}, "choose_theme"),
            reply_markup=kb.theme_inline()
        )
        return

    # ------------------ دانلود ------------------
    if txt.startswith("http"):
        # مهمان فقط دو پلتفرم
        if not user:
            if "instagram" in txt or "spotify" in txt:
                await dl.start_download_task(context.application, uid, txt, lang)
                await update.message.reply_text(
                    t({"language": lang}, "downloading"),
                    reply_markup=kb.cancel_inline(lang)
                )
                return
            else:
                await update.message.reply_text(
                    "⚠️ برای دانلود از این پلتفرم باید حساب بسازی.",
                    reply_markup=kb.start_reply(lang)
                )
                return

        # عضو → دسترسی کامل
        await dl.start_download_task(context.application, uid, txt, lang)
        await update.message.reply_text(
            t({"language": lang}, "downloading"),
            reply_markup=kb.cancel_inline(lang)
        )
        return

    # ---------- ناشناس ----------
    await update.message.reply_text(
        t({"language": lang}, "unknown"),
        reply_markup=kb.start_reply(lang) if not user else kb.panel_reply(lang)
    )


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    lang = get_lang(uid, context)
    user = db.get_user(uid)

    if q.data.startswith("lang_"):
        new = q.data.split("_")[1]

        # update language
        if user:
            db.set_language(uid, new)
        else:
            set_lang_guest(context, new)

        # apply immediately
        await q.edit_message_text(
            t({"language": new}, "lang_changed")
        )

        # refresh keyboard
        if user:
            await q.message.reply_text(
                t(user, "panel_welcome",
                  user_name=user["name"],
                  username=user["username"],
                  theme=user["theme"],
                  language=new),
                reply_markup=kb.panel_reply(new)
            )
            context.user_data["menu"] = "panel"
        else:
            await q.message.reply_text(
                t({"language": new}, "start_guest"),
                reply_markup=kb.start_reply(new)
            )
            context.user_data["menu"] = "start"
        return

    if q.data.startswith("theme_"):
        new = q.data.split("_")[1]
        if user:
            db.set_theme(uid, new)
        else:
            context.user_data["theme"] = new
        await q.edit_message_text(t({"language": lang}, "theme_changed"))
        return

    if q.data == "cancel_download":
        dl.cancel_download(uid)
        await q.edit_message_text(t({"language": lang}, "cancel_download"))
        return


def main():
    db.init_db()
    token = os.getenv("TOKEN")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
