"""
ماژول مدیریت کش دیتابیس برای سلف بات تلگرام
"""
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, Tuple, Set
from datetime import datetime, timedelta

from core.database import Database
from core.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class DatabaseCache:
    """
    کلاس مدیریت کش دیتابیس با استفاده از Redis
    """

    def __init__(self, database: Database, redis: RedisManager, default_ttl: int = 3600):
        """
        مقداردهی اولیه

        Args:
            database: شیء اتصال به دیتابیس
            redis: شیء مدیریت Redis
            default_ttl: زمان پیش‌فرض انقضای کش (ثانیه)
        """
        self.db = database
        self.redis = redis
        self.default_ttl = default_ttl
        self._cache_tags = {}  # {tag: set(keys)}

    def _get_cache_key(self, query_type: str, table: str, query_hash: str) -> str:
        """
        ساخت کلید کش

        Args:
            query_type: نوع کوئری (select, count, etc)
            table: نام جدول
            query_hash: هش کوئری (ترکیبی از پارامترها)

        Returns:
            str: کلید کش
        """
        return f"db:{table}:{query_type}:{query_hash}"

    def _get_tag_key(self, table: str) -> str:
        """
        ساخت کلید تگ برای جدول

        Args:
            table: نام جدول

        Returns:
            str: کلید تگ
        """
        return f"tag:{table}"

    async def _add_to_tag(self, table: str, cache_key: str) -> None:
        """
        افزودن کلید به تگ

        Args:
            table: نام جدول
            cache_key: کلید کش
        """
        tag_key = self._get_tag_key(table)

        # افزودن به نگاشت داخلی
        if tag_key not in self._cache_tags:
            self._cache_tags[tag_key] = set()

        self._cache_tags[tag_key].add(cache_key)

        # افزودن به redis
        await self.redis.hset(tag_key, cache_key, "1")

    async def _invalidate_tag(self, table: str) -> None:
        """
        نامعتبر کردن تمام کش‌های مرتبط با یک جدول

        Args:
            table: نام جدول
        """
        tag_key = self._get_tag_key(table)

        # دریافت کلیدهای مرتبط
        keys = set()

        # از نگاشت داخلی
        if tag_key in self._cache_tags:
            keys = self._cache_tags[tag_key]
            del self._cache_tags[tag_key]

        # از redis
        redis_keys = await self.redis.hgetall(tag_key)
        if redis_keys:
            keys.update(redis_keys.keys())

        # حذف کش‌ها
        for key in keys:
            await self.redis.delete(key)

        # حذف تگ
        await self.redis.delete(tag_key)

    async def fetch_one(self, table: str, query: str, params: Optional[Tuple] = None,
                        ttl: Optional[int] = None, skip_cache: bool = False) -> Optional[Dict[str, Any]]:
        """
        دریافت یک رکورد از دیتابیس با پشتیبانی از کش

        Args:
            table: نام جدول
            query: کوئری SQL
            params: پارامترهای کوئری
            ttl: زمان انقضای کش (ثانیه)
            skip_cache: نادیده گرفتن کش

        Returns:
            Optional[Dict[str, Any]]: رکورد یافت شده یا None
        """
        # ساخت کلید کش
        params_str = json.dumps(params) if params else ""
        query_hash = str(hash(f"{query}:{params_str}"))
        cache_key = self._get_cache_key("one", table, query_hash)

        # بررسی کش
        if not skip_cache:
            cached = await self.redis.get(cache_key)
            if cached is not None:
                logger.debug(f"داده از کش دریافت شد: {cache_key}")
                return cached

        # دریافت از دیتابیس
        result = await self.db.fetch_one(query, params)

        # ذخیره در کش
        if result is not None:
            ttl_value = ttl if ttl is not None else self.default_ttl
            await self.redis.set(cache_key, dict(result), ttl_value)
            await self._add_to_tag(table, cache_key)

        return dict(result) if result else None

    async def fetch_all(self, table: str, query: str, params: Optional[Tuple] = None,
                       ttl: Optional[int] = None, skip_cache: bool = False) -> List[Dict[str, Any]]:
        """
        دریافت چندین رکورد از دیتابیس با پشتیبانی از کش

        Args:
            table: نام جدول
            query: کوئری SQL
            params: پارامترهای کوئری
            ttl: زمان انقضای کش (ثانیه)
            skip_cache: نادیده گرفتن کش

        Returns:
            List[Dict[str, Any]]: لیست رکوردهای یافت شده
        """
        # ساخت کلید کش
        params_str = json.dumps(params) if params else ""
        query_hash = str(hash(f"{query}:{params_str}"))
        cache_key = self._get_cache_key("all", table, query_hash)

        # بررسی کش
        if not skip_cache:
            cached = await self.redis.get(cache_key)
            if cached is not None:
                logger.debug(f"داده از کش دریافت شد: {cache_key}")
                return cached

        # دریافت از دیتابیس
        results = await self.db.fetch_all(query, params)

        # ذخیره در کش
        if results:
            ttl_value = ttl if ttl is not None else self.default_ttl
            data = [dict(row) for row in results]
            await self.redis.set(cache_key, data, ttl_value)
            await self._add_to_tag(table, cache_key)
            return data

        return []

    async def execute(self, tables: List[str], query: str, params: Optional[Tuple] = None) -> None:
        """
        اجرای کوئری دیتابیس و نامعتبر کردن کش

        Args:
            tables: لیست جداول تحت تأثیر
            query: کوئری SQL
            params: پارامترهای کوئری
        """
        # اجرای کوئری
        await self.db.execute(query, params)

        # نامعتبر کردن کش‌های مرتبط
        for table in tables:
            await self._invalidate_tag(table)

    async def count(self, table: str, query: str, params: Optional[Tuple] = None,
                   ttl: Optional[int] = None, skip_cache: bool = False) -> int:
        """
        شمارش تعداد رکوردها با پشتیبانی از کش

        Args:
            table: نام جدول
            query: کوئری SQL
            params: پارامترهای کوئری
            ttl: زمان انقضای کش (ثانیه)
            skip_cache: نادیده گرفتن کش

        Returns:
            int: تعداد رکوردها
        """
        # ساخت کلید کش
        params_str = json.dumps(params) if params else ""
        query_hash = str(hash(f"{query}:{params_str}"))
        cache_key = self._get_cache_key("count", table, query_hash)

        # بررسی کش
        if not skip_cache:
            cached = await self.redis.get(cache_key)
            if cached is not None:
                logger.debug(f"داده از کش دریافت شد: {cache_key}")
                return int(cached)

        # دریافت از دیتابیس
        result = await self.db.fetch_one(query, params)

        # استخراج مقدار count
        count = 0
        if result:
            # معمولاً اولین ستون نتیجه count است
            count = list(dict(result).values())[0]

        # ذخیره در کش
        ttl_value = ttl if ttl is not None else self.default_ttl
        await self.redis.set(cache_key, count, ttl_value)
        await self._add_to_tag(table, cache_key)

        return count

    async def invalidate_cache(self, tables: List[str]) -> None:
        """
        نامعتبر کردن کش برای جداول مشخص

        Args:
            tables: لیست جداول
        """
        for table in tables:
            await self._invalidate_tag(table)

    async def transaction(self, tables: List[str], queries: List[Tuple[str, Optional[Tuple]]]) \
        -> bool: \
        """
        اجرای کوئری‌ها در یک تراکنش

        Args:
            tables: لیست جداول تحت تأثیر
            queries: لیست کوئری‌ها و پارامترهای آن‌ها

        Returns:
            bool: نتیجه اجرای تراکنش
        """
        # اجرای تراکنش
        success = await self.db.transaction(queries)

        # نامعتبر کردن کش‌ها در صورت موفقیت
        if success:
            for table in tables:
                await self._invalidate_tag(table)

        return success
