# keyboards.py
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import translator as tr

def start_reply(lang="fa"):
    rows = [
        [tr.btn(lang, "BTN_HELP"), tr.btn(lang, "BTN_RULES")],
        [tr.btn(lang, "BTN_ABOUT"), tr.btn(lang, "BTN_FEATURES")],
        [tr.btn(lang, "BTN_LANGUAGE"), tr.btn(lang, "BTN_CREATE")],
        [tr.btn(lang, "BTN_BACK")]
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def panel_reply(lang="fa"):
    rows = [
        [tr.btn(lang, "BTN_DOWNLOAD"), tr.btn(lang, "BTN_FEATURES")],
        [tr.btn(lang, "BTN_PANEL_HELP"), tr.btn(lang, "BTN_RULES")],
        [tr.btn(lang, "BTN_ABOUT"), tr.btn(lang, "BTN_LANGUAGE")],
        [tr.btn(lang, "BTN_SETTINGS"), tr.btn(lang, "BTN_BACK")]
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def settings_reply(lang="fa"):
    rows = [[tr.btn(lang, "BTN_LANGUAGE"), tr.btn(lang, "BTN_SETTINGS")], [tr.btn(lang, "BTN_BACK")]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def back_only(lang="fa"):
    return ReplyKeyboardMarkup([[tr.btn(lang, "BTN_BACK")]], resize_keyboard=True, one_time_keyboard=True)

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
    return InlineKeyboardMarkup([[InlineKeyboardButton(tr.btn(lang, "BTN_CANCEL"), callback_data="cancel_download")]])
