# translator.py
import json
import os

DB_FILE = "translate_db.json"

# کلیدها و متن فارسی پایه (فقط فارسی را اینجا می‌نویسیم)
BASE = {
    # دکمه‌ها (KEYS)
    "BTN_HELP": "📖 راهنما",
    "BTN_RULES": "📜 قوانین",
    "BTN_ABOUT": "ℹ درباره ما",
    "BTN_FEATURES": "⭐ قابلیت‌ها",
    "BTN_LANGUAGE": "🌐 زبان",
    "BTN_CREATE": "👤 ساخت حساب",
    "BTN_BACK": "🔙 بازگشت",
    "BTN_DOWNLOAD": "📥 دانلود",
    "BTN_SETTINGS": "🎨 تنظیمات",
    "BTN_PANEL_HELP": "📖 راهنمای پنل",
    "BTN_CANCEL": "لغو دانلود",
    # متون
    "start_guest": "👋 سلام! به ربات دانلودر حرفه‌ای خوش اومدی!\n\n📥 قابلیت‌های حالت مهمان:\n• دانلود از اینستاگرام\n• دانلود از اسپاتیفای\n\n⚠️ برای دانلود از یوتیوب، تیک‌تاک و ساندکلاد باید حساب بسازی.\n\n💡 فقط لینک رو بفرست — دانلود خودکار شروع میشه.",
    "help_guest": "📖 راهنمای حالت مهمان:\n\n1️⃣ فقط از اینستاگرام و اسپاتیفای می‌تونی دانلود کنی.\n2️⃣ برای فعال شدن یوتیوب و تیک‌تاک باید حساب بسازی.\n3️⃣ لینک رو بفرست → بلافاصله دانلود شروع میشه.",
    "help_member": "📖 راهنمای پنل:\n\nشما می‌تونید از همه پلتفرم‌ها دانلود کنید، تم/زبان تغییر بدید، سابقه دانلود ببینید و پشتیبانی بگیرید.",
    "rules": "📜 قوانین:\n1- استفاده شخصی. 2- لینک‌های غیرقانونی مجاز نیست.",
    "about": "ℹ این ربات توسط @Mohammad778889 ساخته شده. نام ربات: دانلودر حرفه‌ای (@professional_dawnloder_bot).",
    "features_text": "⭐ قابلیت‌ها:\n- دانلود ویدیو/صدا از Instagram, YouTube, TikTok, SoundCloud, Spotify\n- برای مهمان: فقط Instagram و Spotify فعال است.\n\nنمونه لینک‌ها:\n• اینستاگرام: https://www.instagram.com/p/XXXXXXXXX\n• یوتیوب: https://youtu.be/XXXXXXXXX\n• تیک‌تاک: https://www.tiktok.com/@user/video/XXXXXXXXX",
    "reg_name": "👤 لطفاً نام و نام خانوادگی رو وارد کن:",
    "reg_username": "🔖 حالا یک نام کاربری انتخاب کن (بدون @):",
    "reg_password": "🔒 یک رمز عبور امن وارد کن:",
    "reg_done": "✅ حساب با موفقیت ساخته شد! شما هم‌اکنون وارد پنل شدید.",
    "reg_fail": "❌ ساخت حساب ناموفق بود. یوزرنیم تکراری یا خطا.",
    "send_link": "📎 لینک رو بفرست تا دانلود آغاز بشه.",
    "guest_block_download": "⚠️ برای دانلود از این پلتفرم باید حساب بسازی.",
    "downloading": "⏳ در حال دانلود...",
    "download_finished": "✅ دانلود کامل شد!",
    "download_error": "❌ خطا در دانلود!",
    "cancel_download": "🚫 دانلود لغو شد.",
    "download_by": "دانلود شده توسط: دانلودر حرفه‌ای ({bot_username})",
    "download_details_line": "📄 عنوان: {title}\n🔗 منبع: {url}\n{by_line}",
    "choose_language": "🌐 زبان مورد نظر را انتخاب کنید:",
    "lang_changed": "✅ زبان با موفقیت تغییر کرد.",
    "choose_theme": "🎨 تم را انتخاب کنید:",
    "theme_changed": "✅ تم با موفقیت تغییر کرد.",
    "settings": "⚙ تنظیمات ربات:",
    "unknown": "🤔 دستور ناشناخته. از دکمه‌ها استفاده کن.",
    "panel_welcome": "🎉 خوش اومدی به پنل کاربری!\n\n🧑‍💼 کاربر: {user_name}\n🆔 یوزرنیم: @{username}\n🎨 تم فعلی: {theme}\n🌐 زبان فعلی: {language}\n\n📥 قابلیت‌های فعال: Instagram, YouTube, TikTok, SoundCloud, Spotify\nبرای دانلود فقط لینک رو ارسال کن."
}

# simple translation dictionaries (برای جابجایی لغات مهم)
EN_DICT = {
    "سلام": "Hello", "خوش اومدی": "Welcome", "قابلیت‌ها": "Features", "دانلود": "Download",
    "در حال دانلود": "Downloading...", "دانلود کامل شد": "Download finished",
    "ساخت حساب": "Create account", "پنل کاربری": "User panel", "لغو دانلود": "Cancel download",
    "برای دانلود فقط لینک رو ارسال کن.": "Send a link to start downloading."
}
AR_DICT = {
    "سلام": "مرحبا", "خوش اومدی": "اهلا بك", "قابلیت‌ها": "الميزات", "دانلود": "تحميل",
    "در حال دانلود": "جاري التحميل...", "دانلود کامل شد": "اكتمل التحميل",
    "ساخت حساب": "إنشاء حساب", "پنل کاربری": "لوحة المستخدم", "لغو دانلود": "إلغاء التنزيل",
    "برای دانلود فقط لینک رو ارسال کن.": "أرسل الرابط لبدء التحميل."
}

# DB load/save
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

def _load():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(d):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def _auto_en(text: str):
    out = text
    for fa, en in EN_DICT.items():
        out = out.replace(fa, en)
    return out

def _auto_ar(text: str):
    out = text
    for fa, ar in AR_DICT.items():
        out = out.replace(fa, ar)
    return out

# API: t(lang, key, **fmt) -> returns translated (and formatted) string
def t(lang: str, key: str, **fmt):
    """
    lang: 'fa' | 'en' | 'ar'
    key: key from BASE
    """
    if key not in BASE:
        return key
    text_fa = BASE[key]
    cache = _load()
    if text_fa in cache and lang in cache[text_fa]:
        out = cache[text_fa][lang]
    else:
        if lang == "fa":
            out = text_fa
        elif lang == "en":
            out = _auto_en(text_fa)
        else:
            out = _auto_ar(text_fa)
        # save
        cache[text_fa] = {"fa": text_fa, "en": _auto_en(text_fa), "ar": _auto_ar(text_fa)}
        _save(cache)
    try:
        return out.format(**fmt) if fmt else out
    except Exception:
        return out

# API for buttons: return label string for a KEY in a lang
def btn(lang: str, key: str):
    return t(lang, key)
