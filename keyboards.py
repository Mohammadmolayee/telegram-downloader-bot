# keyboards.py
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# reply keyboards (always visible at bottom) — includes the universal "🔙 بازگشت"
def start_reply(lang="fa"):
    if lang == "en":
        return ReplyKeyboardMarkup([
            ["📥 Download (Guest)", "📖 Help"],
            ["📜 Rules", "ℹ About"],
            ["🌐 Language", "👤 Create Account"],
            ["🔙 Back"]
        ], resize_keyboard=True)
    # default Persian
    return ReplyKeyboardMarkup([
        ["📥 دانلود (مهمان)", "📖 راهنما"],
        ["📜 قوانین", "ℹ درباره ما"],
        ["🌐 زبان", "👤 ساخت حساب"],
        ["🔙 بازگشت"]
    ], resize_keyboard=True)


def panel_reply(lang="fa"):
    if lang == "en":
        return ReplyKeyboardMarkup([
            ["📥 Download", "📖 Panel Help"],
            ["📜 Rules", "ℹ About"],
            ["🎨 Settings", "🔙 Back"]
        ], resize_keyboard=True)
    return ReplyKeyboardMarkup([
        ["📥 دانلود", "📖 راهنمای پنل"],
        ["📜 قوانین", "ℹ درباره ما"],
        ["🎨 تنظیمات", "🔙 بازگشت"]
    ], resize_keyboard=True)


def settings_reply(lang="fa"):
    if lang == "en":
        return ReplyKeyboardMarkup([
            ["🌐 Change Language", "🎨 Theme"],
            ["🔙 Back"]
        ], resize_keyboard=True)
    return ReplyKeyboardMarkup([
        ["🌐 تغییر زبان", "🎨 تغییر تم"],
        ["🔙 بازگشت"]
    ], resize_keyboard=True)


# Inline keyboards (small popups) for language/theme selection
def language_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
         InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
    ])


def theme_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌙 دارک (Dark)", callback_data="theme_dark"),
         InlineKeyboardButton("☀️ لایت (Light)", callback_data="theme_light")]
    ])


# small inline for cancel actions
def cancel_inline(lang="fa"):
    if lang == "en":
        return InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_download")]])
    return InlineKeyboardMarkup([[InlineKeyboardButton("لغو دانلود", callback_data="cancel_download")]])
