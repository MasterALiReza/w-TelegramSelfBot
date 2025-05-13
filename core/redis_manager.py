"""
ماژول مدیریت کش Redis برای سلف بات تلگرام
"""
import json
import logging
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisManager:
    """
    کلاس مدیریت اتصال و عملیات Redis
    از الگوی طراحی Singleton برای اطمینان از وجود فقط یک نمونه استفاده می‌کند
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        """پیاده‌سازی الگوی Singleton"""
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0,
                 password: Optional[str] = None, prefix: str = 'selfbot:'):
        """
        مقداردهی اولیه

        Args:
            host: هاست Redis
            port: پورت Redis
            db: شماره دیتابیس Redis
            password: رمز عبور Redis (اختیاری)
            prefix: پیشوند کلیدهای Redis
        """
        # اگر قبلاً مقداردهی شده، خروج
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.prefix = prefix
        self.redis = None
        self._pubsub = None
        self._active_subscriptions = {}
        self._running_tasks = []

    async def connect(self) -> bool:
        """
        اتصال به سرور Redis

        Returns:
            bool: وضعیت اتصال
        """
        try:
            connection_url = f"redis://{self.host}:{self.port}/{self.db}"
            if self.password:
                connection_url = f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"

            logger.info(f"در حال اتصال به Redis: {self.host}:{self.port} DB:{self.db}")
            self.redis = redis.from_url(connection_url)

            # تست اتصال
            await self.redis.ping()

            # ایجاد PubSub برای کانال‌های اشتراکی
            self._pubsub = self.redis.pubsub()

            logger.info("اتصال به Redis با موفقیت برقرار شد")
            return True
        except Exception as e:
            logger.error(f"خطا در اتصال به Redis: {str(e)}")
            return False

    async def disconnect(self) -> None:
        """
        قطع اتصال از سرور Redis
        """
        try:
            # توقف تمام وظایف در حال اجرا
            for task in self._running_tasks:
                if not task.done():
                    task.cancel()

            # لغو اشتراک‌ها
            if self._pubsub:
                await self._pubsub.unsubscribe()
                await self._pubsub.close()

            # بستن اتصال
            if self.redis:
                await self.redis.close()

            logger.info("اتصال Redis با موفقیت بسته شد")
        except Exception as e:
            logger.error(f"خطا در بستن اتصال Redis: {str(e)}")

    def _build_key(self, key: str) -> str:
        """
        ایجاد کلید با پیشوند

        Args:
            key: کلید خام

        Returns:
            str: کلید با پیشوند
        """
        return f"{self.prefix}{key}"

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        ذخیره مقدار در Redis

        Args:
            key: کلید
            value: مقدار (در صورت نیاز به json تبدیل می‌شود)
            expire: زمان انقضا به ثانیه (اختیاری)

        Returns:
            bool: وضعیت عملیات
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return False

            # تبدیل مقادیر پیچیده به json
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(value, ensure_ascii=False)

            # ذخیره با پیشوند کلید
            full_key = self._build_key(key)
            await self.redis.set(full_key, value)

            # تنظیم زمان انقضا
            if expire is not None:
                await self.redis.expire(full_key, expire)

            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره مقدار در Redis: {str(e)}")
            return False

    async def get(self, key: str, default: Any = None, parse_json: bool = True) -> Any:
        """
        دریافت مقدار از Redis

        Args:
            key: کلید
            default: مقدار پیش‌فرض در صورت عدم وجود
            parse_json: تبدیل json به دیکشنری

        Returns:
            Any: مقدار ذخیره شده یا مقدار پیش‌فرض
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return default

            # دریافت با پیشوند کلید
            full_key = self._build_key(key)
            value = await self.redis.get(full_key)

            if value is None:
                return default

            # تبدیل از bytes به str
            if isinstance(value, bytes):
                value = value.decode('utf-8')

            # تبدیل از json در صورت نیاز
            if parse_json and value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value

            return value
        except Exception as e:
            logger.error(f"خطا در دریافت مقدار از Redis: {str(e)}")
            return default

    async def delete(self, key: str) -> bool:
        """
        حذف کلید از Redis

        Args:
            key: کلید

        Returns:
            bool: وضعیت عملیات
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return False

            # حذف با پیشوند کلید
            full_key = self._build_key(key)
            await self.redis.delete(full_key)
            return True
        except Exception as e:
            logger.error(f"خطا در حذف کلید از Redis: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """
        بررسی وجود کلید در Redis

        Args:
            key: کلید

        Returns:
            bool: آیا کلید وجود دارد
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return False

            # بررسی با پیشوند کلید
            full_key = self._build_key(key)
            return await self.redis.exists(full_key) > 0
        except Exception as e:
            logger.error(f"خطا در بررسی وجود کلید در Redis: {str(e)}")
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        """
        تنظیم زمان انقضا برای کلید

        Args:
            key: کلید
            seconds: زمان انقضا به ثانیه

        Returns:
            bool: وضعیت عملیات
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return False

            # تنظیم با پیشوند کلید
            full_key = self._build_key(key)
            await self.redis.expire(full_key, seconds)
            return True
        except Exception as e:
            logger.error(f"خطا در تنظیم زمان انقضا برای کلید: {str(e)}")
            return False

    async def ttl(self, key: str) -> int:
        """
        دریافت زمان باقی‌مانده تا انقضای کلید

        Args:
            key: کلید

        Returns:
            int: زمان باقی‌مانده به ثانیه (-2 برای عدم وجود، -1 برای بدون انقضا)
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return -2

            # دریافت با پیشوند کلید
            full_key = self._build_key(key)
            return await self.redis.ttl(full_key)
        except Exception as e:
            logger.error(f"خطا در دریافت زمان انقضای کلید: {str(e)}")
            return -2

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        افزایش مقدار عددی کلید

        Args:
            key: کلید
            amount: مقدار افزایش

        Returns:
            int: مقدار جدید
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return 0

            # افزایش با پیشوند کلید
            full_key = self._build_key(key)
            return await self.redis.incrby(full_key, amount)
        except Exception as e:
            logger.error(f"خطا در افزایش مقدار کلید: {str(e)}")
            return 0

    async def decr(self, key: str, amount: int = 1) -> int:
        """
        کاهش مقدار عددی کلید

        Args:
            key: کلید
            amount: مقدار کاهش

        Returns:
            int: مقدار جدید
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return 0

            # کاهش با پیشوند کلید
            full_key = self._build_key(key)
            return await self.redis.decrby(full_key, amount)
        except Exception as e:
            logger.error(f"خطا در کاهش مقدار کلید: {str(e)}")
            return 0

    async def hset(self, key: str, field: str, value: Any) -> bool:
        """
        ذخیره مقدار در hash

        Args:
            key: کلید hash
            field: فیلد hash
            value: مقدار (در صورت نیاز به json تبدیل می‌شود)

        Returns:
            bool: وضعیت عملیات
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return False

            # تبدیل مقادیر پیچیده به json
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(value, ensure_ascii=False)

            # ذخیره با پیشوند کلید
            full_key = self._build_key(key)
            await self.redis.hset(full_key, field, value)
            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره مقدار در hash: {str(e)}")
            return False

    async def hget(self, key: str, field: str, default: Any = None, parse_json: bool = True) -> Any:
        """
        دریافت مقدار از hash

        Args:
            key: کلید hash
            field: فیلد hash
            default: مقدار پیش‌فرض در صورت عدم وجود
            parse_json: تبدیل json به دیکشنری

        Returns:
            Any: مقدار ذخیره شده یا مقدار پیش‌فرض
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return default

            # دریافت با پیشوند کلید
            full_key = self._build_key(key)
            value = await self.redis.hget(full_key, field)

            if value is None:
                return default

            # تبدیل از bytes به str
            if isinstance(value, bytes):
                value = value.decode('utf-8')

            # تبدیل از json در صورت نیاز
            if parse_json and value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value

            return value
        except Exception as e:
            logger.error(f"خطا در دریافت مقدار از hash: {str(e)}")
            return default

    async def hdel(self, key: str, field: str) -> bool:
        """
        حذف فیلد از hash

        Args:
            key: کلید hash
            field: فیلد hash

        Returns:
            bool: وضعیت عملیات
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return False

            # حذف با پیشوند کلید
            full_key = self._build_key(key)
            await self.redis.hdel(full_key, field)
            return True
        except Exception as e:
            logger.error(f"خطا در حذف فیلد از hash: {str(e)}")
            return False

    async def hgetall(self, key: str, parse_json: bool = True) -> Dict[str, Any]:
        """
        دریافت تمام مقادیر hash

        Args:
            key: کلید hash
            parse_json: تبدیل json به دیکشنری

        Returns:
            Dict[str, Any]: دیکشنری مقادیر
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return {}

            # دریافت با پیشوند کلید
            full_key = self._build_key(key)
            values = await self.redis.hgetall(full_key)

            result = {}

            # تبدیل مقادیر
            for k, v in values.items():
                k_str = k.decode('utf-8') if isinstance(k, bytes) else k
                v_str = v.decode('utf-8') if isinstance(v, bytes) else v

                # تبدیل از json در صورت نیاز
                if parse_json and v_str:
                    try:
                        result[k_str] = json.loads(v_str)
                    except json.JSONDecodeError:
                        result[k_str] = v_str
                else:
                    result[k_str] = v_str

            return result
        except Exception as e:
            logger.error(f"خطا در دریافت تمام مقادیر hash: {str(e)}")
            return {}

    async def publish(self, channel: str, message: Any) -> int:
        """
        انتشار پیام در کانال

        Args:
            channel: نام کانال
            message: پیام (در صورت نیاز به json تبدیل می‌شود)

        Returns:
            int: تعداد دریافت‌کنندگان
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return 0

            # تبدیل مقادیر پیچیده به json
            if not isinstance(message, (str, bytes, int, float)):
                message = json.dumps(message, ensure_ascii=False)

            # انتشار با پیشوند کانال
            full_channel = self._build_key(channel)
            return await self.redis.publish(full_channel, message)
        except Exception as e:
            logger.error(f"خطا در انتشار پیام در کانال: {str(e)}")
            return 0

    async def subscribe(self, channel: str, handler: callable) -> bool:
        """
        اشتراک در کانال

        Args:
            channel: نام کانال
            handler: تابع پردازش پیام

        Returns:
            bool: وضعیت عملیات
        """
        try:
            if self.redis is None or self._pubsub is None:
                logger.error("اتصال Redis برقرار نیست")
                return False

            # اشتراک با پیشوند کانال
            full_channel = self._build_key(channel)
            await self._pubsub.subscribe(full_channel)

            # ذخیره handler
            self._active_subscriptions[full_channel] = handler

            # ایجاد وظیفه دریافت پیام در صورت عدم وجود
            await self._ensure_subscription_worker()

            return True
        except Exception as e:
            logger.error(f"خطا در اشتراک کانال: {str(e)}")
            return False

    async def unsubscribe(self, channel: str) -> bool:
        """
        لغو اشتراک از کانال

        Args:
            channel: نام کانال

        Returns:
            bool: وضعیت عملیات
        """
        try:
            if self.redis is None or self._pubsub is None:
                logger.error("اتصال Redis برقرار نیست")
                return False

            # لغو اشتراک با پیشوند کانال
            full_channel = self._build_key(channel)
            await self._pubsub.unsubscribe(full_channel)

            # حذف handler
            if full_channel in self._active_subscriptions:
                del self._active_subscriptions[full_channel]

            return True
        except Exception as e:
            logger.error(f"خطا در لغو اشتراک کانال: {str(e)}")
            return False

    async def _ensure_subscription_worker(self) -> None:
        """
        ایجاد وظیفه پردازش پیام‌های اشتراکی در صورت عدم وجود
        """
        # بررسی وجود وظیفه فعال
        for task in self._running_tasks:
            if not task.done():
                return

        # ایجاد وظیفه جدید
        task = asyncio.create_task(self._subscription_worker())
        self._running_tasks.append(task)

    async def _subscription_worker(self) -> None:
        """
        وظیفه پردازش پیام‌های اشتراکی
        """
        try:
            if self._pubsub is None:
                return

            logger.info("آغاز وظیفه پردازش پیام‌های اشتراکی Redis")

            while True:
                # دریافت پیام
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

                if message is None:
                    await asyncio.sleep(0.01)  # کاهش مصرف CPU
                    continue

                # پردازش پیام
                try:
                    channel = message.get('channel', b'').decode('utf-8')
                    data = message.get('data', b'')

                    # تبدیل data به str
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')

                    # فراخوانی handler
                    if channel in self._active_subscriptions:
                        handler = self._active_subscriptions[channel]

                        # تبدیل json در صورت امکان
                        try:
                            data = json.loads(data)
                        except json.JSONDecodeError:
                            pass

                        # فراخوانی handler به صورت asyncio
                        asyncio.create_task(handler(channel, data))
                except Exception as inner_e:
                    logger.error(f"خطا در پردازش پیام اشتراکی: {str(inner_e)}")

        except asyncio.CancelledError:
            logger.info("توقف وظیفه پردازش پیام‌های اشتراکی Redis")
        except Exception as e:
            logger.error(f"خطا در وظیفه پردازش پیام‌های اشتراکی Redis: {str(e)}")

    # --- متدهای مدیریت کش اطلاعات --- #

    async def cache_set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        ذخیره مقدار در کش با زمان انقضا

        Args:
            key: کلید
            value: مقدار
            expire: زمان انقضا به ثانیه (پیش‌فرض 1 ساعت)

        Returns:
            bool: وضعیت عملیات
        """
        cache_key = f"cache:{key}"
        return await self.set(cache_key, value, expire)

    async def cache_get(self, key: str, default: Any = None) -> Any:
        """
        دریافت مقدار از کش

        Args:
            key: کلید
            default: مقدار پیش‌فرض در صورت عدم وجود

        Returns:
            Any: مقدار ذخیره شده یا مقدار پیش‌فرض
        """
        cache_key = f"cache:{key}"
        return await self.get(cache_key, default)

    async def cache_delete(self, key: str) -> bool:
        """
        حذف مقدار از کش

        Args:
            key: کلید

        Returns:
            bool: وضعیت عملیات
        """
        cache_key = f"cache:{key}"
        return await self.delete(cache_key)

    # --- متدهای قفل توزیع شده --- #

    async def acquire_lock(self, lock_name: str, timeout: int = 10, expire: int = 30) -> bool:
        """
        گرفتن قفل توزیع شده

        Args:
            lock_name: نام قفل
            timeout: زمان انتظار برای قفل (ثانیه)
            expire: زمان انقضای قفل (ثانیه)

        Returns:
            bool: آیا قفل گرفته شد
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return False

            lock_key = self._build_key(f"lock:{lock_name}")
            lock_id = f"{datetime.now().timestamp()}"

            end_time = datetime.now() + timedelta(seconds=timeout)

            while datetime.now() < end_time:
                # تلاش برای گرفتن قفل
                if await self.redis.set(lock_key, lock_id, nx=True, ex=expire):
                    return True

                # انتظار کوتاه
                await asyncio.sleep(0.1)

            return False
        except Exception as e:
            logger.error(f"خطا در گرفتن قفل: {str(e)}")
            return False

    async def release_lock(self, lock_name: str) -> bool:
        """
        آزاد کردن قفل توزیع شده

        Args:
            lock_name: نام قفل

        Returns:
            bool: آیا قفل آزاد شد
        """
        try:
            if self.redis is None:
                logger.error("اتصال Redis برقرار نیست")
                return False

            lock_key = self._build_key(f"lock:{lock_name}")
            await self.redis.delete(lock_key)
            return True
        except Exception as e:
            logger.error(f"خطا در آزاد کردن قفل: {str(e)}")
            return False


# دریافت نمونه‌ی سینگلتون RedisManager
def get_redis_manager(host: str = 'localhost', port: int = 6379, db: int = 0,
                     password: Optional[str] = None, prefix: str = 'selfbot:') -> RedisManager:
    """
    دریافت نمونه سینگلتون RedisManager

    Args:
        host: هاست Redis
        port: پورت Redis
        db: شماره دیتابیس Redis
        password: رمز عبور Redis (اختیاری)
        prefix: پیشوند کلیدهای Redis

    Returns:
        RedisManager: نمونه سینگلتون RedisManager
    """
    return RedisManager(host, port, db, password, prefix)

async def initialize_redis(host: str = 'localhost', port: int = 6379, db: int = 0,
                          password: Optional[str] = None, prefix: str = 'selfbot:') -> RedisManager:
    """
    راه‌اندازی و اتصال به Redis

    Args:
        host: هاست Redis
        port: پورت Redis
        db: شماره دیتابیس Redis
        password: رمز عبور Redis (اختیاری)
        prefix: پیشوند کلیدهای Redis

    Returns:
        RedisManager: شیء مدیریت Redis
    """
    global redis_manager

    if redis_manager is None:
        redis_manager = RedisManager(host, port, db, password, prefix)

    connected = await redis_manager.connect()
    if not connected:
        logger.error("خطا در اتصال به Redis")

    return redis_manager
