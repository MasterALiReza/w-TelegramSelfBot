"""
پیاده‌سازی Redis برای کش، صف پیام و مدیریت وظایف
"""
import os
import json
from typing import Any, Optional
import redis
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()


class RedisManager:
    """
    مدیریت Redis برای کش، صف پیام و مدیریت وظایف
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """
        مقداردهی اولیه و اتصال به Redis
        """
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = None
        self.default_expiry = 3600  # یک ساعت پیش‌فرض
        self.connect()

    def connect(self) -> bool:
        """
        اتصال به سرور Redis

        Returns:
            bool: وضعیت اتصال
        """
        try:
            self.redis_client = redis.from_url(self.redis_url)
            return True
        except Exception as e:
            print(f"خطا در اتصال به Redis: {str(e)}")
            return False

    def set(self, key: str, value: Any, expiry: Optional[int] = None) -> bool:
        """
        ذخیره داده در Redis

        Args:
            key: کلید
            value: مقدار
            expiry: زمان انقضا (ثانیه)

        Returns:
            bool: وضعیت ذخیره‌سازی
        """
        if not self.redis_client:
            if not self.connect():
                return False

        try:
            # تبدیل مقادیر پیچیده به JSON
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value)

            # ذخیره داده با یا بدون زمان انقضا
            if expiry is not None:
                self.redis_client.setex(key, expiry, value)
            else:
                self.redis_client.set(key, value)
            return True
        except Exception as e:
            print(f"خطا در ذخیره داده در Redis: {str(e)}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        دریافت داده از Redis

        Args:
            key: کلید
            default: مقدار پیش‌فرض در صورت عدم وجود

        Returns:
            Any: داده دریافتی یا مقدار پیش‌فرض
        """
        if not self.redis_client:
            if not self.connect():
                return default

        try:
            value = self.redis_client.get(key)
            if value is None:
                return default

            # تلاش برای تبدیل به JSON
            try:
                return json.loads(value)
            except:
                # اگر JSON نبود، مقدار اصلی را برگردان
                return value.decode('utf-8') if isinstance(value, bytes) else value
        except Exception as e:
            print(f"خطا در دریافت داده از Redis: {str(e)}")
            return default

    def delete(self, key: str) -> bool:
        """
        حذف داده از Redis

        Args:
            key: کلید

        Returns:
            bool: وضعیت حذف
        """
        if not self.redis_client:
            if not self.connect():
                return False

        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"خطا در حذف داده از Redis: {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """
        بررسی وجود کلید در Redis

        Args:
            key: کلید

        Returns:
            bool: وضعیت وجود
        """
        if not self.redis_client:
            if not self.connect():
                return False

        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"خطا در بررسی وجود کلید در Redis: {str(e)}")
            return False

    def publish(self, channel: str, message: Any) -> bool:
        """
        انتشار پیام در یک کانال

        Args:
            channel: نام کانال
            message: پیام

        Returns:
            bool: وضعیت انتشار
        """
        if not self.redis_client:
            if not self.connect():
                return False

        try:
            # تبدیل پیام‌های پیچیده به JSON
            if isinstance(message, (dict, list, tuple)):
                message = json.dumps(message)

            self.redis_client.publish(channel, message)
            return True
        except Exception as e:
            print(f"خطا در انتشار پیام در Redis: {str(e)}")
            return False

    def enqueue(self, queue_name: str, data: Any) -> bool:
        """
        افزودن داده به صف

        Args:
            queue_name: نام صف
            data: داده

        Returns:
            bool: وضعیت افزودن
        """
        if not self.redis_client:
            if not self.connect():
                return False

        try:
            # تبدیل داده‌های پیچیده به JSON
            if isinstance(data, (dict, list, tuple)):
                data = json.dumps(data)

            self.redis_client.lpush(queue_name, data)
            return True
        except Exception as e:
            print(f"خطا در افزودن به صف Redis: {str(e)}")
            return False

    def dequeue(self, queue_name: str, timeout: int = 0) -> Optional[Any]:
        """
        دریافت و حذف داده از صف

        Args:
            queue_name: نام صف
            timeout: زمان انتظار (ثانیه)

        Returns:
            Optional[Any]: داده دریافتی یا None
        """
        if not self.redis_client:
            if not self.connect():
                return None

        try:
            # استفاده از BRPOP برای دریافت با timeout
            result = self.redis_client.brpop(queue_name, timeout)
            if result is None:
                return None

            _, value = result

            # تلاش برای تبدیل به JSON
            try:
                return json.loads(value)
            except:
                # اگر JSON نبود، مقدار اصلی را برگردان
                return value.decode('utf-8') if isinstance(value, bytes) else value
        except Exception as e:
            print(f"خطا در دریافت از صف Redis: {str(e)}")
            return None
