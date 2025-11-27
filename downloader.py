# downloader.py
# wrapper برای yt_dlp که در ترد اجرا می‌شود تا event loop مسدود نشود.
# سعی می‌کند خروجی صوتی را به mp3 تبدیل کند (اگر ffmpeg نصب باشد)، در غیر این صورت فایل صوتی خروجی اصلی را ارسال می‌کنیم.

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
    # 'merge_output_format': 'mp4',  # optional
}

def _safe_filename(p: Path) -> str:
    return str(p).replace(" ", "_")

def _extract_platform(url: str) -> str:
    url_lower = url.lower()
    if "youtube" in url_lower or "youtu.be" in url_lower:
        return "YouTube"
    if "tiktok" in url_lower:
        return "TikTok"
    if "instagram" in url_lower:
        return "Instagram"
    if "soundcloud" in url_lower:
        return "SoundCloud"
    if "spotify" in url_lower:
        return "Spotify"
    return "Unknown"

def _yt_dlp_download(url: str, audio_only: bool = False):
    """
    This function runs inside a thread (not in asyncio loop).
    Returns: (filepath: str, title: str, file_type: 'audio'|'video')
    """
    opts = YTDLP_DEFAULT_OPTS.copy()
    temp_id = str(uuid.uuid4())[:8]
    opts['outtmpl'] = str(DOWNLOAD_DIR / f"{temp_id}_%(id)s.%(ext)s")
    # If audio requested, ask for bestaudio
    if audio_only:
        opts['format'] = 'bestaudio/best'
        # try to extract mp3 via postprocessor (requires ffmpeg)
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # find downloaded file
            video_id = info.get('id')
            title = info.get('title') or "media"
            # match file path by glob
            # we will search for files that start with temp_id_ and contain video_id
            matches = list(DOWNLOAD_DIR.glob(f"{temp_id}_*{video_id}.*"))
            if not matches:
                # try generic search for video_id
                matches = list(DOWNLOAD_DIR.glob(f"*{video_id}.*"))
            if not matches:
                raise RuntimeError("فایل دانلود شده پیدا نشد")
            file_path = matches[0]
            ext = file_path.suffix.lower()
            file_type = 'audio' if audio_only or ext in ['.mp3', '.m4a', '.webm', '.aac'] else 'video'
            return str(file_path), title, file_type
    except Exception as e:
        # bubble up
        raise

async def download_url(url: str, audio_only: bool = False, timeout: int = DOWNLOAD_TIMEOUT):
    """
    Async wrapper که در event loop فراخوانی می‌شود.
    """
    loop = asyncio.get_running_loop()
    try:
        coro = asyncio.to_thread(_yt_dlp_download, url, audio_only)
        # Wrap with timeout to prevent blocking همیشگی
        result = await asyncio.wait_for(coro, timeout=timeout)
        return result  # (filepath, title, file_type)
    except asyncio.TimeoutError:
        raise RuntimeError("Timeout: دانلود طولانی شد یا معلق ماند.")
    except Exception as e:
        # Propagate upward with message
        raise

def safe_remove(path: str):
    try:
        os.remove(path)
    except Exception:
        try:
            # if dir
            shutil.rmtree(path)
        except Exception:
            pass
