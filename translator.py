# translator.py
from deep_translator import GoogleTranslator

def tr(text: str, lang: str):
    """
    ترجمه خودکار متن از فارسی به زبان انتخابی کاربر
    """
    if lang == "fa":
        return text
    
    try:
        return GoogleTranslator(source="auto", target=lang).translate(text)
    except:
        return text  # درصورت خطا متن فارسی نمایش می‌دهد
