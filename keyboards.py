from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def guest_keyboard(lang):
    return ReplyKeyboardMarkup([
        ["📖 راهنما" if lang=="fa" else "📖 Help",
         "🌐 زبان" if lang=="fa" else "🌐 Language"],
        ["👤 ساخت حساب" if lang=="fa" else "👤 Create Account"]
    ], resize_keyboard=True)

def member_keyboard(lang):
    return ReplyKeyboardMarkup([
        ["📥 دانلود"],
        ["📖 راهنما" if lang=="fa" else "📖 Help",
         "🌐 زبان" if lang=="fa" else "🌐 Language"],
        ["🔙 بازگشت" if lang=="fa" else "🔙 Back"]
    ], resize_keyboard=True)

def language_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
    ])
