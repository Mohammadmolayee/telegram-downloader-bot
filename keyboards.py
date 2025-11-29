from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def start_keyboard(lang="fa"):
    if lang=="fa":
        kb = [
            ["📖 راهنما", "📜 قوانین"],
            ["ℹ درباره ما", "🌐 زبان"],
            ["👤 ساخت حساب"]
        ]
    elif lang=="en":
        kb = [["📖 Help","📜 Rules"],["ℹ About","🌐 Language"],["👤 Create Account"]]
    else:
        kb = [["📖 تعليمات","📜 القوانين"],["ℹ معلومات عنا","🌐 اللغة"],["👤 إنشاء حساب"]]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def panel_keyboard(lang="fa"):
    if lang=="fa":
        kb = [["📖 راهنما","📜 قوانین"],["ℹ درباره ما","🌐 زبان"],["🔙 بازگشت"]]
    elif lang=="en":
        kb = [["📖 Help","📜 Rules"],["ℹ About","🌐 Language"],["🔙 Back"]]
    else:
        kb = [["📖 تعليمات","📜 القوانين"],["ℹ About","🌐 اللغة"],["🔙 رجوع"]]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def language_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
         InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
    ])

def cancel_inline(user_id):
    # unique callback to cancel
    return InlineKeyboardMarkup([[InlineKeyboardButton("✖️ لغو دانلود", callback_data=f"cancel_{user_id}")]])
