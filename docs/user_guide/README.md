# راهنمای کاربری سلف بات تلگرام

## معرفی
سلف بات تلگرام یک ابزار پیشرفته برای مدیریت خودکار حساب تلگرام است که به کاربران امکان می‌دهد عملکردهای حساب خود را از طریق پلاگین‌های مختلف ارتقا دهند. این راهنما برای کمک به کاربران در نصب، راه‌اندازی و استفاده از سلف بات تلگرام طراحی شده است.

## پیش‌نیازها
قبل از نصب و راه‌اندازی سلف بات تلگرام، مطمئن شوید که موارد زیر روی سیستم شما نصب شده‌اند:

- پایتون نسخه 3.11 یا بالاتر
- Docker و Docker Compose (برای نصب از طریق کانتینر)
- حداقل 1GB RAM و 1GB فضای دیسک
- دسترسی به اینترنت برای دانلود وابستگی‌ها و تعامل با API تلگرام

## روش‌های نصب

### روش 1: نصب مستقیم

1. کلون کردن مخزن گیت:
```bash
git clone https://github.com/your-username/telegram-selfbot.git
cd telegram-selfbot
```

2. ایجاد محیط مجازی:
```bash
python -m venv venv
# فعال‌سازی در ویندوز
venv\Scripts\activate
# فعال‌سازی در لینوکس/مک
source venv/bin/activate
```

3. نصب وابستگی‌ها:
```bash
pip install -r requirements.txt
```

4. تنظیم فایل .env:
```bash
cp .env.example .env
# فایل .env را با اطلاعات خود ویرایش کنید
```

5. اجرای برنامه:
```bash
python main.py
```

### روش 2: استفاده از Docker

1. کلون کردن مخزن گیت:
```bash
git clone https://github.com/your-username/telegram-selfbot.git
cd telegram-selfbot
```

2. تنظیم فایل .env:
```bash
cp .env.example .env
# فایل .env را با اطلاعات خود ویرایش کنید
```

3. ساخت و اجرای کانتینرها:
```bash
docker-compose up -d
```

## راه‌اندازی اولیه

### دریافت API ID و API Hash تلگرام

1. به [my.telegram.org](https://my.telegram.org/) مراجعه کنید
2. وارد شوید و به بخش "API development tools" بروید
3. یک برنامه جدید ایجاد کنید (نام و پلتفرم را به دلخواه وارد کنید)
4. API ID و API Hash را کپی کنید
5. این اطلاعات را در فایل .env قرار دهید:
```
API_ID=your_api_id
API_HASH=your_api_hash
```

### تنظیم دیتابیس Supabase

1. یک حساب در [Supabase](https://supabase.io/) ایجاد کنید
2. یک پروژه جدید بسازید
3. از بخش Project Settings > API، مقادیر URL و ANON_KEY را کپی کنید
4. این اطلاعات را در فایل .env قرار دهید:
```
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
```

### ورود به حساب تلگرام

1. پس از اجرای برنامه، از شما خواسته می‌شود که شماره تلفن خود را وارد کنید
2. کد تأیید دریافتی را وارد کنید
3. در صورت نیاز، رمز عبور دو مرحله‌ای را وارد کنید
4. پس از اتمام، فایل جلسه (session) ایجاد می‌شود و برای ورودهای بعدی نیازی به تکرار این مراحل نیست

## استفاده از وب پنل

سلف بات تلگرام دارای یک رابط کاربری وب است که امکان مدیریت و کنترل آسان را فراهم می‌کند.

### دسترسی به وب پنل

1. پس از راه‌اندازی موفق، وب پنل در آدرس زیر در دسترس خواهد بود:
```
http://localhost:8000
```

2. در صفحه ورود، از نام کاربری و رمز عبور پیش‌فرض استفاده کنید:
- نام کاربری: admin
- رمز عبور: admin123

3. بعد از اولین ورود، حتماً رمز عبور پیش‌فرض را تغییر دهید.

### بخش‌های اصلی وب پنل

#### داشبورد
- نمای کلی از وضعیت سیستم
- آمار عملکرد
- نمودارهای فعالیت

#### مدیریت پلاگین‌ها
- فعال/غیرفعال کردن پلاگین‌ها
- تنظیمات هر پلاگین
- نصب پلاگین‌های جدید
- حذف پلاگین‌ها

#### تنظیمات
- تنظیمات کلی سیستم
- مدیریت حساب کاربری
- تنظیمات امنیتی
- پشتیبان‌گیری و بازیابی

#### لاگ‌ها
- مشاهده رویدادها و فعالیت‌ها
- جستجو در لاگ‌ها
- فیلتر بر اساس سطح اهمیت

## استفاده از دستورات تلگرام

سلف بات تلگرام از طریق دستورات قابل اجرا در تلگرام نیز قابل کنترل است. این دستورات با پیشوند `.` (نقطه) شروع می‌شوند.

### دستورات عمومی

- `.help` - نمایش لیست دستورات قابل استفاده
- `.status` - نمایش وضعیت سیستم
- `.restart` - راه‌اندازی مجدد سلف بات
- `.backup` - تهیه پشتیبان از تنظیمات و داده‌ها
- `.ping` - بررسی زنده بودن سلف بات

### مدیریت پلاگین‌ها

- `.plugins` - نمایش لیست پلاگین‌های نصب شده
- `.enable [نام پلاگین]` - فعال کردن یک پلاگین
- `.disable [نام پلاگین]` - غیرفعال کردن یک پلاگین
- `.reload [نام پلاگین]` - بارگذاری مجدد یک پلاگین

### تنظیمات

- `.settings` - نمایش تنظیمات فعلی
- `.setlang [زبان]` - تغییر زبان رابط کاربری
- `.setprefix [پیشوند]` - تغییر پیشوند دستورات (پیش‌فرض: `.`)

## پلاگین‌های پیش‌فرض

سلف بات تلگرام با تعدادی پلاگین پیش‌فرض ارائه می‌شود:

### پلاگین‌های مدیریتی

#### پلاگین مدیریت گروه
- مدیریت خودکار گروه‌ها
- پاسخ خودکار به درخواست‌های عضویت
- حذف خودکار پیام‌های نامناسب

استفاده:
- `.group stats` - نمایش آمار گروه
- `.group clean` - پاکسازی پیام‌های قدیمی
- `.group settings` - تنظیمات گروه

#### پلاگین پشتیبان‌گیری
- پشتیبان‌گیری خودکار از چت‌ها
- ذخیره رسانه‌ها به صورت خودکار

استفاده:
- `.backup chat [ID چت]` - پشتیبان‌گیری از یک چت خاص
- `.backup media` - پشتیبان‌گیری از رسانه‌ها
- `.restore [ID پشتیبان]` - بازیابی از پشتیبان

### پلاگین‌های امنیتی

#### پلاگین محافظت از حساب
- تشخیص و جلوگیری از دسترسی غیرمجاز
- هشدار در صورت ورود مشکوک

استفاده:
- `.security status` - نمایش وضعیت امنیتی
- `.security lock` - قفل کردن حساب
- `.security 2fa` - مدیریت احراز هویت دو مرحله‌ای

#### پلاگین فایروال
- محدودیت دسترسی بر اساس کاربر، گروه یا کلیدواژه
- بلاک خودکار کاربران مزاحم

استفاده:
- `.firewall add [الگو]` - افزودن قانون فایروال
- `.firewall list` - نمایش قوانین فایروال
- `.firewall remove [ID قانون]` - حذف قانون فایروال

### پلاگین‌های هوش مصنوعی

#### پلاگین پردازش متن
- پاسخ خودکار با استفاده از OpenAI/Claude
- خلاصه‌سازی متن‌های طولانی

استفاده:
- `.ai chat [پرسش]` - شروع گفتگو با هوش مصنوعی
- `.ai summarize` - خلاصه‌سازی متن (در پاسخ به یک پیام)
- `.ai translate [زبان]` - ترجمه متن

#### پلاگین پردازش تصویر
- تولید تصویر با Stable Diffusion
- ویرایش و بهبود تصاویر

استفاده:
- `.image create [توضیحات]` - ایجاد تصویر جدید
- `.image enhance` - بهبود کیفیت تصویر (در پاسخ به یک تصویر)
- `.image style [سبک]` - تغییر سبک تصویر

## عیب‌یابی و حل مشکلات رایج

### مشکل: برنامه اجرا نمی‌شود
1. بررسی کنید که تمام وابستگی‌ها نصب شده‌اند: `pip install -r requirements.txt`
2. بررسی کنید که فایل .env به درستی تنظیم شده است
3. بررسی کنید که سرویس Redis در حال اجرا است
4. لاگ‌های برنامه را در پوشه logs بررسی کنید

### مشکل: خطای احراز هویت تلگرام
1. API ID و API Hash را در فایل .env بررسی کنید
2. فایل جلسه (session) قبلی را حذف کنید و دوباره وارد شوید
3. بررسی کنید که حساب شما محدود یا مسدود نشده باشد

### مشکل: پلاگین‌ها کار نمی‌کنند
1. بررسی کنید که پلاگین فعال است: `.plugins`
2. لاگ‌های خطا را بررسی کنید: `.logs error`
3. پلاگین را دوباره بارگذاری کنید: `.reload [نام پلاگین]`

### مشکل: وب پنل قابل دسترسی نیست
1. بررسی کنید که سرویس API در حال اجرا است
2. پورت 8000 را بررسی کنید که آزاد و در دسترس باشد
3. فایروال سیستم را بررسی کنید که اجازه اتصال به پورت 8000 را می‌دهد

## ارتقا و بروزرسانی

### بروزرسانی نرم‌افزار

1. روش استفاده از گیت:
```bash
git pull
pip install -r requirements.txt
```

2. روش استفاده از Docker:
```bash
docker-compose down
git pull
docker-compose build
docker-compose up -d
```

### افزودن پلاگین‌های جدید

1. از طریق وب پنل:
   - به بخش "مدیریت پلاگین‌ها" بروید
   - بر روی "نصب پلاگین جدید" کلیک کنید
   - فایل ZIP پلاگین را آپلود کنید

2. به صورت دستی:
   - فایل‌های پلاگین را در پوشه plugins قرار دهید
   - سلف بات را مجدداً راه‌اندازی کنید یا از دستور `.reload` استفاده کنید

## پشتیبانی و کمک بیشتر

### منابع آنلاین
- ویکی پروژه: [GitHub Wiki](https://github.com/your-username/telegram-selfbot/wiki)
- گروه پشتیبانی تلگرام: [@selfbot_support](https://t.me/selfbot_support)
- انجمن: [Community Forum](https://forum.telegram-selfbot.com)

### گزارش مشکلات
اگر با مشکل یا باگی مواجه شدید، لطفاً آن را در صفحه مشکلات گیت‌هاب گزارش دهید:
[GitHub Issues](https://github.com/your-username/telegram-selfbot/issues)

### کمک به توسعه
کمک‌های شما برای بهبود پروژه بسیار ارزشمند است. اگر می‌خواهید در توسعه پروژه مشارکت داشته باشید، لطفاً دستورالعمل‌های مشارکت را مطالعه کنید:
[CONTRIBUTING.md](https://github.com/your-username/telegram-selfbot/CONTRIBUTING.md)

## نکات امنیتی مهم

1. **حفظ امنیت اطلاعات حساب**: هرگز API ID، API Hash یا فایل‌های session خود را با دیگران به اشتراک نگذارید.

2. **استفاده مسئولانه**: از سلف بات برای اسپم، آزار یا نقض قوانین تلگرام استفاده نکنید.

3. **به‌روزرسانی مرتب**: برای بهره‌مندی از بهبودهای امنیتی، همیشه نرم‌افزار را به‌روز نگه دارید.

4. **پشتیبان‌گیری منظم**: به طور مرتب از تنظیمات و داده‌های خود پشتیبان تهیه کنید.

5. **رمزگذاری**: برای افزایش امنیت، از رمزگذاری برای فایل‌های حساس استفاده کنید.

## پیوست‌ها

### ساختار فایل .env
```
# API تلگرام
API_ID=your_api_id
API_HASH=your_api_hash

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# امنیت
SECRET_KEY=your_secret_key
CRYPTO_KEY=your_crypto_key

# تنظیمات عمومی
LOG_LEVEL=INFO
COMMAND_PREFIX=.
DEFAULT_LANGUAGE=fa
```

### فهرست API‌های سلف بات
برای توسعه‌دهندگانی که می‌خواهند با API سلف بات تعامل داشته باشند، [اینجا](docs/api/README.md) را مطالعه کنید.

### راهنمای توسعه پلاگین
برای اطلاعات بیشتر در مورد نحوه توسعه پلاگین‌های سفارشی، [اینجا](docs/plugin_development/README.md) را مطالعه کنید.
