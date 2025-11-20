# bot.py
# فایل اصلی ربات

import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from messages import get_message
from db import (
    init_db,
    create_user,
    check_login,
    get_user_language,
    set_language,
    count_downloads_today
)
from config import GUEST_LIMIT, USER_LIMIT
from utils import detect_platform
from downloader import add_to_queue, cancel_download, download_worker

# مقداردهی دیتابیس
init_db()

# ---------------------
# دکمه‌های اولیه
# ---------------------

def keyboard_start(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 راهنما", callback_data="help")],
        [InlineKeyboardButton("📂 منوی اصلی", callback_data="menu")],
        [InlineKeyboardButton("🌐 تغییر زبان", callback_data="lang")]
    ])


def keyboard_main_menu(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ ساخت حساب", callback_data="register")],
        [InlineKeyboardButton("🔐 ورود", callback_data="login")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="back_home")],
    ])


def keyboard_languages():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="start")]
    ])


# ---------------------
# start
# ---------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = get_user_language(user_id)
    await update.message.reply_text(
        get_message("welcome", lang),
        reply_markup=keyboard_start(lang)
    )

# ---------------------
# CALLBACKS
# ---------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lang = get_user_language(user_id)
    data = query.data

    if data == "help":
        await query.message.edit_text(get_message("help", lang),
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data="start")]]))

    elif data == "menu":
        await query.message.edit_text(get_message("main_menu", lang),
                                      reply_markup=keyboard_main_menu(lang))

    elif data == "back_home" or data == "start":
        await query.message.edit_text(get_message("welcome", lang),
                                      reply_markup=keyboard_start(lang))

    elif data == "lang":
        await query.message.edit_text("🌐 زبان خود را انتخاب کنید:",
                                      reply_markup=keyboard_languages())

    elif data in ["lang_fa", "lang_en", "lang_ar"]:
        lang_code = data.split("_")[1]
        set_language(user_id, lang_code)
        await query.message.edit_text("✅ زبان تغییر کرد",
                                      reply_markup=keyboard_start(lang_code))

    elif data == "register":
        context.user_data["step"] = "fullname"
        await query.message.edit_text(get_message("create_account_intro", lang))

    elif data == "login":
        context.user_data["step"] = "login_user"
        await query.message.edit_text(get_message("login_username", lang))


# ---------------------
# مدیریت پیام‌ها
# ---------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = get_user_language(user_id)
    text = update.message.text

    # مراحل ثبت‌نام
    if context.user_data.get("step") == "fullname":
        context.user_data["fullname"] = text
        context.user_data["step"] = "username"
        return await update.message.reply_text(get_message("enter_username", lang))

    if context.user_data.get("step") == "username":
        context.user_data["username"] = text
        context.user_data["step"] = "password"
        return await update.message.reply_text(get_message("enter_password", lang))

    if context.user_data.get("step") == "password":
        ok = create_user(user_id, context.user_data["fullname"],
                         context.user_data["username"], text)
        if ok:
            context.user_data.clear()
            return await update.message.reply_text(get_message("account_created", lang),
                                                   reply_markup=keyboard_main_menu(lang))
        else:
            return await update.message.reply_text("❌ یوزرنیم تکراری است.")

    # مراحل ورود
    if context.user_data.get("step") == "login_user":
        context.user_data["login_username"] = text
        context.user_data["step"] = "login_pass"
        return await update.message.reply_text(get_message("login_password", lang))

    if context.user_data.get("step") == "login_pass":
        user = check_login(context.user_data["login_username"], text)
        if user:
            context.user_data.clear()
            return await update.message.reply_text(get_message("login_success", lang))
        else:
            return await update.message.reply_text(get_message("login_failed", lang))

    # لینک دانلود
    platform = detect_platform(text)

    if not platform:
        return await update.message.reply_text(get_message("invalid_link", lang))

    # محدودیت کاربران
    downloads_today = count_downloads_today(user_id)

    if user_id > 50_000_000:  # کاربر مهمان
        if downloads_today >= GUEST_LIMIT:
            return await update.message.reply_text(get_message("guest_limit", lang))
        if platform in ["video"]:
            return await update.message.reply_text(get_message("register_required", lang))

    else:  # کاربر عضو
        if downloads_today >= USER_LIMIT:
            return await update.message.reply_text("❌ سقف دانلود روزانه به پایان رسیده.")

    # اضافه به صف
    add_to_queue(user_id, update.message.chat_id, text)
    await update.message.reply_text(get_message("download_started", lang),
                                    reply_markup=InlineKeyboardMarkup([
                                        [InlineKeyboardButton("🚫 لغو دانلود", callback_data=f"cancel_{user_id}")]
                                    ]))


# ---------------------
# لغو دانلود
# ---------------------
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data.startswith("cancel_"):
        user_id = int(data.split("_")[1])
        cancel_download(user_id)
        await update.callback_query.message.edit_text("🚫 دانلود لغو شد.")


# ---------------------
# MAIN
# ---------------------
async def main():
    app = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

    asyncio.create_task(download_worker(app.bot))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(CallbackQueryHandler(cancel_handler, pattern="cancel_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
