# messages.py
# پیام‌ها به 3 زبان (fa / en / ar). keyها یکسانند تا راحت انتخاب شود.
MESS = {
    'fa': {
        'start': (
            "👋 سلام! به ربات «دانلودر حرفه‌ای» خوش اومدی!\n\n"
            "📥 این ربات می‌تونه از این پلتفرم‌ها دانلود کنه:\n"
            "• Instagram (ویدیو / عکس / ریلز)\n"
            "• Spotify (موزیک)\n\n"
            "⚠️ در حالت مهمان فقط این دو فعال هستند.\n\n"
            "🎬 برای فعال‌سازی YouTube و TikTok و SoundCloud باید حساب بسازی.\n\n"
            "💡 فقط لینک بفرست — دانلود خودکار شروع می‌شه."
        ),
        'help_start': "📖 راهنمای استفاده از ربات\n\n🔹 فقط لینک را ارسال کنید — دانلود خودکار شروع می‌شود.\n🔹 نیازی به دستور یا تنظیم خاصی نیست.",
        'main_menu': "🧰 منوی اصلی\n\nدر این بخش می‌تونی حساب کاربری بسازی یا وارد بشی.\n\n⭐ مزایای ساخت حساب:\n• فعال شدن YouTube / TikTok / SoundCloud\n• افزایش دانلود روزانه از ۱۵ به ۲۵\n• داشتن پنل کاربری اختصاصی",
        'help_main_instructions': (
            "📘 راهنمای ساخت حساب\n\n"
            "1) روی 'ساخت حساب' بزنید.\n"
            "2) نام کامل خود را وارد کنید.\n"
            "3) یوزرنیم (بدون @) وارد کنید.\n"
            "سپس وارد پنل کاربری خود شوید (ورود خودکار)."
        ),
        'help_panel': "📘 راهنمای پنل کاربری\n\n📥 دانلودهای اخیر: پنج دانلود آخر با جزئیات\n📊 وضعیت حساب: تعداد دانلودهای امروز و وضعیت پلتفرم‌ها\n⚙️ تنظیمات: تغییر زبان و تم\n",
        'guest_restriction': "❗ شما در حالت مهمان هستید.\nدر حالت مهمان روزانه ۱۵ دانلود دارید و فقط از Instagram و Spotify پشتیبانی می‌شود.\n\nبرای فعال شدن YouTube/TikTok/SoundCloud لطفا حساب بسازید.",
        'panel_welcome': "👤 {name} عزیز، خوش آمدی به پنل اختصاصی!\n\n⭐ وضعیت حساب: فعال\n🎯 سقف دانلود امروز: {limit}\n📡 پلتفرم‌های فعال:\nYouTube • TikTok • Instagram • Spotify • SoundCloud\n\n💡 فقط لینک بفرست — دانلود خودکار انجام می‌شود.",
        'about': "ℹ️ درباره ما\n\n🤖 ربات: دانلودر حرفه‌ای\n👨‍💻 سازنده: @Mohammad778889\n\nاین ربات جهت دانلود سریع و آسان از پلتفرم‌های مختلف ساخته شده.\nبرای ارتباط مستقیم: @Mohammad778889",
        'rules': "📜 قوانین ربات\n\n• این ربات فقط برای استفاده شخصی طراحی شده.\n• مسئولیت محتوای دانلودشده بر عهده کاربر است.\n• ارسال لینک‌های غیرمجاز ممنوع است.\n• در صورت سوءاستفاده، حساب بسته خواهد شد.",
        'processing': "⏳ در حال پردازش لینک... لطفاً صبر کنید.",
        'download_ready': "✅ دانلود آماده است! فایل را دریافت کنید.",
        'download_error': "خطا در دانلود: {err}",
        'limit_exceeded': "⚠️ سقف دانلود امروز به پایان رسیده."
    },
    'en': {
        'start': "👋 Welcome to Pro Downloader!\n\nSend a link and the bot will auto-download video/audio for you.",
        'help_start': "📖 Help: Send a link and the bot will download it automatically.",
        'main_menu': "🧰 Main Menu\n\nCreate an account to unlock all features.",
        'help_main_instructions': "📘 Create account: press Create Account -> send full name -> send username (no @).",
        'help_panel': "📘 Panel guide: recent downloads, account status, settings.",
        'guest_restriction': "You are using Guest mode (15 downloads/day). Only Instagram and Spotify are available.",
        'panel_welcome': "👤 {name}, welcome to your panel!\n\nLimit today: {limit}\nPlatforms: YouTube • TikTok • Instagram • Spotify • SoundCloud",
        'about': "ℹ️ About\n\nBot: Pro Downloader\nAuthor: @Mohammad778889",
        'rules': "📜 Rules: Personal use only. User responsible for downloads. Illegal links prohibited.",
        'processing': "⏳ Processing the link...",
        'download_ready': "✅ Download ready!",
        'download_error': "Download error: {err}",
        'limit_exceeded': "⚠️ Daily download limit reached."
    },
    'ar': {
        'start': "👋 أهلاً بك في Pro Downloader!\n\nأرسل الرابط وسأقوم بالتنزيل تلقائيًا.",
        'help_start': "📖 تعليم: أرسل رابطًا وسيتم تنزيله تلقائيًا.",
        'main_menu': "🧰 القائمة الرئيسية\n\nأنشئ حسابًا للوصول إلى الميزات الكاملة.",
        'help_main_instructions': "📘 إنشاء حساب: اضغط على إنشاء حساب -> أرسل الاسم الكامل -> أرسل اسم المستخدم (بدون @).",
        'help_panel': "📘 دليل الحساب: التنزيلات الأخيرة، حالة الحساب، الإعدادات.",
        'guest_restriction': "أنت في وضع الضيف (15 تنزيل/يوم). فقط Instagram و Spotify متاحان.",
        'panel_welcome': "👤 {name}، مرحبًا بك!\n\nالحد اليومي: {limit}\nالمنصات: YouTube • TikTok • Instagram • Spotify • SoundCloud",
        'about': "ℹ️ حول\n\nبوت: Pro Downloader\nالمطور: @Mohammad778889",
        'rules': "📜 القواعد: للاستخدام الشخصي فقط. المستخدم مسؤول عن المحتوى.",
        'processing': "⏳ جاري المعالجة...",
        'download_ready': "✅ تم التحميل!",
        'download_error': "خطأ في التنزيل: {err}",
        'limit_exceeded': "⚠️ تم الوصول لحد التنزيل اليومي."
    }
}

def get(lang: str, key: str) -> str:
    if lang not in MESS:
        lang = 'fa'
    return MESS[lang].get(key, MESS['fa'].get(key, ''))
