"""
مدیریت لیست‌های مسدود شده و کلمات کلیدی فایروال
"""
import json
import re
import logging
from typing import Optional
from pyrogram.types import Message

logger = logging.getLogger(__name__)


class BlocklistManager:
    """
    کلاس مدیریت لیست مسدود شده و کلمات کلیدی ممنوع
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        self.blocked_users = []  # لیست کاربران مسدود شده
        self.blocked_keywords = []  # کلمات کلیدی مسدود شده

    async def initialize(self, db):
        """
        راه‌اندازی مدیریت کننده

        Args:
            db: اتصال دیتابیس
        """
        try:
            # بارگیری لیست کاربران مسدود شده
            blocked_users = await db.fetchrow(
                "SELECT value FROM settings WHERE key = 'firewall_blocked_users'"
            )

            if blocked_users and 'value' in blocked_users:
                self.blocked_users = json.loads(blocked_users['value'])
            else:
                await db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('firewall_blocked_users', json.dumps(self.blocked_users), 'لیست کاربران مسدود شده توسط فایروال')
                )

            # بارگیری کلمات کلیدی مسدود شده
            blocked_keywords = await db.fetchrow(
                "SELECT value FROM settings WHERE key = 'firewall_blocked_keywords'"
            )

            if blocked_keywords and 'value' in blocked_keywords:
                self.blocked_keywords = json.loads(blocked_keywords['value'])
            else:
                await db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('firewall_blocked_keywords', json.dumps(self.blocked_keywords), 'کلمات کلیدی مسدود شده توسط فایروال')
                )

            logger.info(f"مدیریت‌کننده لیست مسدود راه‌اندازی شد: {len(self.blocked_users)} کاربر و {len(self.blocked_keywords)} کلمه کلیدی")

        except Exception as e:
            logger.error(f"خطا در راه‌اندازی مدیریت‌کننده لیست مسدود: {str(e)}")

    async def cleanup(self, db):
        """
        پاکسازی منابع

        Args:
            db: اتصال دیتابیس
        """
        try:
            # ذخیره لیست کاربران مسدود شده
            await db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_users), 'firewall_blocked_users')
            )

            # ذخیره کلمات کلیدی مسدود شده
            await db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_keywords), 'firewall_blocked_keywords')
            )

        except Exception as e:
            logger.error(f"خطا در پاکسازی مدیریت‌کننده لیست مسدود: {str(e)}")

    async def is_blocked(self, message: Message) -> bool:
        """
        بررسی مسدود بودن فرستنده پیام

        Args:
            message (Message): پیام دریافتی

        Returns:
            bool: وضعیت مسدود بودن
        """
        return message.from_user and message.from_user.id in self.blocked_users

    async def contains_blocked_keywords(self, message: Message) -> bool:
        """
        بررسی وجود کلمات کلیدی مسدود شده در پیام

        Args:
            message (Message): پیام دریافتی

        Returns:
            bool: وضعیت وجود کلمه کلیدی مسدود شده
        """
        if not message.text or not self.blocked_keywords:
            return False

        for keyword in self.blocked_keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", message.text, re.IGNORECASE):
                return True

        return False

    def find_matching_keyword(self, text: str) -> Optional[str]:
        """
        یافتن کلمه کلیدی مسدود شده در متن

        Args:
            text (str): متن برای بررسی

        Returns:
            Optional[str]: کلمه کلیدی مطابقت داده شده یا None
        """
        if not text or not self.blocked_keywords:
            return None

        for keyword in self.blocked_keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE):
                return keyword

        return None

    async def add_blocked_user(self, user_id: int, db) -> bool:
        """
        افزودن کاربر به لیست مسدود شده

        Args:
            user_id (int): شناسه کاربر
            db: اتصال دیتابیس

        Returns:
            bool: وضعیت عملیات
        """
        try:
            # بررسی تکراری نبودن
            if user_id in self.blocked_users:
                return False

            # افزودن به لیست
            self.blocked_users.append(user_id)

            # ذخیره در دیتابیس
            await db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_users), 'firewall_blocked_users')
            )

            return True

        except Exception as e:
            logger.error(f"خطا در افزودن کاربر به لیست مسدود: {str(e)}")
            return False

    async def remove_blocked_user(self, user_id: int, db) -> bool:
        """
        حذف کاربر از لیست مسدود شده

        Args:
            user_id (int): شناسه کاربر
            db: اتصال دیتابیس

        Returns:
            bool: وضعیت عملیات
        """
        try:
            # بررسی وجود در لیست
            if user_id not in self.blocked_users:
                return False

            # حذف از لیست
            self.blocked_users.remove(user_id)

            # ذخیره در دیتابیس
            await db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_users), 'firewall_blocked_users')
            )

            return True

        except Exception as e:
            logger.error(f"خطا در حذف کاربر از لیست مسدود: {str(e)}")
            return False

    async def add_blocked_keyword(self, keyword: str, db) -> bool:
        """
        افزودن کلمه کلیدی به لیست مسدود شده

        Args:
            keyword (str): کلمه کلیدی
            db: اتصال دیتابیس

        Returns:
            bool: وضعیت عملیات
        """
        try:
            # بررسی تکراری نبودن
            if keyword in self.blocked_keywords:
                return False

            # افزودن به لیست
            self.blocked_keywords.append(keyword)

            # ذخیره در دیتابیس
            await db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_keywords), 'firewall_blocked_keywords')
            )

            return True

        except Exception as e:
            logger.error(f"خطا در افزودن کلمه کلیدی به لیست مسدود: {str(e)}")
            return False

    async def remove_blocked_keyword(self, keyword: str, db) -> bool:
        """
        حذف کلمه کلیدی از لیست مسدود شده

        Args:
            keyword (str): کلمه کلیدی
            db: اتصال دیتابیس

        Returns:
            bool: وضعیت عملیات
        """
        try:
            # بررسی وجود در لیست
            if keyword not in self.blocked_keywords:
                return False

            # حذف از لیست
            self.blocked_keywords.remove(keyword)

            # ذخیره در دیتابیس
            await db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_keywords), 'firewall_blocked_keywords')
            )

            return True

        except Exception as e:
            logger.error(f"خطا در حذف کلمه کلیدی از لیست مسدود: {str(e)}")
            return False
