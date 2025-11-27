# settings.py
"""
تنظیمات کلی ربات
"""

# ---------------------
# BOT & DATABASE
# ---------------------
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
DB_PATH = "database.db"

# ---------------------
# LIMITS
# ---------------------
GUEST_DAILY_LIMIT = 15
USER_DAILY_LIMIT = 25

# ---------------------
# THEMES
# ---------------------
DEFAULT_THEME = "light"   # light / dark

THEME_COLORS = {
    "light": {
        "bg": "🌤️",
        "btn": "🔘"
    },
    "dark": {
        "bg": "🌑",
        "btn": "⚫"
    }
}

# ---------------------
# DOWNLOAD SETTINGS
# ---------------------
VIDEO_QUALITY = "480p"
AUDIO_FORMAT = "mp3"
