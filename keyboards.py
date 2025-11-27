# keyboards.py
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def start_keyboard(lang):
    return ReplyKeyboardMarkup([
        ["📖 راهنما" if lang == "fa" else "📖 Help",
         "📜 قوانین" if lang == "fa" else "📜 Rules"],
        ["ℹ درباره ما" if lang == "fa" else "ℹ About"],
        ["🧰 منوی اصلی" if lang == "fa" else "🧰 Main Menu"],
        ["🌐 زبان" if lang == "fa" else "🌐 Language"],
    ], resize_keyboard=True)


def main_menu_keyboard(lang):
    return ReplyKeyboardMarkup([
        ["👤 ساخت حساب" if lang == "fa" else "👤 Create Account"],
        ["🔐 ورود" if lang == "fa" else "🔐 Login"],
        ["🔙 بازگشت" if lang == "fa" else "🔙 Back"]
    ], resize_keyboard=True)


def panel_keyboard(lang):
    return ReplyKeyboardMarkup([
        ["📥 دانلود جدید" if lang == "fa" else "📥 New Download"],
        ["📂 دانلودهای اخیر" if lang == "fa" else "📂 Recent"],
        ["🎨 تنظیمات" if lang == "fa" else "🎨 Settings"],
        ["ℹ درباره ما" if lang == "fa" else "ℹ About"],
        ["🔙 بازگشت" if lang == "fa" else "🔙 Back"]
    ], resize_keyboard=True)


def settings_keyboard(lang):
    return ReplyKeyboardMarkup([
        ["🌐 تغییر زبان" if lang == "fa" else "🌐 Change Language"],
        ["🎨 تغییر تم" if lang == "fa" else "🎨 Theme"],
        ["🔙 بازگشت" if lang == "fa" else "🔙 Back"],
    ], resize_keyboard=True)


def language_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
    ])


def theme_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌙 دارک", callback_data="theme_dark")],
        [InlineKeyboardButton("☀️ لایت", callback_data="theme_light")],
    ])
