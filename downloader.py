# downloader.py
# async-friendly wrapper برای yt-dlp — اجرا در thread تا event loop مسدود نشود.
import yt_dlp
import asyncio
import shutil
from pathlib import Path
from settings import DOWNLOAD_DIR, MAX_VIDEO_HEIGHT, DOWNLOAD_TIMEOUT
import os
import uuid

YTDLP_DEFAULT_OPTS = {
    'format': f'bestvideo[height<={MAX_VIDEO_HEIGHT}]+bestaudio/best[height<={MAX_VIDEO_HEIGHT}]',
    'outtmpl': str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
    'noplaylist': True,
    'retries': 3,
    'quiet': True,
    'no_warnings': True,
}

def _extract_platform(url: str) -> str:
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

def _yt_dlp_download(url: str, audio_only: bool = False):
    opts = YTDLP_DEFAULT_OPTS.copy()
    temp_id = str(uuid.uuid4())[:8]
    opts['outtmpl'] = str(DOWNLOAD_DIR / f"{temp_id}_%(id)s.%(ext)s")
    if audio_only:
        opts['format'] = 'bestaudio/best'
        # try mp3 conversion if ffmpeg available
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            vid = info.get('id', '')
            title = info.get('title', 'media')
            matches = list(DOWNLOAD_DIR.glob(f"{temp_id}_*{vid}.*"))
            if not matches:
                matches = list(DOWNLOAD_DIR.glob(f"*{vid}.*"))
            if not matches:
                # fallback: take newest file with temp_id prefix
                matches = list(DOWNLOAD_DIR.glob(f"{temp_id}_*.*"))
            if not matches:
                raise RuntimeError("فایل دانلود شده پیدا نشد.")
            file_path = matches[0]
            ext = file_path.suffix.lower()
            file_type = 'audio' if audio_only or ext in ['.mp3', '.m4a', '.aac', '.ogg'] else 'video'
            return str(file_path), title, file_type
    except Exception as e:
        raise

async def download_url(url: str, audio_only: bool = False, timeout: int = DOWNLOAD_TIMEOUT):
    loop = asyncio.get_running_loop()
    try:
        coro = asyncio.to_thread(_yt_dlp_download, url, audio_only)
        res = await asyncio.wait_for(coro, timeout=timeout)
        return res
    except asyncio.TimeoutError:
        raise RuntimeError("Timeout: دانلود طولانی شد.")
    except Exception as e:
        raise

def safe_remove(path: str):
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
    except Exception:
        pass
