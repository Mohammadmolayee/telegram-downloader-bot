FROM python:3.11-slim

# install ffmpeg and essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg wget curl build-essential \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# copy project
COPY . /app

# create temp folders
RUN mkdir -p /app/temp

ENV BOT_TOKEN=TOKEN_HERE

# run
CMD ["python", "bot.py"]
