from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


# -----------------------------
# کیبورد پنل مهمان (Start Menu)
# -----------------------------
def start_keyboard(lang="fa"):
    if lang == "fa":
        buttons = [
            ["📖 راهنما", "📜 قوانین"],
            ["ℹ درباره ما", "🌐 زبان"],
            ["👤 ساخت حساب"]
        ]
    elif lang == "en":
        buttons = [
            ["📖 Help", "📜 Rules"],
            ["ℹ About", "🌐 Language"],
            ["👤 Create Account"]
        ]
    elif lang == "ar":
        buttons = [
            ["📖 تعليمات", "📜 القوانين"],
            ["ℹ معلومات عنا", "🌐 اللغة"],
            ["👤 إنشاء حساب"]
        ]
    else:
        buttons = [["Error"]]

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


# -----------------------------
# کیبورد پنل کاربری (Member Panel)
# -----------------------------
def panel_keyboard(lang="fa"):
    if lang == "fa":
        buttons = [
            ["📖 راهنما", "📜 قوانین"],
            ["ℹ درباره ما"],
            ["🌐 زبان"],
            ["🔙 بازگشت"]
        ]
    elif lang == "en":
        buttons = [
            ["📖 Help", "📜 Rules"],
            ["ℹ About"],
            ["🌐 Language"],
            ["🔙 Back"]
        ]
    elif lang == "ar":
        buttons = [
            ["📖 تعليمات", "📜 القوانين"],
            ["ℹ معلومات عنا"],
            ["🌐 اللغة"],
            ["🔙 رجوع"]
        ]
    else:
        buttons = [["Error"]]

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


# -----------------------------
# کیبورد تغییر زبان (Inline)
# -----------------------------
def language_inline():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")
        ]
    ])
