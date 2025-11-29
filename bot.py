# bot.py (main)
import os, re, datetime, logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from database import init_db, user_exists, create_user, get_user, set_language, set_theme, get_last_downloads, get_stats
from keyboards import guest_keyboard, member_keyboard, back_keyboard, cancel_keyboard
from messages import BASE, BUTTONS
from translator import translate_text
from downloader import start_download, cancel_download, detect_platform

# config
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN not set in env")

logging.basicConfig(level=logging.INFO)

# state containers
STATE = {}    # uid -> registration step
PENDING = {}  # uid -> pending data
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

# helpers
def localized_text(key, lang="fa", **kwargs):
    base = BASE.get(key, "")
    text = base.format(**kwargs) if isinstance(base, str) else str(base)
    if lang == "fa": return text
    return translate_text(text, lang)

def translate_button(label_key, lang="fa"):
    # label_key is a BUTTONS value key or direct string
    if label_key in BUTTONS:
        text = BUTTONS[label_key]
    else:
        text = label_key
    if lang == "fa": return text
    return translate_text(text, lang)

def match_action_from_text(text, lang="fa"):
    """
    Compare incoming reply text to translated labels for known actions.
    Return action key (e.g. 'help','rules',...) or None
    """
    for key, fa_label in BUTTONS.items():
        tlabel = translate_text(fa_label, lang) if lang != "fa" else fa_label
        if text.strip() == tlabel:
            return key
    # also handle back/cancel plain texts
    return None

# handlers
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)
    if user:
        lang = user.get("language","fa")
        text = localized_text("start_member", lang, name=user.get("name",""))
        kb = member_keyboard(lang)
        await update.message.reply_text(text, reply_markup=kb)
    else:
        lang = "fa"
        text = localized_text("start_guest", lang)
        kb = guest_keyboard(lang)
        await update.message.reply_text(text, reply_markup=kb)

async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ok = cancel_download(uid)
    user = get_user(uid)
    lang = user["language"] if user else "fa"
    if ok:
        await update.message.reply_text(localized_text("cancelled", lang), reply_markup=member_keyboard(lang) if user else guest_keyboard(lang))
    else:
        await update.message.reply_text("⚠ دانلودی فعال نیست.", reply_markup=member_keyboard(lang) if user else guest_keyboard(lang))

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id
    user = get_user(uid)
    lang = user["language"] if user else "fa"
    is_member = bool(user)

    # registration flow via STATE
    if STATE.get(uid) == "reg_name":
        PENDING[uid] = {"name": text}
        STATE[uid] = "reg_username"
        await update.message.reply_text(localized_text("reg_username", lang), reply_markup=cancel_keyboard(lang))
        return
    if STATE.get(uid) == "reg_username":
        uname = text.replace("@","").strip()
        if len(uname) < 3:
            await update.message.reply_text("یوزرنیم کوتاه است.", reply_markup=cancel_keyboard(lang)); return
        PENDING[uid]["username"] = uname
        STATE[uid] = "reg_password"
        await update.message.reply_text(localized_text("reg_password", lang), reply_markup=cancel_keyboard(lang)); return
    if STATE.get(uid) == "reg_password":
        pw = text.strip()
        if len(pw) < 8 or len(pw) > 12 or not re.match(r"^[A-Za-z0-9]+$", pw):
            await update.message.reply_text("پسورد نامعتبر است.", reply_markup=cancel_keyboard(lang)); return
        info = PENDING.pop(uid, {})
        STATE.pop(uid, None)
        ok = create_user(uid, info.get("name","user"), info.get("username","user"), pw)
        if ok:
            await update.message.reply_text(localized_text("reg_done", lang), reply_markup=member_keyboard(lang))
        else:
            await update.message.reply_text(localized_text("reg_fail", lang), reply_markup=guest_keyboard(lang))
        return

    # match Reply Keyboard actions (translated)
    action = match_action_from_text(text, lang)
    if action:
        # handle actions
        if action == "help":
            key = "help_member" if is_member else "help_guest"
            await update.message.reply_text(localized_text(key, lang), reply_markup=back_keyboard(lang))
            return
        if action == "rules":
            await update.message.reply_text(localized_text("rules", lang), reply_markup=back_keyboard(lang)); return
        if action == "about":
            await update.message.reply_text(localized_text("about", lang), reply_markup=back_keyboard(lang)); return
        if action == "features":
            key = "features_member" if is_member else "features_guest"
            await update.message.reply_text(localized_text(key, lang), reply_markup=back_keyboard(lang)); return
        if action == "language":
            # show language options as simple messages with replies for selection
            # we send three labels, user taps them (we'll match them)
            lab_fa = translate_text("🇮🇷 فارسی", lang) if lang!="fa" else "🇮🇷 فارسی"
            lab_en = translate_text("🇬🇧 English", lang) if lang!="fa" else "🇬🇧 English"
            lab_ar = translate_text("🇸🇦 العربية", lang) if lang!="fa" else "🇸🇦 العربية"
            await update.message.reply_text(localized_text("choose_language", lang) + f"\n\n{lab_fa}\n{lab_en}\n{lab_ar}", reply_markup=back_keyboard(lang))
            return
        if action == "create":
            STATE[uid] = "reg_name"
            await update.message.reply_text(localized_text("reg_name", lang), reply_markup=cancel_keyboard(lang))
            return
        if action == "stats":
            if not is_member:
                await update.message.reply_text(localized_text("guest_block_download", lang), reply_markup=guest_keyboard(lang))
                return
            # show last downloads and stats
            rows = get_last_downloads(uid, limit=5)
            stats = get_stats(uid)
            text_out = "📄 دانلود اخیر شما:\n\n"
            if not rows:
                text_out += "هیچ دانلودی یافت نشد."
            else:
                i = 1
                for r in rows:
                    platform, fname, created = r
                    text_out += f"{i}) {platform} — {fname or ''}\n⏱ {created}\n\n"
                    i += 1
            text_out += f"📊 آمار کلی:\nتمام دانلودها: {stats['total']}\nویدیو: {stats['video']}\nموسیقی: {stats['audio']}"
            await update.message.reply_text(translate_text(text_out, lang) if lang!="fa" else text_out, reply_markup=member_keyboard(lang))
            return
        if action == "settings":
            await update.message.reply_text(localized_text("choose_theme", lang), reply_markup=back_keyboard(lang)); return
        if action == "back":
            if is_member:
                await update.message.reply_text(localized_text("start_member", lang, name=user.get("name","")), reply_markup=member_keyboard(lang))
            else:
                await update.message.reply_text(localized_text("start_guest", "fa"), reply_markup=guest_keyboard("fa"))
            return
        if action == "cancel":
            ok = cancel_download(uid)
            await update.message.reply_text(localized_text("cancelled", lang) if ok else "⚠ دانلودی فعال نیست.", reply_markup=member_keyboard(lang) if is_member else guest_keyboard(lang))
            return

    # language selection raw (user tapped the language text lines we showed)
    if text.strip().startswith("🇮🇷") or "فارسی" in text:
        # set to fa
        if is_member:
            set_language(uid, "fa")
        await update.message.reply_text(localized_text("lang_changed", "fa"), reply_markup=member_keyboard("fa") if is_member else guest_keyboard("fa"))
        return
    if text.strip().startswith("🇬🇧") or "English".lower() in text.lower():
        if is_member:
            set_language(uid, "en")
        await update.message.reply_text(translate_text("✅ زبان با موفقیت تغییر کرد.", "en"), reply_markup=member_keyboard("en") if is_member else guest_keyboard("en"))
        return
    if text.strip().startswith("🇸🇦") or "العربية" in text:
        if is_member:
            set_language(uid, "ar")
        await update.message.reply_text(translate_text("✅ زبان با موفقیت تغییر کرد.", "ar"), reply_markup=member_keyboard("ar") if is_member else guest_keyboard("ar"))
        return

    # cancel keyboard (one_time) handling: if user presses cancel label
    cancel_label = translate_text(BUTTONS["cancel"], lang) if lang!="fa" else BUTTONS["cancel"]
    if text == cancel_label:
        STATE.pop(uid, None); PENDING.pop(uid, None)
        await update.message.reply_text("✅ لغو شد.", reply_markup=member_keyboard(lang) if is_member else guest_keyboard(lang))
        return

    # if text is url -> attempt download
    if text.startswith("http"):
        platform = detect_platform(text)
        if not is_member and platform not in ("instagram", "spotify"):
            await update.message.reply_text(localized_text("guest_block_download", lang), reply_markup=guest_keyboard(lang))
            return
        if not check_and_inc(uid, is_member):
            await update.message.reply_text(localized_text("limit_reached", lang) if "limit_reached" in BASE else "⚠️ محدودیت دانلود روزانه پر شده", reply_markup=member_keyboard(lang) if is_member else guest_keyboard(lang))
            return
        # start download (default quality 480)
        msg_reply = await update.message.reply_text(localized_text("downloading", lang))
        await start_download(uid, text, context.bot, msg_reply, prefer_quality="480")
        return

    # fallback
    await update.message.reply_text(localized_text("unknown", lang), reply_markup=member_keyboard(lang) if is_member else guest_keyboard(lang))

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    # run_polling is blocking; Railway friendly
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
