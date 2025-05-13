#!/usr/bin/env python
"""
ماژول مدیریت ارتباط با پایگاه داده

این ماژول کلاس Database را پیاده‌سازی می‌کند که مسئول برقراری ارتباط با پایگاه داده و اجرای کوئری‌هاست.
الگوی طراحی Singleton برای اطمینان از یکتایی نمونه کلاس استفاده شده است.
"""

import os
import logging
from typing import Dict, List, Any, Optional
import asyncpg

logger = logging.getLogger(__name__)

class Database:
    """
    کلاس مدیریت ارتباط با پایگاه داده.

    از الگوی طراحی Singleton برای اطمینان از وجود فقط یک نمونه در کل برنامه استفاده می‌کند.
    """
    _instance = None
    _pool = None

    def __new__(cls, *args, **kwargs):
        """پیاده‌سازی الگوی Singleton"""
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, conn_string: Optional[str] = None):
        """مقداردهی اولیه کلاس Database"""
        if self._initialized:
            return

        self._initialized = True
        self.conn_string = conn_string or os.getenv('DATABASE_URL')
        self._connected = False

        # بررسی وجود اطلاعات اتصال به دیتابیس
        if not self.conn_string:
            logger.warning("اتصال به دیتابیس: آدرس اتصال تنظیم نشده است (DATABASE_URL)")

    async def connect(self) -> bool:
        """
        برقراری ارتباط با پایگاه داده

        Returns:
            bool: نتیجه برقراری ارتباط
        """
        if self._connected:
            return True

        try:
            # ایجاد یک استخر اتصال
            self._pool = await asyncpg.create_pool(
                dsn=self.conn_string,
                min_size=2,
                max_size=10
            )
            self._connected = True
            logger.info("اتصال به پایگاه داده با موفقیت برقرار شد")
            return True

        except Exception as e:
            logger.error(f"خطا در برقراری ارتباط با پایگاه داده: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """قطع ارتباط با پایگاه داده"""
        if self._pool:
            await self._pool.close()
            self._connected = False
            logger.info("ارتباط با پایگاه داده قطع شد")

    async def execute(self, query: str, *args, **kwargs) -> str:
        """
        اجرای کوئری بدون دریافت نتیجه

        Args:
            query (str): کوئری SQL برای اجرا
            *args: پارامترهای کوئری
            **kwargs: پارامترهای اضافی

        Returns:
            str: شناسه یا تعداد رکوردهای تحت تاثیر
        """
        if not self._connected:
            await self.connect()

        if not self._connected:
            logger.error("عدم امکان اجرای کوئری: ارتباط با پایگاه داده برقرار نیست")
            return None

        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(query, *args, **kwargs)
                return result
        except Exception as e:
            logger.error(f"خطا در اجرای کوئری: {e}")
            logger.debug(f"کوئری: {query}")
            logger.debug(f"پارامترها: {args}, {kwargs}")
            return None

    async def fetch(self, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        اجرای کوئری و دریافت چندین رکورد

        Args:
            query (str): کوئری SQL برای اجرا
            *args: پارامترهای کوئری
            **kwargs: پارامترهای اضافی

        Returns:
            List[Dict[str, Any]]: لیستی از نتایج به صورت دیکشنری
        """
        if not self._connected:
            await self.connect()

        if not self._connected:
            logger.error("عدم امکان اجرای کوئری: ارتباط با پایگاه داده برقرار نیست")
            return []

        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(query, *args, **kwargs)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"خطا در اجرای کوئری: {e}")
            logger.debug(f"کوئری: {query}")
            logger.debug(f"پارامترها: {args}, {kwargs}")
            return []

    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """
        اجرای کوئری و دریافت یک رکورد

        Args:
            query (str): کوئری SQL برای اجرا
            *args: پارامترهای کوئری
            **kwargs: پارامترهای اضافی

        Returns:
            Optional[Dict[str, Any]]: نتیجه به صورت دیکشنری یا None اگر رکوردی یافت نشود
        """
        if not self._connected:
            await self.connect()

        if not self._connected:
            logger.error("عدم امکان اجرای کوئری: ارتباط با پایگاه داده برقرار نیست")
            return None

        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(query, *args, **kwargs)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"خطا در اجرای کوئری: {e}")
            logger.debug(f"کوئری: {query}")
            logger.debug(f"پارامترها: {args}, {kwargs}")
            return None

    async def transaction(self) -> asyncpg.Connection:
        """
        ایجاد یک تراکنش جدید

        Returns:
            asyncpg.Connection: کانکشن با تراکنش فعال
        """
        if not self._connected:
            await self.connect()

        if not self._connected:
            logger.error("عدم امکان ایجاد تراکنش: ارتباط با پایگاه داده برقرار نیست")
            return None

        try:
            return self._pool.acquire()
        except Exception as e:
            logger.error(f"خطا در ایجاد تراکنش: {e}")
            return None
