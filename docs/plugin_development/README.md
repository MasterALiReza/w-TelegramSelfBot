# راهنمای توسعه پلاگین سلف بات تلگرام

## مقدمه
سلف بات تلگرام از یک سیستم پلاگین قدرتمند پشتیبانی می‌کند که به شما امکان می‌دهد عملکرد بات را با نوشتن پلاگین‌های سفارشی گسترش دهید. این مستند، نحوه ایجاد، تست و استقرار پلاگین‌ها را توضیح می‌دهد.

## ساختار پلاگین
هر پلاگین از چندین قسمت اصلی تشکیل شده است:

1. **فایل اصلی پلاگین**: یک فایل Python که حاوی کد اصلی پلاگین است.
2. **فایل meta.json**: فایلی که اطلاعات توصیفی پلاگین را نگهداری می‌کند.
3. **فایل requirements.txt (اختیاری)**: لیست وابستگی‌های خارجی مورد نیاز پلاگین.

### مثال ساختار پوشه یک پلاگین
```
plugins/
└── example_plugin/
    ├── __init__.py
    ├── meta.json
    ├── requirements.txt
    └── main.py
```

### فایل meta.json
فایل meta.json حاوی متادیتای پلاگین است:

```json
{
  "name": "example_plugin",
  "version": "1.0.0",
  "description": "یک پلاگین نمونه",
  "author": "نام نویسنده",
  "author_email": "email@example.com",
  "requires_auth": false,
  "category": "utility",
  "priority": 10,
  "permissions": ["send_message", "read_message"],
  "commands": [
    {
      "name": "hello",
      "description": "ارسال سلام",
      "usage": ".hello [نام]"
    }
  ]
}
```

توضیح فیلدها:
- **name**: نام یکتای پلاگین (باید با نام پوشه مطابقت داشته باشد)
- **version**: نسخه پلاگین با فرمت Semantic Versioning
- **description**: توضیح مختصر در مورد کارکرد پلاگین
- **author**: نام نویسنده پلاگین
- **author_email**: ایمیل نویسنده (اختیاری)
- **requires_auth**: آیا پلاگین نیاز به احراز هویت دارد؟
- **category**: دسته‌بندی پلاگین (utility, security, fun, ai, admin, etc.)
- **priority**: اولویت اجرای پلاگین (عدد بزرگتر = اولویت بالاتر)
- **permissions**: مجوزهای مورد نیاز برای اجرای پلاگین
- **commands**: لیست دستورات قابل استفاده در پلاگین

## ساختار اصلی پلاگین

### فایل `__init__.py`
این فایل به سیستم پلاگین اجازه می‌دهد تا پلاگین شما را به عنوان یک ماژول Python بشناسد. این فایل معمولاً خالی است یا می‌تواند import‌های لازم را انجام دهد:

```python
from .main import start, stop, on_message, on_command
```

### فایل `main.py`
این فایل شامل منطق اصلی پلاگین است. روش‌های زیر باید در این فایل پیاده‌سازی شوند:

```python
from core.plugin_base import PluginBase
from pyrogram import types
from typing import Dict, Any, Optional, List, Union


class ExamplePlugin(PluginBase):
    """پلاگین نمونه برای نمایش ساختار پایه"""
    
    async def start(self) -> bool:
        """
        هنگام فعال‌سازی پلاگین فراخوانی می‌شود.
        
        Returns:
            bool: True در صورت موفقیت، False در صورت شکست
        """
        self.logger.info("پلاگین نمونه فعال شد")
        return True
    
    async def stop(self) -> bool:
        """
        هنگام غیرفعال‌سازی پلاگین فراخوانی می‌شود.
        
        Returns:
            bool: True در صورت موفقیت، False در صورت شکست
        """
        self.logger.info("پلاگین نمونه غیرفعال شد")
        return True
        
    async def on_message(self, message: types.Message) -> Optional[bool]:
        """
        هنگام دریافت پیام جدید فراخوانی می‌شود.
        
        Args:
            message: شیء پیام دریافت شده
            
        Returns:
            Optional[bool]: True اگر پیام پردازش شده و نباید به پلاگین‌های دیگر ارسال شود، 
                           False یا None اگر پردازش نشده و می‌تواند به پلاگین‌های دیگر ارسال شود
        """
        # این تابع پردازش هر پیام دریافتی را انجام می‌دهد
        self.logger.debug(f"پیام جدید دریافت شد: {message.text}")
        return None
    
    async def on_command(self, message: types.Message, command: str, args: List[str]) -> bool:
        """
        هنگام دریافت یک دستور فراخوانی می‌شود.
        
        Args:
            message: شیء پیام دریافت شده
            command: نام دستور (بدون پیشوند)
            args: آرگومان‌های دستور
            
        Returns:
            bool: True اگر دستور پردازش شده، False اگر دستور ناشناخته است
        """
        if command == "hello":
            name = args[0] if args else "دوست عزیز"
            await message.reply(f"سلام {name}!")
            return True
        return False
    
    async def on_callback_query(self, callback_query: types.CallbackQuery) -> bool:
        """
        هنگام دریافت callback query (مثلاً از دکمه‌های inline) فراخوانی می‌شود.
        
        Args:
            callback_query: شیء callback query
            
        Returns:
            bool: True اگر query پردازش شده، False اگر پردازش نشده
        """
        return False
    
    async def get_settings(self) -> Dict[str, Any]:
        """
        تنظیمات پلاگین را برمی‌گرداند.
        
        Returns:
            Dict[str, Any]: تنظیمات پلاگین
        """
        return {
            "example_setting": "مقدار پیش‌فرض",
            "enabled_feature": True
        }
    
    async def set_settings(self, settings: Dict[str, Any]) -> bool:
        """
        تنظیمات پلاگین را به‌روزرسانی می‌کند.
        
        Args:
            settings: تنظیمات جدید
            
        Returns:
            bool: True در صورت موفقیت، False در صورت شکست
        """
        # اعمال تنظیمات جدید
        self.logger.info(f"تنظیمات جدید دریافت شد: {settings}")
        return True
```

## استفاده از API‌های سلف بات
پلاگین‌ها می‌توانند به API‌های مختلف سلف بات دسترسی داشته باشند. در ادامه مهم‌ترین API‌ها معرفی می‌شوند:

### دسترسی به دیتابیس
```python
async def save_data(self, key: str, value: Any) -> bool:
    """ذخیره داده در دیتابیس"""
    return await self.db.insert(
        "plugin_data",
        {"plugin_name": self.name, "key": key, "value": value}
    )

async def get_data(self, key: str) -> Any:
    """بازیابی داده از دیتابیس"""
    result = await self.db.fetch_one(
        "SELECT value FROM plugin_data WHERE plugin_name = $1 AND key = $2",
        (self.name, key)
    )
    return result["value"] if result else None
```

### ارسال پیام
```python
async def send_message_to_user(self, user_id: int, text: str) -> bool:
    """ارسال پیام به یک کاربر"""
    try:
        await self.client.send_message(user_id, text)
        return True
    except Exception as e:
        self.logger.error(f"خطا در ارسال پیام: {str(e)}")
        return False
```

### دسترسی به متغیرهای محیطی
```python
def get_api_key(self) -> str:
    """دریافت کلید API از تنظیمات"""
    return self.config.get("API_KEY", "")
```

### استفاده از Redis برای کش
```python
async def cache_data(self, key: str, value: Any, ttl: int = 3600) -> bool:
    """ذخیره داده در کش Redis"""
    full_key = f"plugin:{self.name}:{key}"
    await self.redis.set(full_key, value, ttl)
    return True

async def get_cached_data(self, key: str) -> Any:
    """بازیابی داده از کش Redis"""
    full_key = f"plugin:{self.name}:{key}"
    return await self.redis.get(full_key)
```

## رویدادهای قابل استفاده
پلاگین‌ها می‌توانند به رویدادهای مختلف واکنش نشان دهند:

1. **on_message**: هنگام دریافت هر پیام
2. **on_command**: هنگام دریافت یک دستور (پیام شروع شده با یک پیشوند خاص)
3. **on_callback_query**: هنگام دریافت callback query از دکمه‌های inline
4. **on_chat_member_updated**: هنگام تغییر در وضعیت اعضای گروه
5. **on_user_status**: هنگام تغییر وضعیت کاربر (آنلاین، آفلاین، آخرین بازدید)
6. **on_media_received**: هنگام دریافت رسانه (عکس، ویدیو، فایل)

## تست پلاگین
برای تست پلاگین خود، می‌توانید از ماژول تست ارائه شده استفاده کنید:

```python
# tests/plugins/test_example_plugin.py
import pytest
from plugins.example_plugin.main import ExamplePlugin
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def plugin():
    """ایجاد نمونه پلاگین برای تست"""
    plugin = ExamplePlugin()
    plugin.logger = MagicMock()
    plugin.db = AsyncMock()
    plugin.client = AsyncMock()
    plugin.redis = AsyncMock()
    plugin.config = {}
    return plugin

@pytest.mark.asyncio
async def test_start(plugin):
    """تست متد start"""
    result = await plugin.start()
    assert result is True
    plugin.logger.info.assert_called_once()

@pytest.mark.asyncio
async def test_hello_command(plugin):
    """تست دستور hello"""
    # ایجاد mock برای پیام
    message = AsyncMock()
    # تست با آرگومان
    result = await plugin.on_command(message, "hello", ["کاربر"])
    assert result is True
    message.reply.assert_called_once_with("سلام کاربر!")
    
    # تست بدون آرگومان
    message.reset_mock()
    result = await plugin.on_command(message, "hello", [])
    assert result is True
    message.reply.assert_called_once_with("سلام دوست عزیز!")
```

## بهترین شیوه‌های توسعه پلاگین

### 1. مدیریت خطا
همیشه خطاها را به درستی مدیریت کنید تا پلاگین شما باعث خرابی کل سیستم نشود:

```python
async def some_risky_operation(self):
    try:
        # عملیات پرخطر
        result = await self.api_call()
        return result
    except Exception as e:
        self.logger.error(f"خطا در عملیات: {str(e)}")
        return None
```

### 2. لاگ گذاری مناسب
از سیستم لاگ برای ثبت رویدادها و دیباگ استفاده کنید:

```python
# سطوح مختلف لاگ
self.logger.debug("پیام دیباگ با جزئیات بیشتر")
self.logger.info("اطلاعات عمومی")
self.logger.warning("هشدار برای مشکلات بالقوه")
self.logger.error("خطاهای مهم")
self.logger.critical("خطاهای بحرانی که باعث توقف سیستم می‌شوند")
```

### 3. بهینه‌سازی عملکرد
برای بهبود عملکرد، از تکنیک‌های زیر استفاده کنید:
- از async/await برای عملیات I/O استفاده کنید
- از کش برای داده‌های پرکاربرد استفاده کنید
- از عملیات سنگین و طولانی در thread جداگانه استفاده کنید

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# برای عملیات CPU-bound
async def process_large_data(self, data):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool, self._cpu_intensive_task, data
        )
    return result

def _cpu_intensive_task(self, data):
    # پردازش داده‌های بزرگ
    return processed_data
```

### 4. امنیت
نکات امنیتی مهم:
- از تزریق SQL جلوگیری کنید (از prepared statements استفاده کنید)
- ورودی‌های کاربر را اعتبارسنجی کنید
- از رمزنگاری برای داده‌های حساس استفاده کنید
- از hardcode کردن اطلاعات حساس خودداری کنید

### 5. مصرف منابع
به مصرف منابع توجه کنید:
- از ذخیره مقادیر زیاد داده در حافظه خودداری کنید
- منابع باز شده (مانند اتصالات فایل یا شبکه) را ببندید
- از ایجاد thread یا process بیش از حد خودداری کنید

## توزیع پلاگین
برای توزیع پلاگین خود، آن را به صورت یک بسته فشرده (zip) با ساختار زیر در بیاورید:

```
example_plugin.zip
├── __init__.py
├── main.py
├── meta.json
└── requirements.txt
```

## مثال‌های پلاگین

### 1. پلاگین ترجمه متن
```python
# plugins/translator/main.py
from core.plugin_base import PluginBase
from pyrogram import types
import aiohttp

class TranslatorPlugin(PluginBase):
    """پلاگین ترجمه متن با استفاده از Google Translate API"""
    
    async def start(self) -> bool:
        self.logger.info("پلاگین مترجم فعال شد")
        self.session = aiohttp.ClientSession()
        return True
    
    async def stop(self) -> bool:
        await self.session.close()
        self.logger.info("پلاگین مترجم غیرفعال شد")
        return True
        
    async def on_command(self, message: types.Message, command: str, args: list) -> bool:
        if command != "translate":
            return False
            
        if len(args) < 2:
            await message.reply("استفاده: .translate [زبان مقصد] [متن]")
            return True
            
        target_lang = args[0]
        text = " ".join(args[1:])
        
        translated = await self._translate_text(text, target_lang)
        if translated:
            await message.reply(f"**ترجمه به {target_lang}**:\n{translated}")
        else:
            await message.reply("خطا در ترجمه متن.")
        return True
        
    async def _translate_text(self, text: str, target_lang: str) -> str:
        """ترجمه متن با استفاده از Google Translate API"""
        try:
            async with self.session.get(
                "https://translate.googleapis.com/translate_a/single",
                params={
                    "client": "gtx",
                    "sl": "auto",
                    "tl": target_lang,
                    "dt": "t",
                    "q": text
                }
            ) as response:
                if response.status != 200:
                    self.logger.error(f"خطا در API ترجمه: {response.status}")
                    return None
                    
                data = await response.json()
                translated = "".join(item[0] for item in data[0] if item[0])
                return translated
                
        except Exception as e:
            self.logger.error(f"خطا در ترجمه: {str(e)}")
            return None
```

### 2. پلاگین مدیریت گروه
```python
# plugins/group_manager/main.py
from core.plugin_base import PluginBase
from pyrogram import types
from typing import Dict, Any, List
import asyncio

class GroupManagerPlugin(PluginBase):
    """پلاگین مدیریت گروه با قابلیت‌های ضد اسپم و مدیریت کاربران"""
    
    async def start(self) -> bool:
        self.logger.info("پلاگین مدیریت گروه فعال شد")
        self.spam_detection = {}  # نگهداری وضعیت اسپم برای هر گروه
        self.user_warnings = {}  # هشدارهای کاربران
        return True
    
    async def on_message(self, message: types.Message) -> None:
        # بررسی وضعیت اسپم فقط در گروه‌ها
        if message.chat.type in ["group", "supergroup"]:
            await self._check_spam(message)
        return None
    
    async def on_command(self, message: types.Message, command: str, args: List[str]) -> bool:
        # دستورات مدیریت گروه
        if command == "warn":
            return await self._warn_user(message, args)
        elif command == "ban":
            return await self._ban_user(message, args)
        elif command == "unban":
            return await self._unban_user(message, args)
        elif command == "mute":
            return await self._mute_user(message, args)
        return False
    
    async def _check_spam(self, message: types.Message) -> None:
        """بررسی پیام‌ها برای شناسایی اسپم"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # ایجاد ساختار داده برای چت اگر وجود ندارد
        if chat_id not in self.spam_detection:
            self.spam_detection[chat_id] = {}
        
        # ایجاد ساختار داده برای کاربر اگر وجود ندارد
        if user_id not in self.spam_detection[chat_id]:
            self.spam_detection[chat_id][user_id] = {
                "messages": [],
                "last_warning": 0
            }
        
        # افزودن پیام جدید و حذف پیام‌های قدیمی‌تر از 10 ثانیه
        current_time = message.date
        self.spam_detection[chat_id][user_id]["messages"].append(current_time)
        self.spam_detection[chat_id][user_id]["messages"] = [
            msg_time for msg_time in self.spam_detection[chat_id][user_id]["messages"]
            if current_time - msg_time < 10
        ]
        
        # بررسی تعداد پیام‌ها در 10 ثانیه
        if len(self.spam_detection[chat_id][user_id]["messages"]) >= 5:
            # اگر آخرین اخطار بیش از 30 ثانیه پیش بوده
            if current_time - self.spam_detection[chat_id][user_id]["last_warning"] > 30:
                self.spam_detection[chat_id][user_id]["last_warning"] = current_time
                try:
                    await message.reply(
                        f"**هشدار اسپم** به کاربر {message.from_user.mention}\n"
                        f"لطفاً سرعت ارسال پیام خود را کاهش دهید."
                    )
                except Exception as e:
                    self.logger.error(f"خطا در ارسال هشدار اسپم: {str(e)}")
    
    async def _warn_user(self, message: types.Message, args: List[str]) -> bool:
        """هشدار به کاربر"""
        if not message.reply_to_message:
            await message.reply("برای هشدار دادن، روی پیام کاربر ریپلای کنید.")
            return True
        
        # بررسی دسترسی‌ها
        if not await self._check_admin_rights(message):
            await message.reply("شما دسترسی لازم برای این عمل را ندارید.")
            return True
        
        target_user = message.reply_to_message.from_user
        chat_id = message.chat.id
        
        # ایجاد ساختار داده هشدارها
        if chat_id not in self.user_warnings:
            self.user_warnings[chat_id] = {}
        
        if target_user.id not in self.user_warnings[chat_id]:
            self.user_warnings[chat_id][target_user.id] = 0
        
        # افزایش تعداد هشدارها
        self.user_warnings[chat_id][target_user.id] += 1
        warnings = self.user_warnings[chat_id][target_user.id]
        
        reason = " ".join(args) if args else "بدون دلیل"
        await message.reply(
            f"کاربر {target_user.mention} هشدار دریافت کرد.\n"
            f"تعداد هشدارها: {warnings}/3\n"
            f"دلیل: {reason}"
        )
        
        # اگر به 3 هشدار رسید، کاربر را بن کنید
        if warnings >= 3:
            try:
                await message.chat.ban_member(target_user.id)
                await message.reply(
                    f"کاربر {target_user.mention} به دلیل دریافت 3 هشدار از گروه اخراج شد."
                )
                # پاک کردن هشدارها پس از بن
                self.user_warnings[chat_id][target_user.id] = 0
            except Exception as e:
                self.logger.error(f"خطا در بن کردن کاربر: {str(e)}")
                await message.reply("خطا در اخراج کاربر. لطفاً دسترسی‌های بات را بررسی کنید.")
        
        return True
    
    async def _check_admin_rights(self, message: types.Message) -> bool:
        """بررسی دسترسی‌های ادمین برای کاربر"""
        try:
            user = await message.chat.get_member(message.from_user.id)
            return user.status in ["creator", "administrator"]
        except Exception as e:
            self.logger.error(f"خطا در بررسی دسترسی‌ها: {str(e)}")
            return False
```

## سوالات متداول

### چگونه می‌توانم از API‌های خارجی استفاده کنم؟
وابستگی‌های مورد نیاز را در فایل requirements.txt اضافه کنید و سپس از آن‌ها در کد خود استفاده کنید. توصیه می‌کنیم از کتابخانه‌های async مانند aiohttp برای درخواست‌های HTTP استفاده کنید.

### چگونه می‌توانم داده‌های پلاگین خود را ذخیره کنم؟
از متد‌های دیتابیس ارائه شده در کلاس پایه پلاگین استفاده کنید. برای ذخیره‌سازی موقت می‌توانید از Redis استفاده کنید و برای ذخیره‌سازی دائمی از PostgreSQL.

### آیا می‌توانم از مدل‌های هوش مصنوعی در پلاگین خود استفاده کنم؟
بله، سلف بات تلگرام از اتصال به OpenAI، Claude و Llama پشتیبانی می‌کند. برای استفاده از این قابلیت‌ها به مستندات AI API مراجعه کنید.

### چگونه می‌توانم با پلاگین‌های دیگر تعامل داشته باشم؟
از سیستم رویداد برای ارتباط بین پلاگین‌ها استفاده کنید:

```python
# انتشار یک رویداد
await self.event_manager.emit(
    "custom_event", 
    {"data": "مقدار داده", "source": self.name}
)

# گوش دادن به یک رویداد
@self.event_manager.on("custom_event")
async def handle_custom_event(self, data):
    self.logger.info(f"رویداد دریافت شد: {data}")
```

### پلاگین من خطای ImportError می‌دهد، چه کار کنم؟
مطمئن شوید که تمام وابستگی‌های مورد نیاز را در فایل requirements.txt اضافه کرده‌اید. همچنین می‌توانید از قسمت محیط مجازی Python برای نصب وابستگی‌ها استفاده کنید.
