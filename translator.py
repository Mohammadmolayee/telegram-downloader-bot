# translator.py
from deep_translator import GoogleTranslator
from functools import lru_cache

@lru_cache(maxsize=1024)
def translate_text(text: str, target: str):
    """
    Translate `text` (assumed Persian or auto-detected) into target lang 'fa'/'en'/'ar'.
    If target == 'fa' returns original text.
    """
    if not text:
        return text
    if target == "fa":
        return text
    try:
        # deep_translator GoogleTranslator may auto-detect source
        return GoogleTranslator(source='auto', target=target).translate(text)
    except Exception:
        # fallback: return original
        return text
