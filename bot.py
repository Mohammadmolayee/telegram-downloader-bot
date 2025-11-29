import os, logging, re, datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from database import init_db, user_exists, create_user, get_user, set_language, set_theme, login
from keyboards import start_keyboard, panel_keyboard, language_inline, cancel_inline
from messages import get_text
from downloader import start_download, cancel_download, RUNNING

# config
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN env not set")

logging.basicConfig(level=logging.INFO)

# simple in-memory state for registration
STATE = {}  # uid -> step
PENDING = {}  # uid -> data

# simple per-day counters (non-persistent; restart resets) -> for lightweight VPS
DAILY = {}  # uid -> {date:str, count:int}

# limits
GUEST_LIMIT = 15
MEMBER_LIMIT = 25

def today_str():
    return datetime.date.today().isoformat()

def inc_count(uid):
    d = DAILY.get(uid)
    t = today_str()
    if not d or d.get("date") != t:
        DAILY[uid] = {"date": t, "count": 1}
        return 1
    d["count"] += 1
    return d["count"]

def check_limit(uid, is_member):
    cnt = DAILY.get(uid, {"date": today_str(), "count": 0})["count"]
    lim = MEMBER_LIMIT if is_member else GUEST_LIMIT
    return cnt < lim

# -------- commands --------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    lang = user["language"] if user else "fa"
    if user:
        text = get_text("start_member", lang, name=user.get("name",""))
        await update.message.reply_text(text, reply_markup=panel_keyboard(lang))
    else:
        text = get_text("start_guest", "fa")
        await update.message.reply_text(text, reply_markup=start_keyboard("fa"))

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ok = cancel_download(uid)
    if ok:
        await update.message.reply_text("❌ دانلود لغو شد.")
    else:
        await update.message.reply_text("⚠ دانلود فعالی وجود ندارد.")

# -------- message handler --------
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    user = get_user(uid)
    lang = user["language"] if user else "fa"
    is_member = bool(user)

    # back button (reply)
    if text in ["🔙 بازگشت", "🔙 Back"]:
        if is_member:
            await update.message.reply_text(get_text("start_member", lang, name=user.get("name","")), reply_markup=panel_keyboard(lang))
        else:
            await update.message.reply_text(get_text("start_guest","fa"), reply_markup=start_keyboard("fa"))
        return

    # language
    if text in ["🌐 زبان", "🌐 Language"]:
        await update.message.reply_text(get_text("choose_language", lang), reply_markup=language_inline())
        return

    # about / rules / help
    if text in ["ℹ درباره ما","ℹ About"]:
        await update.message.reply_text(get_text("about", lang), reply_markup=cancel_inline(uid))
        return
    if text in ["📜 قوانین","📜 Rules"]:
        await update.message.reply_text(get_text("rules", lang), reply_markup=cancel_inline(uid))
        return
    if text in ["📖 راهنما","📖 Help"]:
        key = "help_member" if is_member else "help_guest"
        await update.message.reply_text(get_text(key, lang), reply_markup=cancel_inline(uid))
        return

    # register flow
    if text in ["👤 ساخت حساب","👤 Create Account"]:
        STATE[uid] = "reg_name"
        await update.message.reply_text(get_text("reg_name", lang), reply_markup=cancel_inline(uid))
        return
    step = STATE.get(uid)
    if step == "reg_name":
        PENDING[uid] = {"name": text}
        STATE[uid] = "reg_username"
        await update.message.reply_text(get_text("reg_username", lang), reply_markup=cancel_inline(uid))
        return
    if step == "reg_username":
        uname = text.replace("@","").strip()
        if len(uname) < 3:
            await update.message.reply_text("یوزرنیم کوتاه است.", reply_markup=cancel_inline(uid)); return
        PENDING[uid]["username"] = uname
        STATE[uid] = "reg_password"
        await update.message.reply_text(get_text("reg_password", lang), reply_markup=cancel_inline(uid)); return
    if step == "reg_password":
        pw = text.strip()
        if len(pw) < 8 or len(pw) > 12 or not re.match(r"^[A-Za-z0-9]+$", pw):
            await update.message.reply_text("پسورد نامعتبر است.", reply_markup=cancel_inline(uid)); return
        info = PENDING.pop(uid, {})
        STATE.pop(uid, None)
        ok = create_user(uid, info.get("name","user"), info.get("username","user"), pw)
        if ok:
            await update.message.reply_text(get_text("reg_done", lang), reply_markup=panel_keyboard(lang))
            return
        else:
            await update.message.reply_text(get_text("reg_fail", lang), reply_markup=start_keyboard(lang))
            return

    # theme (from panel) - simple textual selection
    if text in ["🎨 تغییر تم","🎨 Theme"]:
        # show choices
        await update.message.reply_text(get_text("choose_theme", lang), reply_markup=cancel_inline(uid))
        return
    if text in ["🌙 Dark","Dark","تاریک"]:
        set_theme(uid, "dark"); await update.message.reply_text(get_text("theme_changed", lang)); return
    if text in ["☀️ Light","Light","روشن"]:
        set_theme(uid, "light"); await update.message.reply_text(get_text("theme_changed", lang)); return

    # link handling -> only allowed in guest panel or member panel (we enforce: start menu or panel)
    if text.startswith("http"):
        # only allow if user is in start/panel (we may assume yes)
        if not check_limit_and_increment(uid, is_member):
            await update.message.reply_text("⚠️ محدودیت دانلود روزانه رسیده.", reply_markup=cancel_inline(uid)); return
        # guest limitations on platforms
        platform = detect_platform_simple(text)
        if not is_allowed_for_user(platform, is_member):
            await update.message.reply_text("⚠️ این لینک برای سطح شما پشتیبانی نمی‌شود. برای فعال شدن کامل، حساب بساز.", reply_markup=panel_keyboard(lang))
            return
        # start download
        msg = await update.message.reply_text(get_text("downloading", lang))
        await start_download(uid, text, context.bot, lang, msg)  # schedules background task
        return

    # unknown
    await update.message.reply_text(get_text("unknown", lang), reply_markup=cancel_inline(uid))

# small helpers
def detect_platform_simple(url):
    u = url.lower()
    if "youtube" in u or "youtu.be" in u: return "youtube"
    if "tiktok" in u: return "tiktok"
    if "soundcloud" in u: return "soundcloud"
    if "instagram" in u: return "instagram"
    if "spotify" in u: return "spotify"
    return "unknown"

def is_allowed_for_user(platform, is_member):
    # guest -> only instagram + spotify
    if is_member: return True
    return platform in ("instagram","spotify")

def check_limit_and_increment(uid, is_member):
    # check and increment; returns True if allowed
    # this uses database-free DAILY counter in memory for lightness
    from database import get_user as _g
    # ensure date reset inside DAILY handled in check_limit usage earlier (we use DA ILY in main module)
    return check_and_inc(uid, is_member)

# we put DAILY logic centralized to avoid duplication
from collections import defaultdict
_INTERNAL_DAILY = {}
def check_and_inc(uid, is_member):
    t = today_str()
    rec = _INTERNAL_DAILY.get(uid)
    lim = MEMBER_LIMIT if is_member else GUEST_LIMIT
    if not rec or rec.get("date") != t:
        _INTERNAL_DAILY[uid] = {"date": t, "count": 1}; return True
    if rec["count"] >= lim: return False
    rec["count"] += 1; return True

# callback handler for inline (language change / cancel)
async def callback_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; data = q.data; uid = q.from_user.id
    if data.startswith("lang_"):
        lang = data.split("_")[1]; set_language(uid, lang)
        await q.answer("زبان تغییر کرد"); await q.edit_message_text(get_text("lang_changed", lang))
        return
    if data.startswith("cancel_"):
        # cancel_{uid}
        target_uid = int(data.split("_")[1])
        if target_uid == uid:
            ok = cancel_download(uid)
            await q.answer()
            if ok: await q.edit_message_text("❌ دانلود لغو شد.")
            else: await q.edit_message_text("⚠ دانلود فعالی وجود نداشت.")
        else:
            await q.answer("این دکمه برای شما نیست.", show_alert=True)

# -------- main --------
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CallbackQueryHandler(callback_q))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

    # Railway-safe run
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
