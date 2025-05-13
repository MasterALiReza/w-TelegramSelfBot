"""
پلاگین فایروال امنیتی
این پلاگین مسئول محافظت از حساب کاربری در برابر اسپم، محتوای نامناسب و سایر تهدیدات امنیتی است.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import re
from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.types import Message, User, Chat

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient
from plugins.security.firewall.blocklist_manager import BlocklistManager
from plugins.security.firewall.spam_controller import SpamController
from plugins.security.firewall.whitelist_manager import WhitelistManager

logger = logging.getLogger(__name__)


class FirewallPlugin(BasePlugin):
    """
    پلاگین فایروال امنیتی
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="Firewall",
            version="1.0.0",
            description="فایروال امنیتی برای محافظت در برابر تهدیدات",
            author="SelfBot Team",
            category="security"
        )
        self.is_enabled = True
        self.notification_enabled = True

        # ایجاد نمونه‌های مدیریتی
        self.blocklist_manager = BlocklistManager()
        self.spam_controller = SpamController()
        self.whitelist_manager = WhitelistManager()

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین فایروال در حال راه‌اندازی...")

            # راه‌اندازی مدیریت‌کننده‌ها
            await self.blocklist_manager.initialize(self.db)
            await self.spam_controller.initialize(self.db)
            await self.whitelist_manager.initialize(self.db)

            # بارگیری وضعیت نوتیفیکیشن
            notification_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'firewall_notification'"
            )

            if notification_setting and 'value' in notification_setting:
                self.notification_enabled = json.loads(notification_setting['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('firewall_notification', json.dumps(self.notification_enabled), 'وضعیت نوتیفیکیشن فایروال')
                )

            # ثبت دستورات
            self.register_command('fw_block', self.cmd_block_user, 'مسدود کردن کاربر', '.fw_block [user_id]')
            self.register_command('fw_unblock', self.cmd_unblock_user, 'رفع مسدودیت کاربر', '.fw_unblock [user_id]')
            self.register_command('fw_blocklist', self.cmd_show_blocklist, 'نمایش لیست مسدودشده‌ها', '.fw_blocklist')
            self.register_command('fw_keyword', self.cmd_manage_keyword, 'مدیریت کلمات کلیدی', '.fw_keyword [add|remove] [keyword]')
            self.register_command('fw_whitelist', self.cmd_manage_whitelist, 'مدیریت لیست سفید', '.fw_whitelist [add|remove] [id]')
            self.register_command('fw_spam', self.cmd_spam_settings, 'تنظیمات ضد اسپم', '.fw_spam [threshold|window|autodelete] [value]')
            self.register_command('fw_status', self.cmd_status, 'وضعیت فایروال', '.fw_status')
            self.register_command('fw_notify', self.cmd_toggle_notification, 'تغییر وضعیت نوتیفیکیشن', '.fw_notify [on|off]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_message, {})
            self.register_event_handler(EventType.MESSAGE, self.on_block_command, {'text_startswith': ['.fw_block', '/fw_block', '!fw_block']})
            self.register_event_handler(EventType.MESSAGE, self.on_unblock_command, {'text_startswith': ['.fw_unblock', '/fw_unblock', '!fw_unblock']})
            self.register_event_handler(EventType.MESSAGE, self.on_blocklist_command, {'text_startswith': ['.fw_blocklist', '/fw_blocklist', '!fw_blocklist']})
            self.register_event_handler(EventType.MESSAGE, self.on_keyword_command, {'text_startswith': ['.fw_keyword', '/fw_keyword', '!fw_keyword']})
            self.register_event_handler(EventType.MESSAGE, self.on_whitelist_command, {'text_startswith': ['.fw_whitelist', '/fw_whitelist', '!fw_whitelist']})
            self.register_event_handler(EventType.MESSAGE, self.on_spam_command, {'text_startswith': ['.fw_spam', '/fw_spam', '!fw_spam']})
            self.register_event_handler(EventType.MESSAGE, self.on_status_command, {'text_startswith': ['.fw_status', '/fw_status', '!fw_status']})
            self.register_event_handler(EventType.MESSAGE, self.on_notify_command, {'text_startswith': ['.fw_notify', '/fw_notify', '!fw_notify']})

            # زمان‌بندی پاکسازی منظم داده‌های موقت
            self.schedule(self.spam_controller.cleanup_temporary_data, interval=300, name="firewall_cleanup")

            # ثبت آمار پلاگین در دیتابیس
            plugin_data = {
                'name': self.name,
                'version': self.version,
                'description': self.description,
                'author': self.author,
                'category': self.category,
                'is_enabled': True,
                'config': json.dumps(self.config)
            }

            # بررسی وجود پلاگین در دیتابیس
            existing_plugin = await self.fetch_one(
                "SELECT id FROM plugins WHERE name = $1",
                (self.name,)
            )

            if existing_plugin:
                # بروزرسانی
                await self.update(
                    'plugins',
                    {k: v for k, v in plugin_data.items() if k != 'name'},
                    'name = $1',
                    (self.name,)
                )
            else:
                # ایجاد
                await self.insert('plugins', plugin_data)

            logger.info(f"پلاگین {self.name} با موفقیت راه‌اندازی شد")
            return True

        except Exception as e:
            logger.error(f"خطا در راه‌اندازی پلاگین {self.name}: {str(e)}")
            return False

    async def cleanup(self) -> bool:
        """
        پاکسازی منابع پلاگین

        Returns:
            bool: وضعیت پاکسازی
        """
        try:
            logger.info(f"پلاگین {self.name} در حال پاکسازی منابع...")

            # ذخیره تنظیمات در دیتابیس
            await self.update(
                'plugins',
                {'config': json.dumps(self.config)},
                'name = $1',
                (self.name,)
            )

            # پاکسازی مدیریت‌کننده‌ها
            await self.blocklist_manager.cleanup(self.db)
            await self.spam_controller.cleanup(self.db)
            await self.whitelist_manager.cleanup(self.db)

            # ذخیره وضعیت نوتیفیکیشن
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.notification_enabled), 'firewall_notification')
            )

            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def on_message(self, client: TelegramClient, message: Message) -> None:
        """
        پردازش پیام‌های دریافتی

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        if not self.is_enabled:
            return

        # بررسی لیست سفید
        if await self.whitelist_manager.is_whitelisted(message):
            return

        # بررسی لیست مسدود شده
        if await self.blocklist_manager.is_blocked(message):
            await self.handle_blocked_message(client, message)
            return

        # بررسی کلمات کلیدی مسدود شده
        if await self.blocklist_manager.contains_blocked_keywords(message):
            await self.handle_blocked_keyword_message(client, message)
            return

        # بررسی اسپم
        if await self.spam_controller.is_spam(message):
            await self.handle_spam_message(client, message)

    async def handle_blocked_message(self, client: TelegramClient, message: Message) -> None:
        """
        مدیریت پیام از کاربر مسدود شده

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        logger.info(f"پیام از کاربر مسدود شده {message.from_user.id if message.from_user else 'نامشخص'} حذف شد")

        # ثبت رویداد امنیتی
        await self.record_security_event("پیام از کاربر مسدود شده", {
            "user_id": message.from_user.id if message.from_user else 0,
            "username": message.from_user.username if message.from_user and message.from_user.username else "نامشخص",
            "chat_id": message.chat.id if message.chat else 0,
            "chat_title": message.chat.title if message.chat and hasattr(message.chat, 'title') \
                else "نامشخص", \
            "message_text": message.text if message.text else "(بدون متن)"
        })

        # حذف پیام
        try:
            await message.delete()
        except Exception as e:
            logger.error(f"خطا در حذف پیام از کاربر مسدود شده: {str(e)}")

    async def handle_blocked_keyword_message(self, client: TelegramClient, message: Message) \
        -> None: \
        """
        مدیریت پیام حاوی کلمات کلیدی مسدود شده

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        if not message.text:
            return

        keyword = self.blocklist_manager.find_matching_keyword(message.text)
        if not keyword:
            return

        logger.info(f"پیام حاوی کلمه کلیدی مسدود شده '{keyword}' از کاربر {message.from_user.id if message.from_user else 'نامشخص'} شناسایی شد")

        # ثبت رویداد امنیتی
        await self.record_security_event("پیام حاوی کلمه کلیدی مسدود شده", {
            "keyword": keyword,
            "user_id": message.from_user.id if message.from_user else 0,
            "username": message.from_user.username if message.from_user and message.from_user.username else "نامشخص",
            "chat_id": message.chat.id if message.chat else 0,
            "message_text": message.text
        })

        # حذف پیام
        try:
            await message.delete()
        except Exception as e:
            logger.error(f"خطا در حذف پیام حاوی کلمه کلیدی مسدود شده: {str(e)}")

        # اطلاع به کاربر
        if self.notification_enabled and message.from_user:
            try:
                await client.send_message(
                    message.chat.id,
                    f"⚠️ پیام از کاربر {message.from_user.mention()} به دلیل محتوای نامناسب حذف شد."
                )
            except Exception as e:
                logger.error(f"خطا در ارسال نوتیفیکیشن برای کلمه کلیدی مسدود شده: {str(e)}")

    async def handle_spam_message(self, client: TelegramClient, message: Message) -> None:
        """
        مدیریت پیام اسپم

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        user_id = message.from_user.id if message.from_user else 0
        message_count = self.spam_controller.get_user_message_count(user_id)

        logger.warning(f"فعالیت اسپم از کاربر {user_id} شناسایی شد! {message_count} پیام در {self.spam_controller.spam_window} ثانیه")

        # ثبت رویداد امنیتی
        await self.record_security_event("تشخیص اسپم", {
            "user_id": user_id,
            "username": message.from_user.username if message.from_user and message.from_user.username else "نامشخص",
            "chat_id": message.chat.id if message.chat else 0,
            "message_count": message_count,
            "time_window": self.spam_controller.spam_window
        })

        # حذف پیام اگر تنظیم شده باشد
        if self.spam_controller.auto_delete_spam:
            try:
                await message.delete()
            except Exception as e:
                logger.error(f"خطا در حذف پیام اسپم: {str(e)}")

        # هشدار به کاربر
        if self.notification_enabled and message.from_user:
            try:
                await client.send_message(
                    message.chat.id,
                    f"⚠️ کاربر {message.from_user.mention() \
                        }: لطفاً از ارسال پیام‌های متعدد (اسپم) خودداری کنید." \
                )
            except Exception as e:
                logger.error(f"خطا در ارسال هشدار اسپم: {str(e)}")

    async def record_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        ثبت رویداد امنیتی

        Args:
            event_type (str): نوع رویداد
            details (Dict[str, Any]): جزئیات رویداد
        """
        try:
            # دسترسی به پلاگین رویدادهای امنیتی
            security_events_plugin = self.plugin_manager.get_plugin("SecurityEvents")

            if security_events_plugin:
                # استفاده از متد پلاگین برای ثبت رویداد
                await security_events_plugin.record_security_event(
                    f"firewall_{event_type}",
                    details
                )
            else:
                # ثبت مستقیم در دیتابیس اگر پلاگین در دسترس نیست
                await self.insert('security_events', {
                    'event_type': f"firewall_{event_type}",
                    'details': json.dumps(details),
                    'is_resolved': False,
                    'created_at': 'NOW()'
                })

        except Exception as e:
            logger.error(f"خطا در ثبت رویداد امنیتی فایروال: {str(e)}")

    # دستورات مدیریت فایروال

    async def cmd_block_user(self, client: TelegramClient, message: Message) -> None:
        """
        دستور مسدود کردن کاربر
        """
        try:
            args = message.text.split()[1:]

            if not args:
                await message.reply_text("لطفاً شناسه کاربر مورد نظر را وارد کنید. مثال: `.fw_block 123456789`")
                return

            try:
                user_id = int(args[0])
            except ValueError:
                await message.reply_text("شناسه کاربر باید یک عدد صحیح باشد.")
                return

            # بررسی تکراری نبودن
            if user_id in self.blocklist_manager.blocked_users:
                await message.reply_text(f"کاربر {user_id} قبلاً در لیست مسدود شده‌ها قرار دارد.")
                return

            # افزودن به لیست مسدود شده
            await self.blocklist_manager.add_blocked_user(user_id, self.db)

            # ثبت رویداد
            await self.record_security_event("مسدود کردن کاربر", {
                "user_id": user_id,
                "blocked_by": message.from_user.id if message.from_user else 0,
                "reason": args[1] if len(args) > 1 else "دلیل ذکر نشده است"
            })

            await message.reply_text(f"✅ کاربر {user_id} به لیست مسدود شده‌ها اضافه شد.")

        except Exception as e:
            logger.error(f"خطا در اجرای دستور block_user: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")
