# translator.py
import json
import os

TRANSLATE_DB = "translations.json"

if not os.path.exists(TRANSLATE_DB):
    with open(TRANSLATE_DB, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

def load_db():
    with open(TRANSLATE_DB, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(TRANSLATE_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def tr(lang: str, text: str):
    if lang == "fa":
        return text
    db = load_db()
    if text in db and lang in db[text]:
        return db[text][lang]
    en = auto_english(text)
    ar = auto_arabic(text)
    db[text] = {"fa": text, "en": en, "ar": ar}
    save_db(db)
    return db[text].get(lang, text)

def auto_english(text: str):
    simple_dict = {
        "سلام": "Hello", "خوش اومدی": "Welcome", "خوش آمدی": "Welcome",
        "دانلود": "Download", "لطفا لینک را بفرست": "Please send the link",
        "در حال دانلود": "Downloading...", "دانلود کامل شد": "Download finished",
        "ساخت حساب": "Create account", "پنل کاربری": "User panel",
        "لغو دانلود": "Cancel download", "دانلود لغو شد": "Download cancelled"
    }
    out = text
    for fa, en in simple_dict.items():
        out = out.replace(fa, en)
    return out

def auto_arabic(text: str):
    simple_dict = {
        "سلام": "مرحبا", "خوش اومدی": "اهلا بك", "خوش آمدی": "اهلا بك",
        "دانلود": "تحميل", "لطفا لینک را بفرست": "أرسل الرابط من فضلك",
        "در حال دانلود": "جاري التحميل...", "دانلود کامل شد": "اكتمل التنزيل",
        "ساخت حساب": "إنشاء حساب", "پنل کاربری": "لوحة المستخدم",
        "لغو دانلود": "إلغاء التنزيل", "دانلود لغو شد": "تم إلغاء التنزيل"
    }
    out = text
    for fa, ar in simple_dict.items():
        out = out.replace(fa, ar)
    return out
