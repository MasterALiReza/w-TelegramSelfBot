FROM python:3.10-slim

# اطلاعات نسخه
LABEL maintainer="SelfBot Team"
LABEL version="1.0"
LABEL description="Telegram SelfBot API Service"

# تنظیم متغیرهای محیطی
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Tehran

# تنظیم دایرکتوری کاری
WORKDIR /app

# نصب وابستگی‌های سیستمی
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل requirements.txt و نصب وابستگی‌ها
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کد سرویس API
COPY api/ /app/api/
COPY core/ /app/core/

# ایجاد کاربر غیر روت برای اجرای برنامه
RUN useradd -m apiuser
RUN mkdir -p /app/logs && chown -R apiuser:apiuser /app
USER apiuser

# نمایش پورت مورد استفاده
EXPOSE 8000

# دستور اجرا
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
