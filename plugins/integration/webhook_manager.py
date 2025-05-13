"""
پلاگین مدیریت وب‌هوک‌ها
این پلاگین امکان ارسال رویدادها به وب‌هوک‌های مختلف را فراهم می‌کند.
"""
import asyncio
import logging
import json
from typing import Any, Dict
from datetime import datetime

import aiohttp
from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient
from core.crypto import decrypt_data

logger = logging.getLogger(__name__)


class WebhookManager(BasePlugin):
    """
    پلاگین مدیریت وب‌هوک‌ها
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="WebhookManager",
            version="1.0.0",
            description="مدیریت ارسال رویدادها به وب‌هوک‌های خارجی",
            author="SelfBot Team",
            category="integration"
        )

        self.webhooks = {}  # {name: {url, events: [], secret, enabled}}
        self.webhook_enabled = True
        self.timeout = 10.0  # زمان انتظار برای ارسال وب‌هوک (ثانیه)

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین مدیریت وب‌هوک‌ها در حال راه‌اندازی...")

            # بارگیری وضعیت فعال/غیرفعال
            webhook_status = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'webhook_enabled'"
            )

            if webhook_status and 'value' in webhook_status:
                self.webhook_enabled = json.loads(webhook_status['value'])
            else:
                # مقدار پیش‌فرض
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('webhook_enabled', json.dumps(self.webhook_enabled), 'فعال‌سازی سیستم وب‌هوک')
                )

            # بارگیری وب‌هوک‌ها
            webhooks_data = await self.fetch_all(
                "SELECT * FROM webhooks"
            )

            if webhooks_data:
                for webhook in webhooks_data:
                    # رمزگشایی رمز وب‌هوک در صورت وجود
                    secret = None
                    if webhook.get('secret'):
                        secret = await decrypt_data(webhook['secret'])

                    self.webhooks[webhook['name']] = {
                        'url': webhook['url'],
                        'events': json.loads(webhook['events']),
                        'secret': secret,
                        'enabled': webhook['enabled']
                    }

            # ثبت دستورات
            self.register_command('webhook_add', self.cmd_add_webhook, 'افزودن وب‌هوک جدید', '.webhook_add [name] [url] [event1,event2,...]')
            self.register_command('webhook_list', self.cmd_list_webhooks, 'نمایش لیست وب‌هوک‌ها', '.webhook_list')
            self.register_command('webhook_delete', self.cmd_delete_webhook, 'حذف وب‌هوک', '.webhook_delete [name]')
            self.register_command('webhook_toggle', self.cmd_toggle_webhook, 'فعال/غیرفعال‌سازی وب‌هوک', '.webhook_toggle [name]')
            self.register_command('webhook_test', self.cmd_test_webhook, 'تست وب‌هوک', '.webhook_test [name]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_message, {})
            self.register_event_handler(EventType.NEW_CHAT_MEMBER, self.on_new_chat_member, {})
            self.register_event_handler(EventType.LEFT_CHAT_MEMBER, self.on_left_chat_member, {})

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
            # ذخیره وضعیت وب‌هوک‌ها
            await self.save_webhook_status()
            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def save_webhook_status(self) -> None:
        """
        ذخیره وضعیت وب‌هوک‌ها در دیتابیس
        """
        try:
            # ذخیره وضعیت فعال/غیرفعال
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.webhook_enabled), 'webhook_enabled')
            )
        except Exception as e:
            logger.error(f"خطا در ذخیره وضعیت وب‌هوک‌ها: {str(e)}")

    async def send_webhook(self, webhook_name: str, data: Dict[str, Any]) -> bool:
        """
        ارسال داده به آدرس وب‌هوک

        Args:
            webhook_name: نام وب‌هوک
            data: داده برای ارسال

        Returns:
            bool: وضعیت ارسال
        """
        if not self.webhook_enabled or webhook_name not in self.webhooks or not self.webhooks[webhook_name]['enabled']:
            return False

        webhook = self.webhooks[webhook_name]
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'TelegramSelfBot/{self.version}'
        }

        # افزودن رمز در صورت وجود
        if webhook['secret']:
            headers['X-Webhook-Secret'] = webhook['secret']

        # افزودن زمان ارسال
        data['timestamp'] = datetime.now().isoformat()
        data['webhook_name'] = webhook_name

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook['url'],
                    headers=headers,
                    json=data,
                    timeout=self.timeout
                ) as response:
                    return response.status < 400
        except Exception as e:
            logger.error(f"خطا در ارسال وب‌هوک {webhook_name}: {str(e)}")
            return False

    async def on_message(self, client: TelegramClient, message: Message) -> None:
        """
        پردازش رویداد پیام جدید

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        if not self.webhook_enabled:
            return

        # بررسی وب‌هوک‌های مرتبط با رویداد پیام
        event_type = "message"
        for webhook_name, webhook in self.webhooks.items():
            if webhook['enabled'] and event_type in webhook['events']:
                # آماده‌سازی داده برای ارسال
                data = {
                    'event_type': event_type,
                    'message_id': message.id,
                    'chat_id': message.chat.id,
                    'chat_title': message.chat.title if hasattr(message.chat, 'title') else "",
                    'sender_id': message.from_user.id if message.from_user else None,
                    'sender_name': f"{message.from_user.first_name} {message.from_user.last_name if message.from_user.last_name else ''}" if message.from_user else "",
                    'text': message.text or "",
                    'date': message.date.isoformat() if message.date else "",
                    'is_outgoing': message.outgoing,
                    'has_media': bool(message.media) or bool(message.photo),
                }

                asyncio.create_task(self.send_webhook(webhook_name, data))

    async def on_new_chat_member(self, client: TelegramClient, message: Message) -> None:
        """
        پردازش رویداد عضو جدید گروه

        Args:
            client: کلاینت تلگرام
            message: پیام حاوی رویداد
        """
        if not self.webhook_enabled:
            return

        event_type = "new_chat_member"
        for webhook_name, webhook in self.webhooks.items():
            if webhook['enabled'] and event_type in webhook['events']:
                # آماده‌سازی داده برای ارسال
                data = {
                    'event_type': event_type,
                    'chat_id': message.chat.id,
                    'chat_title': message.chat.title if hasattr(message.chat, 'title') else "",
                }

                # افزودن اطلاعات اعضای جدید
                if hasattr(message, 'new_chat_members') and message.new_chat_members:
                    data['new_members'] = []
                    for user in message.new_chat_members:
                        data['new_members'].append({
                            'user_id': user.id,
                            'username': user.username or "",
                            'name': f"{user.first_name} {user.last_name if user.last_name else ''}"
                        })

                asyncio.create_task(self.send_webhook(webhook_name, data))

    async def on_left_chat_member(self, client: TelegramClient, message: Message) -> None:
        """
        پردازش رویداد خروج عضو از گروه

        Args:
            client: کلاینت تلگرام
            message: پیام حاوی رویداد
        """
        if not self.webhook_enabled:
            return

        event_type = "left_chat_member"
        for webhook_name, webhook in self.webhooks.items():
            if webhook['enabled'] and event_type in webhook['events']:
                # آماده‌سازی داده برای ارسال
                data = {
                    'event_type': event_type,
                    'chat_id': message.chat.id,
                    'chat_title': message.chat.title if hasattr(message.chat, 'title') else "",
                }

                # افزودن اطلاعات عضو خارج شده
                if hasattr(message, 'left_chat_member') and message.left_chat_member:
                    user = message.left_chat_member
                    data['left_member'] = {
                        'user_id': user.id,
                        'username': user.username or "",
                        'name': f"{user.first_name} {user.last_name if user.last_name else ''}"
                    }

                asyncio.create_task(self.send_webhook(webhook_name, data))
