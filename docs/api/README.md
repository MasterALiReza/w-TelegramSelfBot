# مستندات API سلف بات تلگرام

## مقدمه
API سلف بات تلگرام یک رابط برنامه‌نویسی RESTful است که امکان مدیریت و کنترل سلف بات تلگرام را از طریق درخواست‌های HTTP فراهم می‌کند. این API با استفاده از FastAPI پیاده‌سازی شده و از JWT برای احراز هویت استفاده می‌کند.

## نقطه دسترسی
آدرس پایه API:
```
http://localhost:8000
```

در محیط پروداکشن، آدرس دامنه شما جایگزین localhost می‌شود.

## احراز هویت
تمام درخواست‌ها به API (به جز نقاط پایانی عمومی) نیاز به احراز هویت دارند. احراز هویت با استفاده از Bearer Token انجام می‌شود.

### دریافت توکن
برای دریافت توکن، باید از نقطه پایانی زیر استفاده کنید:

```
POST /token
```

پارامترهای درخواست:
- `username`: نام کاربری
- `password`: رمز عبور

نمونه درخواست:
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=password"
```

نمونه پاسخ:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### استفاده از توکن
برای تمام درخواست‌هایی که نیاز به احراز هویت دارند، باید هدر `Authorization` را به صورت زیر تنظیم کنید:

```
Authorization: Bearer {your_token_here}
```

نمونه:
```bash
curl -X GET "http://localhost:8000/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## نقاط پایانی
در ادامه، اطلاعات مربوط به نقاط پایانی اصلی API ارائه شده است.

### عمومی

#### ریشه API
```
GET /
```
این نقطه پایانی پیام خوش‌آمدگویی برای API را برمی‌گرداند.

#### وضعیت سرور
```
GET /status
```
وضعیت فعلی سرور و اتصالات دیتابیس را برمی‌گرداند.

### مدیریت کاربران

#### دریافت اطلاعات کاربر جاری
```
GET /users/me
```
اطلاعات کاربر فعلی احراز هویت شده را برمی‌گرداند.

#### دریافت لیست کاربران
```
GET /users/
```
پارامترهای Query:
- `page`: شماره صفحه (پیش‌فرض: 1)
- `limit`: تعداد آیتم در هر صفحه (پیش‌فرض: 10)
- `search`: جستجو بر اساس نام کاربری یا ایمیل

#### دریافت اطلاعات یک کاربر خاص
```
GET /users/{user_id}
```

#### ایجاد کاربر جدید
```
POST /users/
```
نمونه داده درخواست:
```json
{
  "username": "new_user",
  "email": "user@example.com",
  "password": "StrongPassword123",
  "name": "کاربر جدید",
  "role": "user",
  "permissions": ["view_dashboard", "use_selfbot"]
}
```

#### به‌روزرسانی کاربر
```
PATCH /users/{user_id}
```
نمونه داده درخواست:
```json
{
  "name": "نام به‌روزرسانی شده",
  "email": "updated@example.com"
}
```

#### حذف کاربر
```
DELETE /users/{user_id}
```

### مدیریت پلاگین‌ها

#### دریافت لیست پلاگین‌ها
```
GET /plugins/
```
پارامترهای Query:
- `page`: شماره صفحه (پیش‌فرض: 1)
- `limit`: تعداد آیتم در هر صفحه (پیش‌فرض: 10)
- `plugin_type`: فیلتر بر اساس نوع پلاگین
- `status`: فیلتر بر اساس وضعیت پلاگین
- `search`: جستجو بر اساس نام یا توضیحات

#### دریافت اطلاعات یک پلاگین خاص
```
GET /plugins/{plugin_id}
```

#### ایجاد پلاگین جدید
```
POST /plugins/
```
نمونه داده درخواست:
```json
{
  "name": "new_plugin",
  "version": "1.0.0",
  "description": "پلاگین جدید",
  "author": "نویسنده",
  "category": "utility",
  "source_code": "async def start(message):\n    return \"Hello World!\""
}
```

#### به‌روزرسانی پلاگین
```
PATCH /plugins/{plugin_id}
```
نمونه داده درخواست:
```json
{
  "description": "توضیحات به‌روزرسانی شده",
  "version": "1.0.1"
}
```

#### تغییر وضعیت پلاگین (فعال/غیرفعال)
```
PUT /plugins/{plugin_id}/toggle
```
نمونه داده درخواست:
```json
{
  "is_enabled": false
}
```

#### حذف پلاگین
```
DELETE /plugins/{plugin_id}
```

### مدیریت تنظیمات

#### دریافت تنظیمات سیستم
```
GET /settings/
```

#### به‌روزرسانی تنظیمات
```
PATCH /settings/
```
نمونه داده درخواست:
```json
{
  "auto_response": true,
  "notification_level": "important_only",
  "default_language": "fa"
}
```

### مدیریت لاگ‌ها

#### دریافت لاگ‌ها
```
GET /logs/
```
پارامترهای Query:
- `page`: شماره صفحه (پیش‌فرض: 1)
- `limit`: تعداد آیتم در هر صفحه (پیش‌فرض: 50)
- `level`: سطح لاگ (debug, info, warning, error, critical)
- `start_date`: تاریخ شروع
- `end_date`: تاریخ پایان
- `search`: جستجو در متن لاگ

## مدل‌های داده
مدل‌های داده مورد استفاده در API با استفاده از Pydantic تعریف شده‌اند. در ادامه مهم‌ترین مدل‌های داده معرفی می‌شوند:

### UserBase
```python
class UserBase(BaseModel):
    username: str
    email: EmailStr
    name: str
    role: str
    permissions: List[str]
```

### PluginBase
```python
class PluginBase(BaseModel):
    name: str
    version: str
    description: str
    author: str
    category: str
    is_enabled: bool = True
    is_system: bool = False
```

## کدهای وضعیت و خطاها
API از کدهای استاندارد HTTP برای نشان دادن وضعیت درخواست‌ها استفاده می‌کند:

- `200 OK`: درخواست موفقیت‌آمیز بود
- `201 Created`: منبع جدید با موفقیت ایجاد شد
- `400 Bad Request`: درخواست نامعتبر است
- `401 Unauthorized`: احراز هویت نشده یا توکن منقضی شده است
- `403 Forbidden`: دسترسی به منبع مورد نظر ممنوع است
- `404 Not Found`: منبع مورد نظر یافت نشد
- `500 Internal Server Error`: خطای داخلی سرور

در صورت بروز خطا، پاسخ به صورت زیر خواهد بود:

```json
{
  "detail": "پیام خطا"
}
```

## نمونه‌های استفاده
در این بخش، چند نمونه از استفاده API با Python ارائه شده است:

### احراز هویت و دریافت لیست کاربران
```python
import requests

# احراز هویت و دریافت توکن
response = requests.post(
    "http://localhost:8000/token",
    data={"username": "admin", "password": "admin_password"}
)
token = response.json()["access_token"]

# دریافت لیست کاربران
headers = {"Authorization": f"Bearer {token}"}
users_response = requests.get(
    "http://localhost:8000/users/",
    headers=headers
)

# نمایش نتیجه
users = users_response.json()
print(f"تعداد کاربران: {users['count']}")
for user in users['users']:
    print(f"- {user['username']}: {user['name']}")
```

### ایجاد پلاگین جدید
```python
import requests

# احراز هویت (مشابه قبل)
# ...

# ایجاد پلاگین جدید
plugin_data = {
    "name": "hello_world",
    "version": "1.0.0",
    "description": "پلاگین ساده سلام دنیا",
    "author": "کاربر تست",
    "category": "utility",
    "source_code": """
async def start(message):
    return {"response": "سلام دنیا!"}
"""
}

response = requests.post(
    "http://localhost:8000/plugins/",
    json=plugin_data,
    headers=headers
)

print(f"وضعیت: {response.status_code}")
print(f"پاسخ: {response.json()}")
```

## محدودیت‌ها و توصیه‌ها
- برای بهبود عملکرد، از پارامترهای `page` و `limit` در API‌های لیست استفاده کنید.
- توکن JWT بعد از 24 ساعت منقضی می‌شود و نیاز به دریافت توکن جدید وجود دارد.
- از rate limiting در API استفاده می‌شود، بنابراین از ارسال درخواست‌های متعدد در زمان کوتاه خودداری کنید.
- برای امنیت بیشتر، از HTTPS برای ارتباط با API استفاده کنید.

## منابع تکمیلی
- [مستندات FastAPI](https://fastapi.tiangolo.com/)
- [JWT.io](https://jwt.io/) - برای کدگشایی و اعتبارسنجی توکن‌های JWT
