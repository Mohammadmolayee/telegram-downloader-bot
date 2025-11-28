# keyboards.py
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from translator import tr
from messages import msg

def start_guest_kb(lang):
    return ReplyKeyboardMarkup([
        [tr("📖 راهنما", lang), tr("📜 قوانین", lang)],
        [tr("ℹ درباره ما", lang), tr("🌐 زبان", lang)],
        [tr("👤 ساخت حساب", lang)],
    ], resize_keyboard=True)

def member_panel_kb(lang):
    return ReplyKeyboardMarkup([
        [tr("📥 قابلیت‌ها", lang)],
        [tr("📖 راهنما", lang), tr("📜 قوانین", lang)],
        [tr("ℹ درباره ما", lang), tr("🌐 زبان", lang)],
    ], resize_keyboard=True)

def capabilities_kb(lang):
    return ReplyKeyboardMarkup([
        [tr("🎬 یوتیوب", lang), tr("🎵 اینستاگرام", lang)],
        [tr("🎧 تیک‌تاک", lang), tr("🎼 ساندکلاد", lang)],
        [tr("🎶 اسپاتیفای", lang)],
        [tr("🔙 برگشت", lang)]
    ], resize_keyboard=True)

def back_btn(lang):
    return ReplyKeyboardMarkup([[tr("🔙 برگشت", lang)]], resize_keyboard=True)

def language_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
    ])
