# messages.py
import translator as tr

def t(user_like, key, **fmt):
    """
    user_like: dict {'language': 'fa'} or language string 'fa'
    key: key from translator.BASE
    """
    lang = "fa"
    if isinstance(user_like, dict):
        lang = user_like.get("language", "fa")
    elif isinstance(user_like, str):
        lang = user_like
    return tr.t(lang, key, **fmt)
