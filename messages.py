# messages.py
from translator import tr

MESSAGES = {
    # شروع / مهمان
    "start_guest": (
        "👋 سلام! به ربات دانلودر حرفه‌ای خوش اومدی!\n\n"
        "📥 قابلیت‌های حالت مهمان:\n"
        "• دانلود از اینستاگرام\n"
        "• دانلود از اسپاتیفای\n\n"
        "⚠️ برای دانلود از یوتیوب، تیک‌تاک و ساندکلاد باید حساب بسازی.\n\n"
        "💡 فقط لینک رو بفرست — دانلود خودکار شروع میشه."
    ),
    "help_guest": (
        "📖 راهنمای حالت مهمان:\n\n"
        "1️⃣ فقط از اینستاگرام و اسپاتیفای می‌تونی دانلود کنی.\n"
        "2️⃣ برای فعال شدن یوتیوب و تیک‌تاک باید حساب بسازی.\n"
        "3️⃣ لینک رو بفرست → بلافاصله دانلود شروع میشه."
    ),
    "help_member": (
        "📖 راهنمای پنل:\n\n"
        "شما می‌تونید از همه پلتفرم‌ها دانلود کنید، تم/زبان تغییر بدید، سابقه دانلود ببینید و پشتیبانی بگیرید."
    ),
    "rules": "📜 قوانین:\n1- استفاده شخصی. 2- لینک‌های غیرقانونی مجاز نیست.",
    "about": "ℹ این ربات توسط @Mohammad778889 ساخته شده. نام ربات: دانلودر حرفه‌ای (@professional_dawnloder_bot).",
    "features_text": (
        "⭐ قابلیت‌ها:\n"
        "- دانلود ویدیو/صدا از Instagram, YouTube, TikTok, SoundCloud, Spotify\n"
        "- برای مهمان: فقط Instagram و Spotify فعال است.\n\n"
        "نمونه لینک‌ها:\n"
        "• اینستاگرام: https://www.instagram.com/p/XXXXXXXXX\n"
        "• یوتیوب: https://youtu.be/XXXXXXXXX\n"
        "• تیک‌تاک: https://www.tiktok.com/@user/video/XXXXXXXXX\n"
    ),
    # ثبت نام
    "reg_name": "👤 لطفاً نام و نام خانوادگی رو وارد کن:",
    "reg_username": "🔖 حالا یک نام کاربری انتخاب کن (بدون @):",
    "reg_password": "🔒 یک رمز عبور امن وارد کن:",
    "reg_done": "✅ حساب با موفقیت ساخته شد! برای ورود به پنل /start بزن (Auto-login فعال شد).",
    "reg_fail": "❌ ساخت حساب ناموفق بود. یوزرنیم تکراری یا خطا.",
    # دانلود
    "send_link": "📎 لینک رو بفرست تا دانلود آغاز بشه.",
    "guest_block_download": "⚠️ برای دانلود از این پلتفرم باید حساب بسازی.",
    "downloading": "⏳ در حال دانلود...",
    "download_finished": "✅ دانلود کامل شد!",
    "download_error": "❌ خطا در دانلود!",
    "cancel_download": "🚫 دانلود لغو شد.",
    "download_by": "دانلود شده توسط: دانلودر حرفه‌ای ({bot_username})",
    "download_details_line": "📄 عنوان: {title}\n🔗 منبع: {url}\n{by_line}",
    # تنظیمات
    "choose_language": "🌐 زبان مورد نظر را انتخاب کنید:",
    "lang_changed": "✅ زبان با موفقیت تغییر کرد.",
    "choose_theme": "🎨 تم را انتخاب کنید:",
    "theme_changed": "✅ تم با موفقیت تغییر کرد.",
    "settings": "⚙ تنظیمات ربات:",
    "unknown": "🤔 دستور ناشناخته. از دکمه‌ها استفاده کن.",
    "panel_welcome": (
        "🎉 خوش اومدی به پنل کاربری!\n\n"
        "🧑‍💼 کاربر: {user_name}\n"
        "🆔 یوزرنیم: @{username}\n"
        "🎨 تم فعلی: {theme}\n"
        "🌐 زبان فعلی: {language}\n\n"
        "📥 قابلیت‌های فعال: Instagram, YouTube, TikTok, SoundCloud, Spotify\n"
        "برای دانلود فقط لینک رو ارسال کن."
    )
}

def t(user_like, key, **fmt):
    """
    user_like: dict مثل {'language': 'fa'} یا رشته زبان 'fa'
    key: کلید متن
    fmt: پارامترهای فرمت مثل title, url, bot_username
    """
    lang = "fa"
    if isinstance(user_like, dict):
        lang = user_like.get("language", "fa")
    elif isinstance(user_like, str):
        lang = user_like
    text_fa = MESSAGES.get(key, "")
    try:
        formatted = text_fa.format(**fmt) if fmt else text_fa
    except Exception:
        formatted = text_fa
    return tr(lang, formatted)
