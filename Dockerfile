FROM python:3.11-slim

# نصب FFmpeg + وابستگی‌های yt-dlp
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg wget curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# پوشه کاری
WORKDIR /app

# نصب نیازمندی‌ها
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# کپی پروژه
COPY . /app

# آپدیت اتومات yt-dlp
RUN yt-dlp -U

# اجرای ربات
CMD ["python", "bot.py"]
