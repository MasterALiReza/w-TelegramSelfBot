"""
کنترل‌کننده اسپم برای فایروال
"""
import json
import time
import logging
from typing import Dict, List, Any
from pyrogram.types import Message

logger = logging.getLogger(__name__)


class SpamController:
    """
    کلاس کنترل اسپم در پیام‌ها
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        self.spam_threshold = 5  # آستانه تشخیص اسپم
        self.spam_window = 60  # پنجره زمانی (ثانیه) برای بررسی اسپم
        self.user_message_count = {}  # تعداد پیام کاربران در پنجره زمانی
        self.last_cleanup_time = time.time()
        self.auto_delete_spam = True  # حذف خودکار پیام‌های اسپم

    async def initialize(self, db):
        """
        راه‌اندازی کنترل‌کننده

        Args:
            db: اتصال دیتابیس
        """
        try:
            # بارگیری تنظیمات اسپم
            spam_settings = await db.fetchrow(
                "SELECT value FROM settings WHERE key = 'firewall_spam_settings'"
            )

            if spam_settings and 'value' in spam_settings:
                settings = json.loads(spam_settings['value'])
                self.spam_threshold = settings.get('threshold', 5)
                self.spam_window = settings.get('window', 60)
                self.auto_delete_spam = settings.get('auto_delete', True)
            else:
                spam_settings_data = {
                    'threshold': self.spam_threshold,
                    'window': self.spam_window,
                    'auto_delete': self.auto_delete_spam
                }
                await db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('firewall_spam_settings', json.dumps(spam_settings_data), 'تنظیمات تشخیص اسپم فایروال')
                )

            logger.info(f"کنترل‌کننده اسپم راه‌اندازی شد: آستانه {self.spam_threshold} پیام در {self.spam_window} ثانیه")

        except Exception as e:
            logger.error(f"خطا در راه‌اندازی کنترل‌کننده اسپم: {str(e)}")

    async def cleanup(self, db):
        """
        پاکسازی منابع

        Args:
            db: اتصال دیتابیس
        """
        try:
            # ذخیره تنظیمات اسپم
            spam_settings_data = {
                'threshold': self.spam_threshold,
                'window': self.spam_window,
                'auto_delete': self.auto_delete_spam
            }
            await db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(spam_settings_data), 'firewall_spam_settings')
            )

        except Exception as e:
            logger.error(f"خطا در پاکسازی کنترل‌کننده اسپم: {str(e)}")

    async def is_spam(self, message: Message) -> bool:
        """
        بررسی اسپم بودن پیام

        Args:
            message (Message): پیام دریافتی

        Returns:
            bool: وضعیت اسپم بودن
        """
        if not message.from_user:
            return False

        # بروزرسانی تعداد پیام‌های کاربر
        current_time = time.time()

        # پاکسازی داده‌های قدیمی
        if current_time - self.last_cleanup_time > 60:
            await self.cleanup_temporary_data()

        user_id = message.from_user.id

        if user_id not in self.user_message_count:
            self.user_message_count[user_id] = []

        # اضافه کردن زمان پیام جاری
        self.user_message_count[user_id].append(current_time)

        # حذف پیام‌های قدیمی‌تر از پنجره زمانی
        self.user_message_count[user_id] = [
            t for t in self.user_message_count[user_id]
            if current_time - t <= self.spam_window
        ]

        # بررسی آستانه اسپم
        return len(self.user_message_count[user_id]) > self.spam_threshold

    async def cleanup_temporary_data(self) -> None:
        """
        پاکسازی داده‌های موقت
        """
        try:
            current_time = time.time()
            self.last_cleanup_time = current_time

            # پاکسازی تعداد پیام کاربران
            for user_id in list(self.user_message_count.keys()):
                # حذف پیام‌های قدیمی‌تر از پنجره زمانی
                self.user_message_count[user_id] = [
                    t for t in self.user_message_count[user_id]
                    if current_time - t <= self.spam_window
                ]

                # حذف کاربرانی که پیامی ندارند
                if not self.user_message_count[user_id]:
                    del self.user_message_count[user_id]

            logger.debug(f"پاکسازی داده‌های موقت اسپم انجام شد، {len(self.user_message_count)} کاربر در حافظه")

        except Exception as e:
            logger.error(f"خطا در پاکسازی داده‌های موقت اسپم: {str(e)}")

    def get_user_message_count(self, user_id: int) -> int:
        """
        دریافت تعداد پیام‌های کاربر در پنجره زمانی

        Args:
            user_id (int): شناسه کاربر

        Returns:
            int: تعداد پیام‌ها
        """
        if user_id not in self.user_message_count:
            return 0

        return len(self.user_message_count[user_id])

    async def update_spam_settings(self, threshold: int = None, window: int = None, auto_delete: bool = None, db = None) \
        \ \
        \ \
        -> bool: \
        """
        بروزرسانی تنظیمات اسپم

        Args:
            threshold (int, optional): آستانه جدید
            window (int, optional): پنجره زمانی جدید
            auto_delete (bool, optional): وضعیت حذف خودکار
            db: اتصال دیتابیس

        Returns:
            bool: وضعیت عملیات
        """
        try:
            if threshold is not None:
                self.spam_threshold = threshold

            if window is not None:
                self.spam_window = window

            if auto_delete is not None:
                self.auto_delete_spam = auto_delete

            # ذخیره در دیتابیس اگر موجود باشد
            if db:
                spam_settings_data = {
                    'threshold': self.spam_threshold,
                    'window': self.spam_window,
                    'auto_delete': self.auto_delete_spam
                }
                await db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (json.dumps(spam_settings_data), 'firewall_spam_settings')
                )

            return True

        except Exception as e:
            logger.error(f"خطا در بروزرسانی تنظیمات اسپم: {str(e)}")
            return False
