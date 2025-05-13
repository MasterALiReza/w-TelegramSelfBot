FROM node:18-alpine

# اطلاعات نسخه
LABEL maintainer="SelfBot Team"
LABEL version="1.0"
LABEL description="Telegram SelfBot Web Panel"

# تنظیم دایرکتوری کاری
WORKDIR /app

# نصب وابستگی‌ها
COPY web/package.json web/package-lock.json* ./
RUN npm ci --production

# کپی کد سورس
COPY web/ ./

# ساخت برنامه
RUN npm run build

# نمایش پورت مورد استفاده
EXPOSE 3000

# دستور اجرا
CMD ["npm", "start"]
