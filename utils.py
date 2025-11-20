# utils.py
# توابع کمکی برای مدیریت کاربران مهمان/عضو + تشخیص نوع لینک

from config import SUPPORTED_VIDEO, SUPPORTED_AUDIO


def is_guest(user_id, users_db):
    """کاربر عضو هست یا مهمان؟"""
    return user_id not in users_db


def detect_platform(url: str):
    url = url.lower()

    if any(x in url for x in SUPPORTED_VIDEO):
        return "video"

    if any(x in url for x in SUPPORTED_AUDIO):
        return "audio"

    return None
