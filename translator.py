# translator.py
# ترجمه هوشمند فارسی → انگلیسی / عربی
# سبک، سریع، بدون نیاز به API خارجی

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

_translation_cache = {}


def translate(text: str, lang: str = "fa") -> str:
    """
    text: متن فارسی
    lang: fa / en / ar
    """
    if lang == "fa":
        return text

    key = (text, lang)
    if key in _translation_cache:
        return _translation_cache[key]

    if GoogleTranslator is None:
        return text

    try:
        translated = GoogleTranslator(source="auto", target=lang).translate(text)
    except Exception:
        translated = text

    _translation_cache[key] = translated
    return translated
