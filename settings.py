# settings.py
# تنظیمات مرکزی پروژه

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("توکن ربات را در متغیر محیطی TOKEN قرار بده (Railway/Env Vars).")

DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "downloads.db"

# limits
GUEST_DAILY_LIMIT = int(os.getenv("GUEST_DAILY_LIMIT", 15))
USER_DAILY_LIMIT = int(os.getenv("USER_DAILY_LIMIT", 25))

# yt-dlp / downloader
MAX_VIDEO_HEIGHT = int(os.getenv("MAX_VIDEO_HEIGHT", 480))
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", 60 * 60 * 2))  # 2 hours

# logging
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
