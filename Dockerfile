FROM python:3.12-slim

WORKDIR /app

# FFmpeg + ffprobe for video production
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Directories for output
RUN mkdir -p /data/reports /data/videos /data/music

# Font for ASS subtitles (copy if present in project)
RUN if [ -d fonts ]; then cp fonts/*.ttf /usr/share/fonts/truetype/ 2>/dev/null; fc-cache -f; fi

EXPOSE 3000

# Longer timeout for video generation (pipeline can take 15+ min)
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "1", "--threads", "4", "--timeout", "1800", "--preload", "app:app"]
