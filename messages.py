# messages.py
# متن‌های فارسی برای ربات؛ get_text(key, lang) می‌تواند ترجمه کند
from translator import translate

BASE = {
    "welcome_title": "👋 سلام! به {bot_name} خوش اومدی!",
    "welcome_sub": "📚 برای راهنما روی «راهنما» بزن.\n📂 برای امکانات، «منوی اصلی» را انتخاب کن.\n🌐 برای تغییر زبان، «زبان» را انتخاب کن.",
    "btn_help": "📚 راهنما",
    "btn_main_menu": "📂 منوی اصلی",
    "btn_set_lang": "🌐 تغییر زبان",
    "main_menu_text": "📂 **منوی اصلی**\nلطفاً یک گزینه انتخاب کن:",
    "btn_create_account": "⭐ ساخت حساب",
    "btn_back": "⬅️ بازگشت",
    "help_full": (
        "📚 راهنمای ربات دانلودر حرفه‌ای\n\n"
        "👤 ساخت حساب:\n"
        "نام و نام خانوادگی → یوزرنیم → پسورد (۸-۱۲ کرکتر).\n\n"
        "🔐 ورود: این ربات از autologin استفاده می‌کند — اگر قبلاً حساب ساختی کافیست /start بزنی و مستقیماً وارد پنل می‌شوی.\n\n"
        "🧑‍💻 مهمان:\n"
        "• روزی ۱۵ دانلود\n"
        "• دانلود ویدیو از اینستاگرام\n"
        "• دانلود صوت از Spotify\n\n"
        "⭐ عضو:\n"
        "• روزی ۲۵ دانلود\n"
        "• دانلود ویدیو 720p از YouTube, TikTok, Instagram\n"
        "• دانلود صوت از SoundCloud و Spotify\n\n"
        "برای بازگشت دکمه‌ی «بازگشت» را بزنید."
    ),
    "create_prompt_name": "📝 لطفاً نام و نام خانوادگی خود را ارسال کنید:",
    "create_prompt_username": "🧑‍💻 لطفاً یوزرنیم (بدون @) را وارد کنید:",
    "create_prompt_password": "🔒 لطفاً پسورد (۸ تا ۱۲ کاراکتر) را وارد کنید:",
    "create_success": "🎉 حساب با موفقیت ساخته شد!\nاکنون /start را بزن تا وارد پنل شوی.",
    "create_fail": "❌ ثبت نام ناموفق — یوزرنیم ممکن است تکراری باشد.",
    "login_success": "🎊 ورود موفق — به پنل خوش آمدی.",
    "login_fail": "❌ ورود ناموفق.",
    "panel_welcome": "⭐ پنل کاربری\n👤 {display_name}\n📊 دانلود امروز: {count}/{limit}\n\nگزینه‌ای انتخاب کن:",
    "btn_profile": "👤 پروفایل من",
    "btn_recent": "📥 دانلودهای اخیر",
    "btn_stats": "📊 آمار دانلود",
    "btn_queue_status": "🗂 وضعیت صف",
    "btn_cancel_download": "🚫 لغو دانلود",
    "added_queue": "✅ لینک شما به صف اضافه شد. (برای لغو، دکمه لغو را بزن)",
    "cancelled": "🚫 دانلود لغو شد.",
    "invalid_link": "❌ لینک معتبر نیست. لطفاً لینک کامل بفرست.",
    "guest_must_register": "🔐 این لینک فقط برای کاربران عضو است. لطفاً حساب بسازید.",
    "guest_limit": "⚠️ شما مهمان هستید؛ روزی {} دانلود مجاز است.",
    "registered_limit": "⚠️ سقف دانلود روزانه شما ({}) تکمیل شده.",
    "cancel_info": "برای لغو دانلود، روی دکمه «🚫 لغو دانلود» که بعد از ارسال لینک می‌آید بزنید."
}

def get_text(key: str, lang: str = "fa", **kwargs) -> str:
    text = BASE.get(key, "")
    if kwargs:
        text = text.format(**kwargs)
    # translate if needed (translator may return same text if not available)
    try:
        return translate(text, lang)
    except Exception:
        return text
