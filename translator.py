from deep_translator import GoogleTranslator
from functools import lru_cache

@lru_cache(maxsize=512)
def translate_text(text: str, target: str):
    try:
        if target == "fa":
            return text
        # source is fa by design
        translated = GoogleTranslator(source='auto', target=target).translate(text)
        return translated
    except Exception:
        return text  # fallback to fa
