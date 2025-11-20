# config.py
BOT_NAME = "بات دانلودر حرفه ای"

# محدودیت‌ها
GUEST_DAILY_LIMIT = 15
REGISTERED_DAILY_LIMIT = 25

# مسیرها و تنظیمات دانلود
DATABASE_PATH = "downloads.db"
DOWNLOAD_FOLDER = "downloads"
MAX_VIDEO_DOC_SIZE = 50 * 1024 * 1024  # اگر بزرگتر بود به صورت document می‌فرستیم
CLEANUP_OLDER_THAN_SEC = 10 * 60  # فایل‌های قدیمی‌تر از 10 دقیقه پاک شوند

# yt-dlp default options (قابل تغییر)
YTDL_DEFAULT_VIDEO_FORMAT = "bestvideo[height<=720]+bestaudio/best/best"
YTDL_DEFAULT_AUDIO_FORMAT = "bestaudio/best"
