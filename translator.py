from googletrans import Translator
_tr = Translator()

def translate_if_needed(text, src, dest):
    if src == dest:
        return text
    try:
        res = _tr.translate(text, src=src, dest=dest)
        return res.text
    except Exception:
        return text  # fallback to fa
