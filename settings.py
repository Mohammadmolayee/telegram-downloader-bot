# settings.py
# تنظیمات مرکزی ربات — محیط (ENV) خوانده می‌شود
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

TOKEN = os.getenv("TOKEN")  # حتما در Railway/Env قرار بده
if not TOKEN:
    raise RuntimeError("TOKEN را در متغیرهای محیطی (Environment) تنظیم کن.")

DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

DB_PATH = BASE_DIR / "downloads.db"

# محدودیت‌ها
GUEST_DAILY_LIMIT = 15
USER_DAILY_LIMIT = 25

# yt-dlp options defaults
# کیفیت ویدیو (حداکثر height) — 480 برای سبک بودن سرور
MAX_VIDEO_HEIGHT = 480

# تغییرات اختیاری: اندازه timeout برای دانلود (در ثانیه)
DOWNLOAD_TIMEOUT = 60 * 60 * 2  # 2 ساعت برای ویدیوهای طولانی

# اگر می‌خوای برای تست لاگ‌های بیشتر
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
