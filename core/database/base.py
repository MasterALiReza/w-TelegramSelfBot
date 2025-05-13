"""
کلاس پایه برای تعامل با دیتابیس
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union


class DatabaseInterface(ABC):
    """
    رابط (Interface) اصلی برای تعامل با دیتابیس‌ها
    """

    @abstractmethod
    async def connect(self) -> bool:
        """
        اتصال به دیتابیس

        Returns:
            bool: وضعیت اتصال
        """

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        قطع اتصال از دیتابیس

        Returns:
            bool: وضعیت قطع اتصال
        """

    @abstractmethod
    async def execute(self, query: str, values: Optional[Tuple[Any, ...]] = None) -> Any:
        """
        اجرای کوئری روی دیتابیس

        Args:
            query: کوئری SQL
            values: مقادیر پارامترها

        Returns:
            Any: نتیجه اجرای کوئری
        """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def insert(self, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        افزودن یک رکورد به جدول

        Args:
            table: نام جدول
            data: داده‌های رکورد جدید

        Returns:
            Optional[Dict[str, Any]]: رکورد افزوده شده یا None
        """

    @abstractmethod
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
        pass

    @abstractmethod
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

    @abstractmethod
    async def create_tables(self) -> bool:
        """
        ایجاد جداول در دیتابیس

        Returns:
            bool: وضعیت ایجاد جداول
        """


class DatabaseManager:
    """
    مدیریت دسترسی به دیتابیس
    """
    _instance = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def set_database(cls, db: DatabaseInterface) -> None:
        """
        تنظیم نمونه دیتابیس

        Args:
            db: شیء دیتابیس
        """
        cls._db = db

    @classmethod
    def get_database(cls) -> Optional[DatabaseInterface]:
        """
        دریافت نمونه دیتابیس

        Returns:
            Optional[DatabaseInterface]: شیء دیتابیس
        """
        return cls._db
