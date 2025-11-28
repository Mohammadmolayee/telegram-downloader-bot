# keyboards.py
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def start_reply(lang="fa"):
    if lang == "en":
        rows = [
            ["📖 Help", "📜 Rules"],
            ["ℹ About", "⭐ Features"],
            ["🌐 Language", "👤 Create Account"],
            ["🔙 Back"]
        ]
    elif lang == "ar":
        rows = [
            ["📖 تعليمات", "📜 القوانين"],
            ["ℹ حول", "⭐ الميزات"],
            ["🌐 اللغة", "👤 انشاء حساب"],
            ["🔙 رجوع"]
        ]
    else:
        rows = [
            ["📖 راهنما", "📜 قوانین"],
            ["ℹ درباره ما", "⭐ قابلیت‌ها"],
            ["🌐 زبان", "👤 ساخت حساب"],
            ["🔙 بازگشت"]
        ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def panel_reply(lang="fa"):
    if lang == "en":
        rows = [
            ["📥 Download", "⭐ Features"],
            ["📖 Panel Help", "📜 Rules"],
            ["ℹ About", "🌐 Language"],
            ["🎨 Settings", "🔙 Back"]
        ]
    elif lang == "ar":
        rows = [
            ["📥 تحميل", "⭐ الميزات"],
            ["📖 مساعدة اللوحة", "📜 القوانين"],
            ["ℹ حول", "🌐 اللغة"],
            ["🎨 الاعدادات", "🔙 رجوع"]
        ]
    else:
        rows = [
            ["📥 دانلود", "⭐ قابلیت‌ها"],
            ["📖 راهنمای پنل", "📜 قوانین"],
            ["ℹ درباره ما", "🌐 زبان"],
            ["🎨 تنظیمات", "🔙 بازگشت"]
        ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def settings_reply(lang="fa"):
    if lang == "en":
        rows = [["🌐 Change Language", "🎨 Theme"], ["🔙 Back"]]
    elif lang == "ar":
        rows = [["🌐 تغيير اللغة", "🎨 النمط"], ["🔙 رجوع"]]
    else:
        rows = [["🌐 تغییر زبان", "🎨 تغییر تم"], ["🔙 بازگشت"]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def back_only(lang="fa"):
    if lang == "en":
        rows = [["🔙 Back"]]
    elif lang == "ar":
        rows = [["🔙 رجوع"]]
    else:
        rows = [["🔙 بازگشت"]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)

def language_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
         InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
    ])

def theme_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌙 Dark", callback_data="theme_dark"),
         InlineKeyboardButton("☀️ Light", callback_data="theme_light")]
    ])

def cancel_inline(lang="fa"):
    text = "لغو دانلود" if lang == "fa" else ("Cancel" if lang == "en" else "إلغاء")
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="cancel_download")]])
