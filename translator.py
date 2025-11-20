# translator.py
try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None

_cache = {}

def translate(text: str, lang: str = "fa") -> str:
    """
    text: متن فارسی
    lang: 'fa'|'en'|'ar'
    """
    if not text:
        return ""
    if lang == "fa":
        return text
    key = (text, lang)
    if key in _cache:
        return _cache[key]
    if GoogleTranslator is None:
        # fallback conservative: متن فارسی را برگردان
        return text
    try:
        res = GoogleTranslator(source='auto', target=lang).translate(text)
    except Exception:
        res = text
    _cache[key] = res
    return res
