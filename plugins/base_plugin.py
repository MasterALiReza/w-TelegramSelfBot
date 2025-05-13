"""
کلاس پایه برای پلاگین‌ها
"""
import asyncio
import inspect
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from abc import ABC, abstractmethod
import json
import yaml

from core.client import TelegramClient
from core.database.sql import PostgreSQLDatabase
from core.database.redis import RedisManager
from core.event_handler import EventHandler, EventType
from core.scheduler import Scheduler
from core.localization import Localization, _

# تنظیم سیستم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/plugins.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BasePlugin(ABC):
    """
    کلاس پایه برای تمام پلاگین‌ها
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        self.description = ""
        self.author = ""
        self.category = "general"
        self.commands = []
        self.event_handler = EventHandler()
        self.db = PostgreSQLDatabase()
        self.redis = RedisManager()
        self.scheduler = Scheduler()
        self.localization = Localization()
        self.config = {}
        self.is_enabled = True
        self._registered_handlers = {}

    def set_metadata(self, name: str, version: str, description: str, author: str, category: str):
        """
        تنظیم متادیتای پلاگین

        Args:
            name: نام پلاگین
            version: نسخه پلاگین
            description: توضیحات پلاگین
            author: نویسنده پلاگین
            category: دسته‌بندی پلاگین
        """
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.category = category

    def load_config(self, config: Dict[str, Any]):
        """
        بارگذاری تنظیمات پلاگین

        Args:
            config: تنظیمات
        """
        self.config = config or {}

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        دریافت یک تنظیم

        Args:
            key: کلید تنظیم
            default: مقدار پیش‌فرض

        Returns:
            Any: مقدار تنظیم
        """
        return self.config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """
        تنظیم یک تنظیم

        Args:
            key: کلید تنظیم
            value: مقدار تنظیم
        """
        self.config[key] = value

    def save_config(self, path: Optional[str] = None) -> bool:
        """
        ذخیره تنظیمات پلاگین

        Args:
            path: مسیر فایل (اختیاری)

        Returns:
            bool: وضعیت ذخیره‌سازی
        """
        try:
            if not path:
                path = os.path.join("config", "plugins", f"{self.name}.yml")

            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)

            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره تنظیمات پلاگین {self.name}: {str(e)}")
            return False

    @abstractmethod
    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """

    @abstractmethod
    async def cleanup(self) -> bool:
        """
        پاکسازی منابع پلاگین

        Returns:
            bool: وضعیت پاکسازی
        """

    def register_command(self, name: str, handler: Callable, description: str = "", usage: str = "") \
        \ \
        \ \
        : \
        """
        ثبت یک دستور

        Args:
            name: نام دستور
            handler: تابع اجرا کننده دستور
            description: توضیحات دستور
            usage: نحوه استفاده از دستور
        """
        self.commands.append({
            'name': name,
            'handler': handler,
            'description': description,
            'usage': usage
        })

    def register_event_handler(self, event_type: str, handler: Callable, filters: Optional[Dict[str, Any]] = None) \
        \ \
        \ \
        : \
        """
        ثبت هندلر رویداد

        Args:
            event_type: نوع رویداد
            handler: تابع اجرا کننده
            filters: فیلترها
        """
        handler_id = f"{self.name}_{event_type}_{len(self._registered_handlers)}"
        self.event_handler.register_handler(event_type, handler, filters)
        self._registered_handlers[handler_id] = {
            'event_type': event_type,
            'handler': handler,
            'filters': filters
        }

    def on_message(self, filters: Optional[Dict[str, Any]] = None):
        """
        دکوراتور برای ثبت هندلر پیام

        Args:
            filters: فیلترها

        Returns:
            Callable: دکوراتور
        """
        def decorator(func):
            self.register_event_handler(EventType.MESSAGE, func, filters)
            return func
        return decorator

    def on_edited_message(self, filters: Optional[Dict[str, Any]] = None):
        """
        دکوراتور برای ثبت هندلر پیام ویرایش شده

        Args:
            filters: فیلترها

        Returns:
            Callable: دکوراتور
        """
        def decorator(func):
            self.register_event_handler(EventType.EDITED_MESSAGE, func, filters)
            return func
        return decorator

    def on_callback_query(self, filters: Optional[Dict[str, Any]] = None):
        """
        دکوراتور برای ثبت هندلر callback query

        Args:
            filters: فیلترها

        Returns:
            Callable: دکوراتور
        """
        def decorator(func):
            self.register_event_handler(EventType.CALLBACK_QUERY, func, filters)
            return func
        return decorator

    def schedule(
        self,
        func: Callable,
        interval: Optional[int] = None,
        cron: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        times: Optional[int] = None,
        name: Optional[str] = None,
        *args,
        **kwargs
    ) -> str:
        """
        زمان‌بندی یک وظیفه

        Args:
            func: تابع
            interval: فاصله زمانی (ثانیه)
            cron: عبارت cron
            start_time: زمان شروع (timestamp)
            end_time: زمان پایان (timestamp)
            times: تعداد دفعات اجرا
            name: نام وظیفه
            *args: پارامترهای تابع
            **kwargs: پارامترهای تابع

        Returns:
            str: شناسه وظیفه
        """
        if not name:
            name = f"{self.name}_{func.__name__}"
        return self.scheduler.schedule(func, interval, cron, start_time, end_time, times, name, None, *args, **kwargs)

    def schedule_once(
        self,
        func: Callable,
        when: float,
        name: Optional[str] = None,
        *args,
        **kwargs
    ) -> str:
        """
        زمان‌بندی یک وظیفه یکبارمصرف

        Args:
            func: تابع
            when: زمان اجرا (timestamp)
            name: نام وظیفه
            *args: پارامترهای تابع
            **kwargs: پارامترهای تابع

        Returns:
            str: شناسه وظیفه
        """
        if not name:
            name = f"{self.name}_{func.__name__}"
        return self.scheduler.schedule_once(func, when, name, None, *args, **kwargs)

    async def get_db_connection(self) -> bool:
        """
        دریافت اتصال به دیتابیس

        Returns:
            bool: وضعیت اتصال
        """
        if not hasattr(self, '_db_connected') or not self._db_connected:
            self._db_connected = await self.db.connect()
        return self._db_connected

    async def execute_query(self, query: str, values: Optional[Tuple[Any, ...]] = None) -> Any:
        """
        اجرای کوئری روی دیتابیس

        Args:
            query: کوئری SQL
            values: مقادیر پارامترها

        Returns:
            Any: نتیجه اجرای کوئری
        """
        await self.get_db_connection()
        return await self.db.execute(query, values)

    async def fetch_one(self, query: str, values: Optional[Tuple[Any, ...]] = None) \
        -> Optional[Dict[str, Any]]: \
        """
        دریافت یک رکورد از دیتابیس

        Args:
            query: کوئری SQL
            values: مقادیر پارامترها

        Returns:
            Optional[Dict[str, Any]]: رکورد یافته شده یا None
        """
        await self.get_db_connection()
        return await self.db.fetch_one(query, values)

    async def fetch_all(self, query: str, values: Optional[Tuple[Any, ...]] = None) \
        -> List[Dict[str, Any]]: \
        """
        دریافت تمام رکوردهای مطابق با کوئری

        Args:
            query: کوئری SQL
            values: مقادیر پارامترها

        Returns:
            List[Dict[str, Any]]: لیست رکوردهای یافته شده
        """
        await self.get_db_connection()
        return await self.db.fetch_all(query, values)

    async def insert(self, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        افزودن یک رکورد به جدول

        Args:
            table: نام جدول
            data: داده‌های رکورد جدید

        Returns:
            Optional[Dict[str, Any]]: رکورد افزوده شده یا None
        """
        await self.get_db_connection()
        return await self.db.insert(table, data)

    async def update(self, table: str, data: Dict[str, Any], condition: str, values: Tuple[Any, ...]) \
        \ \
        \ \
        -> int: \
        """
        بروزرسانی یک یا چند رکورد

        Args:
            table: نام جدول
            data: داده‌های جدید
            condition: شرط بروزرسانی
            values: مقادیر شرط

        Returns:
            int: تعداد رکوردهای بروزرسانی شده
        """
        await self.get_db_connection()
        return await self.db.update(table, data, condition, values)

    async def delete(self, table: str, condition: str, values: Tuple[Any, ...]) -> int:
        """
        حذف یک یا چند رکورد

        Args:
            table: نام جدول
            condition: شرط حذف
            values: مقادیر شرط

        Returns:
            int: تعداد رکوردهای حذف شده
        """
        await self.get_db_connection()
        return await self.db.delete(table, condition, values)

    def _(self, key: str, lang: Optional[str] = None, default: Optional[str] = None, **kwargs) \
        -> str: \
        """
        ترجمه متن

        Args:
            key: کلید ترجمه
            lang: کد زبان (اختیاری)
            default: متن پیش‌فرض
            **kwargs: پارامترهای قالب‌بندی

        Returns:
            str: متن ترجمه شده
        """
        return self.localization.format_text(key, lang, default, **kwargs)

    def create_migration(self, description: str) -> str:
        """
        ایجاد فایل مهاجرت برای پلاگین

        Args:
            description: توضیحات مهاجرت

        Returns:
            str: مسیر فایل مهاجرت
        """
        import time
        timestamp = int(time.time())
        migration_dir = os.path.join("scripts", "migrations")
        os.makedirs(migration_dir, exist_ok=True)

        filename = f"{timestamp}_{self.name}_{description.lower().replace(' ', '_')}.sql"
        filepath = os.path.join(migration_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"-- Migration: {description}\n")
            f.write(f"-- Plugin: {self.name}\n")
            f.write(f"-- Timestamp: {timestamp}\n\n")

        return filepath
