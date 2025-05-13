"""
مدیریت لیست سفید فایروال
"""
import json
import logging
from pyrogram.types import Message

logger = logging.getLogger(__name__)


class WhitelistManager:
    """
    کلاس مدیریت لیست سفید کاربران و گروه‌های استثنا شده
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        self.whitelist = []  # لیست سفید کاربران و گروه‌ها

    async def initialize(self, db):
        """
        راه‌اندازی مدیریت کننده

        Args:
            db: اتصال دیتابیس
        """
        try:
            # بارگیری لیست سفید
            whitelist = await db.fetchrow(
                "SELECT value FROM settings WHERE key = 'firewall_whitelist'"
            )

            if whitelist and 'value' in whitelist:
                self.whitelist = json.loads(whitelist['value'])
            else:
                await db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('firewall_whitelist', json.dumps(self.whitelist), 'لیست سفید کاربران و گروه‌های استثنا شده از فایروال')
                )

            logger.info(f"مدیریت‌کننده لیست سفید راه‌اندازی شد: {len(self.whitelist)} مورد")

        except Exception as e:
            logger.error(f"خطا در راه‌اندازی مدیریت‌کننده لیست سفید: {str(e)}")

    async def cleanup(self, db):
        """
        پاکسازی منابع

        Args:
            db: اتصال دیتابیس
        """
        try:
            # ذخیره لیست سفید
            await db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.whitelist), 'firewall_whitelist')
            )

        except Exception as e:
            logger.error(f"خطا در پاکسازی مدیریت‌کننده لیست سفید: {str(e)}")

    async def is_whitelisted(self, message: Message) -> bool:
        """
        بررسی وجود در لیست سفید

        Args:
            message (Message): پیام دریافتی

        Returns:
            bool: وضعیت وجود در لیست سفید
        """
        # بررسی کاربر
        if message.from_user and message.from_user.id in self.whitelist:
            return True

        # بررسی گروه/چت
        if message.chat and message.chat.id in self.whitelist:
            return True

        return False

    async def add_to_whitelist(self, item_id: int, db) -> bool:
        """
        افزودن مورد به لیست سفید

        Args:
            item_id (int): شناسه کاربر یا گروه
            db: اتصال دیتابیس

        Returns:
            bool: وضعیت عملیات
        """
        try:
            # بررسی تکراری نبودن
            if item_id in self.whitelist:
                return False

            # افزودن به لیست
            self.whitelist.append(item_id)

            # ذخیره در دیتابیس
            await db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.whitelist), 'firewall_whitelist')
            )

            return True

        except Exception as e:
            logger.error(f"خطا در افزودن به لیست سفید: {str(e)}")
            return False

    async def remove_from_whitelist(self, item_id: int, db) -> bool:
        """
        حذف مورد از لیست سفید

        Args:
            item_id (int): شناسه کاربر یا گروه
            db: اتصال دیتابیس

        Returns:
            bool: وضعیت عملیات
        """
        try:
            # بررسی وجود در لیست
            if item_id not in self.whitelist:
                return False

            # حذف از لیست
            self.whitelist.remove(item_id)

            # ذخیره در دیتابیس
            await db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.whitelist), 'firewall_whitelist')
            )

            return True

        except Exception as e:
            logger.error(f"خطا در حذف از لیست سفید: {str(e)}")
            return False
