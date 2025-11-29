from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from translator import translate_text

# callback_data constants (fixed)
CB_HELP = "help"
CB_RULES = "rules"
CB_ABOUT = "about"
CB_LANG = "lang"
CB_CREATE = "create"
CB_PANEL = "panel"
CB_THEME = "theme"
CB_BACK = "back"
CB_CANCEL = "cancel"

def make_start_inline(lang="fa"):
    # texts in Farsi -> will be translated per lang
    labels = [
        ("📖 راهنما", CB_HELP),
        ("📜 قوانین", CB_RULES),
        ("ℹ درباره ما", CB_ABOUT),
        ("🌐 زبان", CB_LANG),
        ("👤 ساخت حساب", CB_CREATE)
    ]
    return _inline_from_labels(labels, lang)

def make_panel_inline(lang="fa"):
    labels = [
        ("📖 راهنما", CB_HELP),
        ("📜 قوانین", CB_RULES),
        ("ℹ درباره ما", CB_ABOUT),
        ("🌐 زبان", CB_LANG),
        ("🔙 بازگشت", CB_BACK)
    ]
    return _inline_from_labels(labels, lang)

def make_language_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
         InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
    ])

def make_cancel_inline(user_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✖️ لغو دانلود", callback_data=f"cancel_{user_id}")]])

# helper
def _inline_from_labels(labels, lang):
    # returns InlineKeyboardMarkup in two-column layout
    rows = []
    cur = []
    for text, cb in labels:
        lab = translate_text(text, lang) if lang != "fa" else text
        cur.append(InlineKeyboardButton(lab, callback_data=cb))
        if len(cur) == 2:
            rows.append(cur); cur = []
    if cur:
        rows.append(cur)
    return InlineKeyboardMarkup(rows)
