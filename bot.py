import os, re, datetime, logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from database import init_db, user_exists, create_user, get_user, set_language, set_theme
from keyboards import make_start_inline, make_panel_inline, make_language_inline, make_cancel_inline, CB_HELP, CB_RULES, CB_ABOUT, CB_LANG, CB_CREATE, CB_PANEL, CB_THEME, CB_BACK
from messages import BASE as MBASE
from translator import translate_text
from downloader import start_download, cancel_download, detect_platform

# config
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN not set in env")

logging.basicConfig(level=logging.INFO)

# state
STATE = {}    # uid -> step
PENDING = {}  # uid -> data
DAILY = {}    # uid -> {"date":..., "count":...}

GUEST_LIMIT = 15
MEMBER_LIMIT = 25

def today():
    return datetime.date.today().isoformat()

def check_and_inc(uid, is_member):
    rec = DAILY.get(uid)
    t = today()
    limit = MEMBER_LIMIT if is_member else GUEST_LIMIT
    if not rec or rec.get("date") != t:
        DAILY[uid] = {"date": t, "count": 1}
        return True
    if rec["count"] >= limit: return False
    rec["count"] += 1; return True

# helpers to get message (translate on demand)
def msg(key, lang="fa", **kwargs):
    base = MBASE.get(key, "")
    text = base.format(**kwargs) if isinstance(base, str) else str(base)
    if lang == "fa": return text
    return translate_text(text, lang)

# --- handlers ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    if user:
        language = user.get("language","fa")
        text = msg("start_member", language, name=user.get("name",""))
        kb = make_panel_inline(language)
        await update.message.reply_text(text, reply_markup=kb)
    else:
        text = msg("start_guest", "fa")
        kb = make_start_inline("fa")
        await update.message.reply_text(text, reply_markup=kb)

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ok = cancel_download(uid)
    await update.message.reply_text(msg("cancelled", get_user(uid)["language"] if get_user(uid) else "fa") if ok else "⚠ دانلودی فعال نیست.")

# message handler for free text (including register flow and links)
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    user = get_user(uid)
    lang = user["language"] if user else "fa"
    is_member = bool(user)

    # registration flow via STATE
    if text == "👤 ساخت حساب" or text.lower() == "create account":
        STATE[uid] = "reg_name"
        await update.message.reply_text(msg("reg_name", lang), reply_markup=make_cancel_inline(uid))
        return
    if STATE.get(uid) == "reg_name":
        PENDING[uid] = {"name": text}
        STATE[uid] = "reg_username"
        await update.message.reply_text(msg("reg_username", lang), reply_markup=make_cancel_inline(uid))
        return
    if STATE.get(uid) == "reg_username":
        uname = text.replace("@","").strip()
        if len(uname) < 3:
            await update.message.reply_text("یوزرنیم کوتاه است.", reply_markup=make_cancel_inline(uid)); return
        PENDING[uid]["username"] = uname
        STATE[uid] = "reg_password"
        await update.message.reply_text(msg("reg_password", lang), reply_markup=make_cancel_inline(uid)); return
    if STATE.get(uid) == "reg_password":
        pw = text.strip()
        if len(pw) < 8 or len(pw) > 12 or not re.match(r"^[A-Za-z0-9]+$", pw):
            await update.message.reply_text("پسورد نامعتبر است.", reply_markup=make_cancel_inline(uid)); return
        info = PENDING.pop(uid, {})
        STATE.pop(uid, None)
        ok = create_user(uid, info.get("name","user"), info.get("username","user"), pw)
        if ok:
            await update.message.reply_text(msg("reg_done", lang), reply_markup=make_panel_inline(lang))
        else:
            await update.message.reply_text(msg("reg_fail", lang), reply_markup=make_start_inline(lang))
        return

    # if text is url -> attempt download (but only from start/panel allowed)
    if text.startswith("http"):
        platform = detect_platform(text)
        if not is_member and platform not in ("instagram", "spotify"):
            await update.message.reply_text(msg("guest_block_download", lang), reply_markup=make_start_inline(lang))
            return
        if not check_and_inc(uid, is_member):
            await update.message.reply_text(msg("limit_reached", lang), reply_markup=make_panel_inline(lang))
            return
        msg_reply = await update.message.reply_text(msg("downloading", lang))
        await start_download(uid, text, context.bot, msg_reply)
        return

    # fallback unknown
    await update.message.reply_text(msg("unknown", lang), reply_markup=make_start_inline(lang if not user else user.get("language","fa")))

# callback handler (all inline buttons come here)
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    uid = q.from_user.id
    user = get_user(uid)
    lang = user["language"] if user else "fa"
    await q.answer()

    # language inline special (lang_fa / lang_en / lang_ar)
    if data.startswith("lang_"):
        new = data.split("_")[1]
        set_language(uid, new)
        await q.edit_message_text(translate_text("✅ زبان با موفقیت تغییر کرد.", new))
        return

    # cancel_{uid}
    if data.startswith("cancel_"):
        try:
            target = int(data.split("_")[1])
            if target == uid:
                ok = cancel_download(uid)
                await q.edit_message_text(msg("cancelled", lang))
            else:
                await q.answer("این دکمه برای شما نیست.", show_alert=True)
        except:
            await q.answer()
        return

    # fixed callback_data mapping
    if data == "help":
        await q.edit_message_text(msg("help_member" if user else "help_guest", lang), reply_markup=make_cancel_inline(uid))
        return
    if data == "rules":
        await q.edit_message_text(msg("rules", lang), reply_markup=make_cancel_inline(uid)); return
    if data == "about":
        await q.edit_message_text(msg("about", lang), reply_markup=make_cancel_inline(uid)); return
    if data == "lang":
        await q.edit_message_text(msg("choose_language", lang), reply_markup=make_language_inline()); return
    if data == "create":
        # start reg
        STATE[uid] = "reg_name"
        await q.edit_message_text(msg("reg_name", lang)); return
    if data == "back":
        # send start or panel
        if user:
            await q.edit_message_text(msg("start_member", user.get("language","fa"), name=user.get("name","")), reply_markup=make_panel_inline(user.get("language","fa")))
        else:
            await q.edit_message_text(msg("start_guest", "fa"), reply_markup=make_start_inline("fa"))
        return

# main
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Railway-friendly run (blocking)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
