"""
پیاده‌سازی PostgreSQL (Supabase) برای دیتابیس
"""
import os
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from supabase import Client, create_client

from core.database.base import DatabaseInterface

# بارگذاری متغیرهای محیطی
load_dotenv()


class PostgreSQLDatabase(DatabaseInterface):
    """
    پیاده‌سازی اینترفیس دیتابیس برای PostgreSQL/Supabase
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.client: Optional[Client] = None

    async def connect(self) -> bool:
        """
        اتصال به دیتابیس Supabase

        Returns:
            bool: وضعیت اتصال
        """
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            return True
        except Exception as e:
            print(f"خطا در اتصال به Supabase: {str(e)}")
            return False

    async def disconnect(self) -> bool:
        """
        قطع اتصال از دیتابیس
        در Supabase نیازی به قطع اتصال دستی نیست

        Returns:
            bool: وضعیت قطع اتصال
        """
        self.client = None
        return True

    async def execute(self, query: str, values: Optional[Tuple[Any, ...]] = None) -> Any:
        """
        اجرای کوئری روی دیتابیس

        Args:
            query: کوئری SQL
            values: مقادیر پارامترها

        Returns:
            Any: نتیجه اجرای کوئری
        """
        if not self.client:
            await self.connect()

        try:
            # تبدیل values به دیکشنری برای استفاده در RPC
            params = {}
            if values:
                for i, value in enumerate(values):
                    params[f"param_{i+1}"] = value

            # استفاده از RPC برای اجرای کوئری
            return self.client.rpc(query, params).execute()
        except Exception as e:
            print(f"خطا در اجرای کوئری: {str(e)}")
            return None

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
        if not self.client:
            await self.connect()

        try:
            # روش استاندارد برای کوئری‌های ساده
            table_name = query.split("FROM")[1].split() \
                [0].strip() if "FROM" in query.upper() else None \

            if table_name:
                query_builder = self.client.table(table_name).select("*")

                # اعمال شرط‌ها (ساده‌سازی شده)
                if "WHERE" in query.upper() and values:
                    condition = query.split("WHERE")[1].strip()
                    if "=" in condition:
                        column, _ = condition.split("=", 1)
                        column = column.strip()
                        query_builder = query_builder.eq(column, values[0])

                result = query_builder.limit(1).execute()
                return result.data[0] if result.data else None
            else:
                # برای کوئری‌های پیچیده‌تر از RPC استفاده می‌کنیم
                params = {}
                if values:
                    for i, value in enumerate(values):
                        params[f"param_{i+1}"] = value

                result = self.client.rpc(query, params).execute()
                return result.data[0] if result.data else None
        except Exception as e:
            print(f"خطا در دریافت رکورد: {str(e)}")
            return None

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
        if not self.client:
            await self.connect()

        try:
            # روش استاندارد برای کوئری‌های ساده
            table_name = query.split("FROM")[1].split() \
                [0].strip() if "FROM" in query.upper() else None \

            if table_name:
                query_builder = self.client.table(table_name).select("*")

                # اعمال شرط‌ها (ساده‌سازی شده)
                if "WHERE" in query.upper() and values:
                    condition = query.split("WHERE")[1].strip()
                    if "=" in condition:
                        column, _ = condition.split("=", 1)
                        column = column.strip()
                        query_builder = query_builder.eq(column, values[0])

                result = query_builder.execute()
                return result.data if result.data else []
            else:
                # برای کوئری‌های پیچیده‌تر از RPC استفاده می‌کنیم
                params = {}
                if values:
                    for i, value in enumerate(values):
                        params[f"param_{i+1}"] = value

                result = self.client.rpc(query, params).execute()
                return result.data if result.data else []
        except Exception as e:
            print(f"خطا در دریافت رکوردها: {str(e)}")
            return []

    async def insert(self, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        افزودن یک رکورد به جدول

        Args:
            table: نام جدول
            data: داده‌های رکورد جدید

        Returns:
            Optional[Dict[str, Any]]: رکورد افزوده شده یا None
        """
        if not self.client:
            await self.connect()

        try:
            result = self.client.table(table).insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"خطا در افزودن رکورد: {str(e)}")
            return None

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
        if not self.client:
            await self.connect()

        try:
            # استخراج نام ستون و مقدار شرط
            column, _ = condition.split("=", 1)
            column = column.strip()
            value = values[0]

            result = self.client.table(table).update(data).eq(column, value).execute()
            return len(result.data) if result.data else 0
        except Exception as e:
            print(f"خطا در بروزرسانی رکورد: {str(e)}")
            return 0

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
        if not self.client:
            await self.connect()

        try:
            # استخراج نام ستون و مقدار شرط
            column, _ = condition.split("=", 1)
            column = column.strip()
            value = values[0]

            result = self.client.table(table).delete().eq(column, value).execute()
            return len(result.data) if result.data else 0
        except Exception as e:
            print(f"خطا در حذف رکورد: {str(e)}")
            return 0

    async def create_tables(self) -> bool:
        """
        ایجاد جداول در دیتابیس
        در Supabase معمولاً با مهاجرت یا RPC انجام می‌شود

        Returns:
            bool: وضعیت ایجاد جداول
        """
        # مهاجرت‌ها باید با ابزار مخصوص Migration اجرا شوند
        return True
