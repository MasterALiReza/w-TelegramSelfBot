"""
پلاگین پاسخ خودکار
این پلاگین امکان تنظیم پاسخ‌های خودکار به پیام‌های دریافتی را فراهم می‌کند.
"""
import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import json

from pyrogram import filters
from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient
from core.database.sql import PostgreSQLDatabase

logger = logging.getLogger(__name__)


class AutoResponderPlugin(BasePlugin):
    """
    پلاگین پاسخ خودکار به پیام‌ها
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="AutoResponder",
            version="1.0.0",
            description="مدیریت پاسخ‌های خودکار به پیام‌ها",
            author="SelfBot Team",
            category="tools"
        )
        self.auto_responses = []
        self.enabled = True

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین پاسخ خودکار در حال راه‌اندازی...")

            # دریافت وضعیت فعال/غیرفعال بودن
            enabled_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'auto_response_enabled'"
            )

            if enabled_config and 'value' in enabled_config:
                self.enabled = json.loads(enabled_config['value'])
            else:
                # مقدار پیش‌فرض
                self.enabled = True
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('auto_response_enabled', json.dumps(self.enabled), 'فعال‌سازی پاسخ خودکار')
                )

            # بارگیری پاسخ‌های خودکار از دیتابیس
            responses = await self.fetch_all(
                """
                SELECT id, user_id, trigger_type, trigger_value, response_text, is_enabled, priority
                FROM auto_responses
                WHERE is_enabled = TRUE
                ORDER BY priority DESC
                """
            )

            self.auto_responses = responses

            # ثبت دستورات
            self.register_command('ar_add', self.cmd_add_response, 'افزودن پاسخ خودکار', '.ar_add [text|regex] [trigger] [response]')
            self.register_command('ar_del', self.cmd_del_response, 'حذف پاسخ خودکار', '.ar_del [شناسه]')
            self.register_command('ar_list', self.cmd_list_responses, 'مشاهده لیست پاسخ‌های خودکار', '.ar_list')
            self.register_command('ar_toggle', self.cmd_toggle_auto_response, 'فعال/غیرفعال‌سازی پاسخ خودکار', '.ar_toggle')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_add_response_command, {'text_startswith': ['.ar_add', '/ar_add', '!ar_add']})
            self.register_event_handler(EventType.MESSAGE, self.on_del_response_command, {'text_startswith': ['.ar_del', '/ar_del', '!ar_del']})
            self.register_event_handler(EventType.MESSAGE, self.on_list_responses_command, {'text_startswith': ['.ar_list', '/ar_list', '!ar_list']})
            self.register_event_handler(EventType.MESSAGE, self.on_toggle_auto_response_command, {'text_startswith': ['.ar_toggle', '/ar_toggle', '!ar_toggle']})
            self.register_event_handler(EventType.MESSAGE, self.on_message, {'is_private': True})
            self.register_event_handler(EventType.MESSAGE, self.on_message, {'is_group': True})

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

            # ذخیره وضعیت فعال/غیرفعال بودن
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.enabled), 'auto_response_enabled')
            )

            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def cmd_add_response(self, client: TelegramClient, message: Message) -> None:
        """
        دستور افزودن پاسخ خودکار

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""

            if not text:
                await message.reply_text(self._("invalid_add_response_command", default="دستور نامعتبر است. استفاده صحیح: `.ar_add [text|regex] [trigger] [response]`"))
                return

            # تجزیه پارامترها
            parts = text.split(maxsplit=2)

            if len(parts) < 3:
                await message.reply_text(self._("invalid_add_response_command", default="دستور نامعتبر است. استفاده صحیح: `.ar_add [text|regex] [trigger] [response]`"))
                return

            trigger_type = parts[0].lower()
            trigger_value = parts[1]
            response_text = parts[2]

            if trigger_type not in ['text', 'regex']:
                await message.reply_text(self._("invalid_trigger_type", default="نوع تریگر نامعتبر است. گزینه‌های مجاز: text, regex"))
                return

            # بررسی معتبر بودن regex
            if trigger_type == 'regex':
                try:
                    re.compile(trigger_value)
                except re.error:
                    await message.reply_text(self._("invalid_regex", default="الگوی regex نامعتبر است."))
                    return

            # افزودن به دیتابیس
            auto_response = await self.insert('auto_responses', {
                'user_id': message.from_user.id,
                'trigger_type': trigger_type,
                'trigger_value': trigger_value,
                'response_text': response_text,
                'is_enabled': True,
                'priority': 0
            })

            if auto_response:
                # افزودن به لیست در حافظه
                self.auto_responses.append(auto_response)

                await message.reply_text(self._("response_added", default=f"پاسخ خودکار با شناسه {auto_response['id']} اضافه شد."))
            else:
                await message.reply_text(self._("response_add_failed", default="افزودن پاسخ خودکار با خطا مواجه شد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور ar_add: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_del_response(self, client: TelegramClient, message: Message) -> None:
        """
        دستور حذف پاسخ خودکار

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if not args:
                await message.reply_text(self._("invalid_del_response_command", default="دستور نامعتبر است. استفاده صحیح: `.ar_del [شناسه]`"))
                return

            try:
                response_id = int(args[0])
            except ValueError:
                await message.reply_text(self._("invalid_response_id", default="شناسه پاسخ خودکار نامعتبر است."))
                return

            # حذف از دیتابیس
            deleted = await self.delete('auto_responses', 'id = $1', (response_id,))

            if deleted > 0:
                # حذف از لیست در حافظه
                self.auto_responses = [r for r in self.auto_responses if r['id'] != response_id]

                await message.reply_text(self._("response_deleted", default=f"پاسخ خودکار با شناسه {response_id} حذف شد."))
            else:
                await message.reply_text(self._("response_not_found", default="پاسخ خودکار با شناسه مورد نظر یافت نشد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور ar_del: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_list_responses(self, client: TelegramClient, message: Message) -> None:
        """
        دستور مشاهده لیست پاسخ‌های خودکار

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت لیست پاسخ‌های خودکار از دیتابیس
            responses = await self.fetch_all(
                """
                SELECT id, trigger_type, trigger_value, response_text, is_enabled, priority
                FROM auto_responses
                ORDER BY priority DESC, id ASC
                """
            )

            if not responses:
                await message.reply_text(self._("no_responses_found", default="پاسخ خودکاری یافت نشد."))
                return

            # ساخت پاسخ
            response_text = self._("auto_responses_list_header", default="📋 **لیست پاسخ‌های خودکار**\n\n")

            for resp in responses:
                status = "✅" if resp['is_enabled'] else "❌"
                trigger_info = f"`{resp['trigger_value']}`" if len(resp['trigger_value']) \
                    < 30 else f"`{resp['trigger_value'][:27]}...`" \
                response_info = f"`{resp['response_text']}`" if len(resp['response_text']) \
                    < 30 else f"`{resp['response_text'][:27]}...`" \

                response_text += f"**{resp['id']}**: {status} ({resp['trigger_type']})\n"
                response_text += f"  🔍 Trigger: {trigger_info}\n"
                response_text += f"  💬 Response: {response_info}\n\n"

            # ارسال پاسخ
            await message.reply_text(response_text)

        except Exception as e:
            logger.error(f"خطا در اجرای دستور ar_list: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_toggle_auto_response(self, client: TelegramClient, message: Message) -> None:
        """
        دستور فعال/غیرفعال‌سازی پاسخ خودکار

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # تغییر وضعیت
            self.enabled = not self.enabled

            # ذخیره در دیتابیس
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.enabled), 'auto_response_enabled')
            )

            # ارسال پاسخ
            status = "فعال" if self.enabled else "غیرفعال"
            await message.reply_text(self._("auto_response_toggled", default=f"سیستم پاسخ خودکار {status} شد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور ar_toggle: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def on_message(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر پیام‌ها برای پاسخ خودکار

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        # اگر سیستم غیرفعال است یا پیام از خودمان است، نادیده بگیر
        if not self.enabled or message.outgoing:
            return

        if not message.text:
            return

        # بررسی همه پاسخ‌های خودکار
        for response in self.auto_responses:
            if not response['is_enabled']:
                continue

            matched = False

            # بررسی تطابق با پترن
            if response['trigger_type'] == 'text':
                if response['trigger_value'].lower() in message.text.lower():
                    matched = True
            elif response['trigger_type'] == 'regex':
                try:
                    if re.search(response['trigger_value'], message.text, re.IGNORECASE):
                        matched = True
                except re.error:
                    logger.error(f"خطا در الگوی regex: {response['trigger_value']}")

            # در صورت تطابق، پاسخ ارسال شود
            if matched:
                try:
                    await message.reply_text(response['response_text'])

                    # در اینجا می‌توان آمار استفاده از پاسخ‌های خودکار را ثبت کرد
                    logger.info(f"پاسخ خودکار با شناسه {response['id']} استفاده شد")

                    # فقط اولین پاسخ مطابق استفاده شود
                    break

                except Exception as e:
                    logger.error(f"خطا در ارسال پاسخ خودکار: {str(e)}")

    async def on_add_response_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور افزودن پاسخ خودکار

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_add_response(client, message)

    async def on_del_response_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور حذف پاسخ خودکار

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_del_response(client, message)

    async def on_list_responses_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور مشاهده لیست پاسخ‌های خودکار

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_list_responses(client, message)

    async def on_toggle_auto_response_command(self, client: TelegramClient, message: Message) \
        -> None: \
        """
        هندلر دستور فعال/غیرفعال‌سازی پاسخ خودکار

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_toggle_auto_response(client, message)
