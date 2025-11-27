# utils.py
# توابع کمکی
from typing import Tuple
def detect_platform(url: str) -> str:
    u = url.lower()
    if "youtube" in u or "youtu.be" in u:
        return "YouTube"
    if "tiktok" in u:
        return "TikTok"
    if "instagram" in u:
        return "Instagram"
    if "soundcloud" in u:
        return "SoundCloud"
    if "spotify" in u:
        return "Spotify"
    return "Unknown"

def looks_like_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")
