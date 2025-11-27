# keyboards.py
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def start_reply_keyboard(lang='fa'):
    # Reply keyboard for /start (guest)
    keys = [
        ["📖 راهنما", "🧰 منوی اصلی"],
        ["📜 قوانین", "ℐ درباره ما"],
        ["🌐 زبان"]
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)

def guest_main_reply():
    keys = [
        ["🔐 ساخت حساب", "🤖 ورود خودکار"],
        ["📘 راهنمای منوی اصلی", "⚙️ تنظیمات"],
        ["ℹ️ درباره ما", "🔙 بازگشت"]
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)

def user_panel_reply():
    keys = [
        ["📥 دانلودهای اخیر", "📊 وضعیت حساب"],
        ["📘 راهنمای پنل کاربری", "📜 قوانین"],
        ["ℹ️ درباره ما", "⚙️ تنظیمات"],
        ["🔙 بازگشت"]
    ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)

def inline_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]])

def language_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
         InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
         InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
    ])

def cancel_inline():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⛔️ لغو", callback_data="cancel")]])
