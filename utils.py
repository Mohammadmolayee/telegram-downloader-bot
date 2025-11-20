# utils.py
from urllib.parse import urlparse

def detect_platform(url: str) -> str | None:
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "tiktok.com" in u:
        return "tiktok"
    if "instagram.com" in u or "instagram" in u:
        return "instagram"
    if "soundcloud.com" in u:
        return "soundcloud"
    if "spotify.com" in u:
        return "spotify"
    return None

def is_audio_platform(platform: str) -> bool:
    return platform in ("soundcloud", "spotify")

def is_video_platform(platform: str) -> bool:
    return platform in ("youtube", "tiktok", "instagram")
