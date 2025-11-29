# keyboards.py
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from messages import BUTTONS
from translator import translate_text

# reply keyboards (two-row layouts etc.)
def guest_keyboard(lang="fa"):
    order = [
        [BUTTONS["help"], BUTTONS["rules"]],
        [BUTTONS["about"], BUTTONS["features"]],
        [BUTTONS["language"], BUTTONS["create"]]
    ]
    return _make_reply(order, lang)

def member_keyboard(lang="fa"):
    order = [
        [BUTTONS["stats"], BUTTONS["features"]],
        [BUTTONS["help"], BUTTONS["rules"]],
        [BUTTONS["about"], BUTTONS["language"]],
        [BUTTONS["settings"]]
    ]
    return _make_reply(order, lang)

def back_keyboard(lang="fa"):
    lab = translate_text(BUTTONS["back"], lang) if lang != "fa" else BUTTONS["back"]
    return ReplyKeyboardMarkup([[lab]], resize_keyboard=True, one_time_keyboard=True)

def cancel_keyboard(lang="fa"):
    lab = translate_text(BUTTONS["cancel"], lang) if lang != "fa" else BUTTONS["cancel"]
    return ReplyKeyboardMarkup([[lab]], resize_keyboard=True, one_time_keyboard=True)

def _make_reply(layout, lang):
    # translate labels per lang
    kb = []
    for row in layout:
        r = []
        for label in row:
            rlabel = translate_text(label, lang) if lang != "fa" else label
            r.append(rlabel)
        kb.append(r)
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)
