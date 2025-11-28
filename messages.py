TEXTS = {
    "start_guest": {
        "fa": "👋 سلام! به ربات دانلودر حرفه‌ای خوش اومدی!\n\n📥 قابلیت‌های حالت مهمان:\n• دانلود اینستاگرام\n• دانلود اسپاتیفای\n\n⚠️ برای دانلود یوتیوب، تیک‌تاک و ساندکلاد باید حساب بسازی.\n\n💡 فقط لینک رو بفرست — دانلود خودکار شروع میشه",
        "en": "👋 Welcome to the professional downloader bot!\n\n📥 Guest features:\n• Instagram download\n• Spotify download\n\n⚠️ You need an account for YouTube, TikTok, and SoundCloud downloads.\n\n💡 Just send a link — download starts automatically.",
        "ar": "👋 أهلاً بك في روبوت التحميل الاحترافي!\n\n📥 ميزات الضيف:\n• تحميل إنستغرام\n• تحميل سبوتيفاي\n\n⚠️ يلزمك حساب لتحميل يوتيوب وتيك توك وساوند كلاود.\n\n💡 فقط أرسل الرابط — يبدأ التحميل تلقائياً."
    },

    "start_member": {
        "fa": "🎉 خوش اومدی! این پنل کاربری توست.",
        "en": "🎉 Welcome! This is your dashboard.",
        "ar": "🎉 مرحباً! هذه هي لوحة حسابك."
    },

    "account_created": {
        "fa": "✔ حساب با موفقیت ساخته شد.",
        "en": "✔ Account created successfully.",
        "ar": "✔ تم إنشاء الحساب بنجاح."
    },

    "choose_lang": {
        "fa": "🌐 لطفا زبان را انتخاب کنید:",
        "en": "🌐 Choose your language:",
        "ar": "🌐 اختر لغتك:"
    },

    "lang_changed": {
        "fa": "🌐 زبان با موفقیت تغییر کرد.",
        "en": "🌐 Language updated successfully.",
        "ar": "🌐 تم تغيير اللغة بنجاح."
    }
}

def t(key, lang):
    if key not in TEXTS:
        return "..."
    return TEXTS[key].get(lang, TEXTS[key]["fa"])
