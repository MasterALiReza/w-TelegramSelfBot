"""
پلاگین ثبت و گزارش رویدادهای امنیتی
این پلاگین رویدادهای امنیتی حساب کاربری را ثبت و گزارش می‌کند.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import json
from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient

logger = logging.getLogger(__name__)


class SecurityEventsPlugin(BasePlugin):
    """
    پلاگین ثبت و گزارش رویدادهای امنیتی
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="SecurityEvents",
            version="1.0.0",
            description="ثبت و گزارش رویدادهای امنیتی",
            author="SelfBot Team",
            category="security"
        )
        self.security_events = []
        self.admin_notifications = True

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین رویدادهای امنیتی در حال راه‌اندازی...")

            # دریافت وضعیت نوتیفیکیشن‌ها
            notification_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'admin_notifications'"
            )

            if notification_config and 'value' in notification_config:
                self.admin_notifications = json.loads(notification_config['value'])
            else:
                # مقدار پیش‌فرض
                self.admin_notifications = True
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('admin_notifications', json.dumps(self.admin_notifications), 'نوتیفیکیشن‌های ادمین')
                )

            # ثبت دستورات
            self.register_command('events', self.cmd_list_events, 'مشاهده رویدادهای امنیتی', '.events [count]')
            self.register_command('clear_events', self.cmd_clear_events, 'پاکسازی رویدادهای امنیتی', '.clear_events')
            self.register_command('notify', self.cmd_toggle_notifications, 'فعال/غیرفعال‌سازی نوتیفیکیشن‌ها', '.notify [on|off]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_list_events_command, {'text_startswith': ['.events', '/events', '!events']})
            self.register_event_handler(EventType.MESSAGE, self.on_clear_events_command, {'text_startswith': ['.clear_events', '/clear_events', '!clear_events']})
            self.register_event_handler(EventType.MESSAGE, self.on_toggle_notifications_command, {'text_startswith': ['.notify', '/notify', '!notify']})

            # زمان‌بندی بررسی دوره‌ای
            self.schedule(self.clean_old_events, interval=86400, name="clean_old_events") \
                # هر 24 ساعت \

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

            # ذخیره وضعیت نوتیفیکیشن‌ها
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.admin_notifications), 'admin_notifications')
            )

            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def record_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        ثبت یک رویداد امنیتی

        Args:
            event_type: نوع رویداد
            details: جزئیات رویداد
        """
        try:
            # ثبت در دیتابیس
            event = await self.insert('security_events', {
                'event_type': event_type,
                'details': json.dumps(details),
                'is_resolved': False,
                'created_at': 'NOW()'
            })

            if event:
                self.security_events.append(event)

                # اگر نوتیفیکیشن‌ها فعال است، به ادمین اطلاع بده
                if self.admin_notifications:
                    try:
                        # دریافت اطلاعات ادمین‌ها
                        admin_config = await self.fetch_one(
                            "SELECT value FROM settings WHERE key = 'admin_users'"
                        )

                        if admin_config and 'value' in admin_config:
                            admin_users = json.loads(admin_config['value'])

                            if admin_users:
                                client = self.client
                                if client and client.is_connected:
                                    # ساخت پیام
                                    message = f"""
⚠️ **رویداد امنیتی جدید**

🔐 **نوع:** {event_type}
📅 **زمان:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🆔 **شناسه رویداد:** {event['id']}

📝 **جزئیات:**
```
{json.dumps(details, indent=2, ensure_ascii=False)}
```

برای مشاهده همه رویدادها، از دستور `.events` استفاده کنید.
"""
                                    # ارسال به ادمین‌ها
                                    for admin_id in admin_users:
                                        try:
                                            await client.send_message(admin_id, message)
                                        except Exception as e:
                                            logger.error(f"خطا در ارسال نوتیفیکیشن به ادمین {admin_id}: {str(e)}")
                    except Exception as e:
                        logger.error(f"خطا در ارسال نوتیفیکیشن برای رویداد امنیتی: {str(e)}")

        except Exception as e:
            logger.error(f"خطا در ثبت رویداد امنیتی: {str(e)}")

    async def clean_old_events(self) -> None:
        """
        پاکسازی رویدادهای امنیتی قدیمی
        """
        try:
            # رویدادهای قدیمی‌تر از 30 روز را پاک می‌کنیم
            cutoff_date = datetime.now() - timedelta(days=30)

            # حذف از دیتابیس
            deleted = await self.db.execute(
                "DELETE FROM security_events WHERE created_at < $1 AND is_resolved = TRUE",
                (cutoff_date,)
            )

            if deleted:
                logger.info(f"{deleted} رویداد امنیتی قدیمی پاکسازی شد")

        except Exception as e:
            logger.error(f"خطا در پاکسازی رویدادهای امنیتی قدیمی: {str(e)}")

    async def cmd_list_events(self, client: TelegramClient, message: Message) -> None:
        """
        دستور مشاهده رویدادهای امنیتی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            # تعداد رویدادها
            count = 10  # پیش‌فرض
            if args and args[0].isdigit():
                count = int(args[0])
                count = min(count, 50)  # حداکثر 50 رویداد

            # دریافت رویدادها از دیتابیس
            events = await self.fetch_all(
                """
                SELECT id, event_type, details, is_resolved, created_at
                FROM security_events
                ORDER BY created_at DESC
                LIMIT $1
                """,
                (count,)
            )

            if not events:
                await message.reply_text(self._("no_security_events", default="رویداد امنیتی‌ای یافت نشد."))
                return

            # ساخت پاسخ
            response = self._("security_events_header", default="🔐 **رویدادهای امنیتی**\n\n")

            for event in events:
                event_time = event['created_at'].strftime('%Y-%m-%d %H:%M:%S') \
                    if hasattr(event['created_at'], 'strftime') else str(event['created_at']) \
                status = "✅" if event['is_resolved'] else "⏳"

                response += f"**{event['id']}**: {status} **{event['event_type']}** - {event_time}\n"

                # اضافه کردن جزئیات به صورت مختصر
                try:
                    details = json.loads(event['details'])
                    detail_str = ", ".join([f"{k}: {v}" for k, v in details.items()])
                    if len(detail_str) > 100:
                        detail_str = detail_str[:97] + "..."
                    response += f"    {detail_str}\n\n"
                except Exception:
                    response += f"    {event['details'][:100]}\n\n"

            # ارسال پاسخ
            await message.reply_text(response)

        except Exception as e:
            logger.error(f"خطا در اجرای دستور events: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_clear_events(self, client: TelegramClient, message: Message) -> None:
        """
        دستور پاکسازی رویدادهای امنیتی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # حذف رویدادهای قطعی شده
            deleted = await self.db.execute(
                "DELETE FROM security_events WHERE is_resolved = TRUE"
            )

            # ارسال پاسخ
            await message.reply_text(self._("events_cleared", default=f"{deleted} رویداد امنیتی حل‌شده پاکسازی شد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور clear_events: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_toggle_notifications(self, client: TelegramClient, message: Message) -> None:
        """
        دستور فعال/غیرفعال‌سازی نوتیفیکیشن‌ها

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if args and args[0].lower() in ['on', 'off']:
                self.admin_notifications = args[0].lower() == 'on'
            else:
                # تغییر وضعیت فعلی
                self.admin_notifications = not self.admin_notifications

            # ذخیره در دیتابیس
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.admin_notifications), 'admin_notifications')
            )

            # ارسال پاسخ
            status = "فعال" if self.admin_notifications else "غیرفعال"
            await message.reply_text(self._("notifications_toggled", default=f"نوتیفیکیشن‌های امنیتی {status} شد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور notify: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def on_list_events_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور مشاهده رویدادهای امنیتی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_list_events(client, message)

    async def on_clear_events_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور پاکسازی رویدادهای امنیتی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_clear_events(client, message)

    async def on_toggle_notifications_command(self, client: TelegramClient, message: Message) \
        -> None: \
        """
        هندلر دستور فعال/غیرفعال‌سازی نوتیفیکیشن‌ها

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_toggle_notifications(client, message)
