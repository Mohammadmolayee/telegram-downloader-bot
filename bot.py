# bot.py (fixed for missing keys + back behavior + stable menus)
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

# ماژول‌های پروژه (مطمئن باش این فایل‌ها وجود دارند)
from database import (
    init_db, user_exists, create_user, login,
    get_user, set_language, set_theme
)
from keyboards import (
    start_keyboard, main_menu_keyboard, panel_keyboard,
    settings_keyboard, language_inline, theme_inline
)
from downloader import download_media, cancel_download
from messages import t  # t expects dict-like {"language": "fa"} and key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# وضعیت موقت برای فلوها
user_state = {}     # e.g. {user_id: "register_name" / "login_username" / ...}
pending = {}        # temporary storage for registration/login


# --- helper to get text safely (fallback to literal if missing) ---
def txt(ctx_user_lang, key, fallback=""):
    # ctx_user_lang can be dict {"language": "fa"} or string 'fa'
    if isinstance(ctx_user_lang, str):
        lang_obj = {"language": ctx_user_lang}
    else:
        lang_obj = ctx_user_lang
    try:
        return t(lang_obj, key)
    except Exception:
        return fallback or key


# ---------------------------
# send start menu (guest)
# ---------------------------
async def send_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_lang = context.user_data.get("language", "fa")
    context.user_data['last_menu'] = context.user_data.get('menu', None)
    context.user_data['menu'] = 'start'
    text = txt(user_lang, "start", "👋 سلام! به ربات خوش آمدی.\nلطفا یک گزینه انتخاب کن.")
    await update.message.reply_text(text, reply_markup=start_keyboard(user_lang))


# ---------------------------
# send main menu (intro)
# ---------------------------
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_lang = context.user_data.get("language", "fa")
    context.user_data['last_menu'] = context.user_data.get('menu', None)
    context.user_data['menu'] = 'main_menu'
    text = txt(user_lang, "main_menu", "🧰 منوی اصلی")
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_lang))


# ---------------------------
# send user panel (member)
# ---------------------------
async def send_user_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, user_row=None):
    user = user_row or get_user(update.effective_user.id)
    lang = user.get("language", "fa") if user else context.user_data.get("language", "fa")
    context.user_data['last_menu'] = context.user_data.get('menu', None)
    context.user_data['menu'] = 'panel'
    name = (user.get("name") if isinstance(user, dict) else None) or update.effective_user.first_name
    # use panel_welcome key if exists
    panel_text = txt(lang, "panel_welcome",
                     f"👤 {name}\nبه پنل کاربری خوش آمدی.\nسقف دانلود امروز: { ( '25' if user_exists(update.effective_user.id) else '15') }")
    await update.message.reply_text(panel_text, reply_markup=panel_keyboard(lang))


# ---------------------------
# /start handler
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    # if member -> send panel, else start menu
    if user_exists(uid):
        user = get_user(uid)
        await send_user_panel(update, context, user_row=user)
    else:
        # set language from context if exists
        lang = context.user_data.get("language", "fa")
        await send_start_menu(update, context)


# ---------------------------
# main message handler
# ---------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    uid = update.effective_user.id
    user = get_user(uid)
    lang = (user.get("language") if user else context.user_data.get("language", "fa")) or "fa"

    # --------- BACK handling (reply keyboard) ----------
    if text in ["🔙 بازگشت", "🔙 Back"]:
        last = context.user_data.get('last_menu')
        # if last menu exists, navigate there
        if last == 'panel' and user:
            await send_user_panel(update, context, user_row=user)
            return
        if last == 'main_menu':
            await send_main_menu(update, context)
            return
        # default: go to start
        await send_start_menu(update, context)
        return

    # --------- start menu buttons ----------
    if text in ["📖 راهنما", "📖 Help"]:
        key = "help_member" if user else "help_guest"
        await update.message.reply_text(txt(lang, key, "راهنمای استفاده"), reply_markup=None)
        return

    if text in ["📜 قوانین", "📜 Rules"]:
        await update.message.reply_text(txt(lang, "rules", "قوانین ربات"), reply_markup=None)
        return

    if text in ["ℹ درباره ما", "ℹ About"]:
        await update.message.reply_text(txt(lang, "about", "درباره ما"), reply_markup=None)
        return

    if text in ["🌐 زبان", "🌐 Language"]:
        await update.message.reply_text(txt(lang, "choose_language", "زبان را انتخاب کنید:"), reply_markup=language_inline())
        return

    if text in ["🧰 منوی اصلی", "🧰 Main Menu"]:
        await send_main_menu(update, context)
        return

    # --------- Main menu actions (register/login) ----------
    if text in ["👤 ساخت حساب", "👤 Create Account"]:
        # start registration flow
        user_state[uid] = "reg_name"
        await update.message.reply_text(txt(lang, "enter_name", "لطفاً نام کامل را ارسال کنید:"))
        return

    if user_state.get(uid) == "reg_name":
        pending[uid] = {"name": text}
        user_state[uid] = "reg_username"
        await update.message.reply_text(txt(lang, "enter_username", "حالا یوزرنیم را بفرست (بدون @):"))
        return

    if user_state.get(uid) == "reg_username":
        pending[uid]["username"] = text.lstrip("@")
        user_state[uid] = "reg_password"
        await update.message.reply_text(txt(lang, "enter_password", "حالا یک پسورد ۸-۱۲ کاراکتری بفرست:"))
        return

    if user_state.get(uid) == "reg_password":
        info = pending.get(uid, {})
        name = info.get("name") or update.effective_user.first_name
        username = info.get("username") or f"user{uid}"
        password = text
        ok = create_user(uid, name, username, password)
        # cleanup
        user_state.pop(uid, None)
        pending.pop(uid, None)
        if ok:
            await update.message.reply_text(txt(lang, "reg_done", "🎉 حساب ساخته شد! برای ورود از '🔐 ورود' استفاده کن."),
                                            reply_markup=start_keyboard(lang))
        else:
            await update.message.reply_text(txt(lang, "reg_fail", "❌ خطا یا یوزرنیم تکراری است. دوباره تلاش کن."))
        return

    # --------- login flow ----------
    if text in ["🔐 ورود", "🔐 Login"]:
        user_state[uid] = "login_username"
        await update.message.reply_text(txt(lang, "login_username", "یوزرنیم را ارسال کنید:"))
        return

    if user_state.get(uid) == "login_username":
        pending[uid] = {"username": text.lstrip("@")}
        user_state[uid] = "login_password"
        await update.message.reply_text(txt(lang, "login_password", "پسورد را ارسال کنید:"))
        return

    if user_state.get(uid) == "login_password":
        username = pending.get(uid, {}).get("username")
        password = text
        found = login(username, password)
        user_state.pop(uid, None)
        pending.pop(uid, None)
        if found:
            # login ok -> send panel
            await update.message.reply_text(txt(lang, "login_success", "✅ ورود موفق!"), reply_markup=panel_keyboard(lang))
            await send_user_panel(update, context)
        else:
            await update.message.reply_text(txt(lang, "login_fail", "❌ یوزرنیم یا پسورد اشتباه است."))
        return

    # --------- settings commands ----------
    if text in ["🎨 تنظیمات", "🎨 Settings"]:
        await update.message.reply_text(txt(lang, "settings", "تنظیمات"), reply_markup=settings_keyboard(lang))
        return

    if text in ["🌐 تغییر زبان", "🌐 Change Language"]:
        await update.message.reply_text(txt(lang, "choose_language", "زبان را انتخاب کنید"), reply_markup=language_inline())
        return

    if text in ["🎨 تغییر تم", "🎨 Theme"]:
        await update.message.reply_text(txt(lang, "choose_theme", "تم را انتخاب کنید"), reply_markup=theme_inline())
        return

    # --------- download link handling ----------
    if text.startswith("http"):
        # if user is in main_menu (intro) we disallow downloading (as requested)
        if context.user_data.get("menu") == "main_menu":
            await update.message.reply_text(txt(lang, "guest_download_block",
                                                "برای دانلود در این بخش امکان‌پذیر نیست. لطفاً به استارت یا پنل مراجعه کن."))
            return

        # schedule download in application task
        try:
            # store menu context so back works while downloading
            context.user_data['menu'] = 'downloading'
            context.user_data['last_menu'] = context.user_data.get('menu')
            # create task safely via application
            context.application.create_task(download_media(uid, text, context.bot, lang))
            await update.message.reply_text(txt(lang, "downloading", "⏳ دانلود آغاز شد..."), reply_markup=None)
        except Exception as e:
            logger.exception("create_task failed")
            await update.message.reply_text(txt(lang, "download_error", "خطا در شروع دانلود"))
        return

    # unknown input
    await update.message.reply_text(txt(lang, "unknown", "برای دانلود یک لینک ارسال کنید یا از منو استفاده کن."))


# ---------------------------
# callback handler (inline buttons)
# ---------------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    data = q.data
    uid = q.from_user.id
    user = get_user(uid)
    lang = (user.get("language") if user else context.user_data.get("language", "fa")) or "fa"

    # language change
    if data.startswith("lang_"):
        new_lang = data.split("_", 1)[1]
        if user:
            set_language(uid, new_lang)
        else:
            context.user_data["language"] = new_lang
        await q.edit_message_text(txt(new_lang, "language_changed", "✅ زبان تغییر کرد."))
        return

    # theme change
    if data.startswith("theme_"):
        theme = data.split("_", 1)[1]
        if user:
            set_theme(uid, theme)
        else:
            context.user_data["theme"] = theme
        await q.edit_message_text(txt(lang, "theme_changed", "🎨 تم تغییر کرد."))
        return

    # cancel download via inline
    if data == "cancel_download":
        cancel_download(uid)
        await q.edit_message_text(txt(lang, "cancel_download", "🚫 دانلود لغو شد."))
        return

    # fallback
    await q.edit_message_text(txt(lang, "unknown", "عملیات نامشخص."))


# ---------------------------
# MAIN (synchronous run_polling)
# ---------------------------
def main():
    init_db()
    token = os.getenv("TOKEN") or os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
    app = Application.builder().token(token).build()

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Starting bot (run_polling)...")
    app.run_polling()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    main()
