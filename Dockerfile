FROM python:3.10-slim

# اطلاعات نسخه
LABEL maintainer="SelfBot Team"
LABEL version="1.0"
LABEL description="Telegram SelfBot با قابلیت‌های پیشرفته امنیتی و هوش مصنوعی"

# تنظیم متغیرهای محیطی
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tehran

# تنظیم دایرکتوری کاری
WORKDIR /app

# نصب وابستگی‌های سیستمی
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل requirements.txt و نصب وابستگی‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل پروژه
COPY . .

# ایجاد کاربر غیر روت برای اجرای برنامه
RUN useradd -m selfbot
RUN chown -R selfbot:selfbot /app
USER selfbot

# دستور اجرا
CMD ["python", "main.py"]
