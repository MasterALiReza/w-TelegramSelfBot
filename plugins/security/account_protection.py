"""
پلاگین محافظت از حساب کاربری
این پلاگین امکانات امنیتی برای محافظت از حساب تلگرام را فراهم می‌کند.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import os
from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.types import Message, User
from pyrogram.errors import FloodWait, UserDeactivated, AuthKeyUnregistered

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient
from core.crypto import encrypt_data, decrypt_data, hash_password, verify_password

logger = logging.getLogger(__name__)


class AccountProtectionPlugin(BasePlugin):
    """
    پلاگین محافظت از حساب کاربری
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="AccountProtection",
            version="1.0.0",
            description="محافظت از حساب کاربری تلگرام",
            author="SelfBot Team",
            category="security"
        )
        self.suspicious_logins = []
        self.login_attempts = {}
        self.protected_dialogs = []
        self.protection_enabled = True
        self.last_online = time.time()
        self.auto_offline = False
        self.privacy_settings = {
            "hide_online": False,
            "hide_last_seen": False,
            "hide_phone": True,
            "auto_delete_messages": False,
            "auto_delete_interval": 24  # ساعت
        }

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین محافظت از حساب در حال راه‌اندازی...")

            # بارگیری تنظیمات حریم خصوصی
            privacy_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'privacy_settings'"
            )

            if privacy_config and 'value' in privacy_config:
                self.privacy_settings = json.loads(privacy_config['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('privacy_settings', json.dumps(self.privacy_settings), 'تنظیمات حریم خصوصی')
                )

            # بارگیری دیالوگ‌های محافظت شده
            protected_dialogs = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'protected_dialogs'"
            )

            if protected_dialogs and 'value' in protected_dialogs:
                self.protected_dialogs = json.loads(protected_dialogs['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('protected_dialogs', json.dumps(self.protected_dialogs), 'چت‌های محافظت شده')
                )

            # ثبت دستورات
            self.register_command('protect', self.cmd_protect_chat, 'محافظت از یک چت', '.protect [چت_آیدی]')
            self.register_command('unprotect', self.cmd_unprotect_chat, 'حذف محافظت از یک چت', '.unprotect [چت_آیدی]')
            self.register_command('privacy', self.cmd_privacy_settings, 'تنظیمات حریم خصوصی', '.privacy [پارامتر] [مقدار]')
            self.register_command('offline', self.cmd_go_offline, 'مخفی کردن وضعیت آنلاین', '.offline')
            self.register_command('online', self.cmd_go_online, 'نمایش وضعیت آنلاین', '.online')
            self.register_command('lock', self.cmd_lock_account, 'قفل کردن حساب کاربری', '.lock [رمز]')
            self.register_command('unlock', self.cmd_unlock_account, 'باز کردن قفل حساب کاربری', '.unlock [رمز]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.NEW_LOGIN, self.on_new_login, {})
            self.register_event_handler(EventType.MESSAGE, self.on_message, {})
            self.register_event_handler(EventType.MESSAGE, self.on_protect_command, {'text_startswith': ['.protect', '/protect', '!protect']})
            self.register_event_handler(EventType.MESSAGE, self.on_unprotect_command, {'text_startswith': ['.unprotect', '/unprotect', '!unprotect']})
            self.register_event_handler(EventType.MESSAGE, self.on_privacy_command, {'text_startswith': ['.privacy', '/privacy', '!privacy']})
            self.register_event_handler(EventType.MESSAGE, self.on_offline_command, {'text_startswith': ['.offline', '/offline', '!offline']})
            self.register_event_handler(EventType.MESSAGE, self.on_online_command, {'text_startswith': ['.online', '/online', '!online']})
            self.register_event_handler(EventType.MESSAGE, self.on_lock_command, {'text_startswith': ['.lock', '/lock', '!lock']})
            self.register_event_handler(EventType.MESSAGE, self.on_unlock_command, {'text_startswith': ['.unlock', '/unlock', '!unlock']})

            # زمان‌بندی بررسی دوره‌ای
            self.schedule(self.check_security, interval=3600, name="security_check")  # هر ساعت

            # اگر حذف خودکار پیام فعال است، زمان‌بندی کن
            if self.privacy_settings.get("auto_delete_messages", False):
                self.schedule(self.auto_delete_old_messages, interval=3600, name="auto_delete_messages") \
                    \ \
                    \ \
                    # هر ساعت \

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

            # ذخیره تنظیمات حریم خصوصی
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.privacy_settings), 'privacy_settings')
            )

            # ذخیره دیالوگ‌های محافظت شده
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.protected_dialogs), 'protected_dialogs')
            )

            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def check_security(self) -> None:
        """
        بررسی دوره‌ای امنیت حساب
        """
        try:
            logger.info("در حال بررسی دوره‌ای امنیت حساب...")

            # بررسی تلاش‌های ورود مشکوک
            suspicious_count = len(self.suspicious_logins)
            if suspicious_count > 0:
                logger.warning(f"{suspicious_count} تلاش ورود مشکوک شناسایی شده است")

            # اگر خروج خودکار فعال است
            if self.auto_offline and (time.time() - self.last_online) > 3600:  # یک ساعت
                logger.info("در حال تنظیم وضعیت به آفلاین...")
                try:
                    client = self.client
                    if client and client.is_connected:
                        await client.set_offline()
                except Exception as e:
                    logger.error(f"خطا در تنظیم وضعیت آفلاین: {str(e)}")

        except Exception as e:
            logger.error(f"خطا در بررسی دوره‌ای امنیت: {str(e)}")

    async def auto_delete_old_messages(self) -> None:
        """
        حذف خودکار پیام‌های قدیمی
        """
        try:
            if not self.privacy_settings.get("auto_delete_messages", False):
                return

            interval_hours = self.privacy_settings.get("auto_delete_interval", 24)
            cutoff_time = datetime.now() - timedelta(hours=interval_hours)
            cutoff_timestamp = cutoff_time.timestamp()

            logger.info(f"در حال حذف پیام‌های قدیمیتر از {interval_hours} ساعت...")

            # دریافت پیام‌های قدیمی
            old_messages = await self.fetch_all(
                """
                SELECT message_id, chat_id
                FROM message_history
                WHERE is_outgoing = TRUE AND created_at < $1
                """,
                (cutoff_timestamp,)
            )

            client = self.client
            if not client or not client.is_connected:
                logger.warning("کلاینت متصل نیست. انجام حذف پیام‌ها به تعویق افتاد.")
                return

            deleted_count = 0
            for msg in old_messages:
                try:
                    await client.delete_messages(msg['chat_id'], msg['message_id'])

                    # حذف از دیتابیس
                    await self.delete(
                        'message_history',
                        'message_id = $1 AND chat_id = $2',
                        (msg['message_id'], msg['chat_id'])
                    )

                    deleted_count += 1

                    # تأخیر کوتاه برای جلوگیری از flood wait
                    await asyncio.sleep(0.5)

                except FloodWait as e:
                    # تأخیر به دلیل محدودیت ریت لیمیت
                    await asyncio.sleep(e.x)
                except Exception as e:
                    logger.error(f"خطا در حذف پیام: {str(e)}")

            logger.info(f"{deleted_count} پیام حذف شد")

        except Exception as e:
            logger.error(f"خطا در حذف خودکار پیام‌ها: {str(e)}")

    async def on_new_login(self, client: TelegramClient, data: Dict[str, Any]) -> None:
        """
        هندلر ورود جدید

        Args:
            client: کلاینت تلگرام
            data: اطلاعات ورود
        """
        try:
            # بررسی دستگاه مشکوک
            device_model = data.get('device_model', 'Unknown')
            system_version = data.get('system_version', 'Unknown')
            app_version = data.get('app_version', 'Unknown')
            ip_address = data.get('ip_address', 'Unknown')
            location = data.get('location', 'Unknown')
            date_time = data.get('date_time', datetime.now().isoformat())

            # افزودن به لیست مشکوک
            self.suspicious_logins.append({
                'device_model': device_model,
                'system_version': system_version,
                'app_version': app_version,
                'ip_address': ip_address,
                'location': location,
                'date_time': date_time
            })

            # ارسال هشدار به ادمین
            warning_message = f"""
⚠️ **هشدار ورود جدید**

📱 **دستگاه:** {device_model} ({system_version})
🔗 **آیپی ادرس:** {ip_address}
📍 **موقعیت:** {location}
📅 **زمان:** {date_time}

اگر این ورود توسط شما انجام نشده، لطفاً مراحل امنیتی را بررسی کنید.
            """

            # ارسال پیام به خودتان (اگر امکان دارد)
            try:
                my_id = (await client.get_me()).id
                await client.send_message(my_id, warning_message)
            except Exception as e:
                logger.error(f"خطا در ارسال هشدار ورود: {str(e)}")

            # ذخیره در دیتابیس
            await self.insert('security_events', {
                'event_type': 'new_login',
                'details': json.dumps({
                    'device_model': device_model,
                    'system_version': system_version,
                    'app_version': app_version,
                    'ip_address': ip_address,
                    'location': location,
                    'date_time': date_time
                }),
                'is_resolved': False,
                'created_at': 'NOW()'
            })

        except Exception as e:
            logger.error(f"خطا در هندلر ورود جدید: {str(e)}")

    async def cmd_protect_chat(self, client: TelegramClient, message: Message) -> None:
        """
        دستور محافظت از یک چت

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            # اگر آرگومانی نداریم، فرض می‌کنیم چت فعلی مد نظر است
            chat_id = message.chat.id
            if args:
                try:
                    chat_id = int(args[0])
                except ValueError:
                    # اگر به صورت یوزرنیم باشد
                    chat = await client.get_chat(args[0])
                    chat_id = chat.id

            # بررسی وجود چت در لیست محافظت شده
            if chat_id in self.protected_dialogs:
                await message.reply_text(self._("chat_already_protected", default="این چت در حال حاضر محافظت شده است."))
                return

            # افزودن چت به لیست محافظت شده
            self.protected_dialogs.append(chat_id)

            # ذخیره در دیتابیس
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.protected_dialogs), 'protected_dialogs')
            )

            # دریافت اطلاعات چت
            try:
                chat = await client.get_chat(chat_id)
                chat_title = chat.title if hasattr(chat, 'title') \
                    else chat.first_name if hasattr(chat, 'first_name') \
                    else str(chat_id) \
            except Exception:
                chat_title = str(chat_id)

            # افزودن یا بروزرسانی اطلاعات چت در دیتابیس
            chat_info = await self.fetch_one("SELECT id FROM chats WHERE id = $1", (chat_id,))
            if chat_info:
                await self.update(
                    'chats',
                    {
                        'is_managed': True,
                        'updated_at': 'NOW()'
                    },
                    'id = $1',
                    (chat_id,)
                )
            else:
                await self.insert('chats', {
                    'id': chat_id,
                    'title': chat_title,
                    'type': 'private' if hasattr(chat, 'first_name') \
                        else 'group' if hasattr(chat, 'title') else 'unknown', \
                    'is_managed': True
                })

            # ارسال پاسخ
            await message.reply_text(self._("chat_protected", default=f"چت {chat_title} به لیست محافظت شده اضافه شد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور protect: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_unprotect_chat(self, client: TelegramClient, message: Message) -> None:
        """
        دستور حذف محافظت از یک چت

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            # اگر آرگومانی نداریم، فرض می‌کنیم چت فعلی مد نظر است
            chat_id = message.chat.id
            if args:
                try:
                    chat_id = int(args[0])
                except ValueError:
                    # اگر به صورت یوزرنیم باشد
                    chat = await client.get_chat(args[0])
                    chat_id = chat.id

            # بررسی وجود چت در لیست محافظت شده
            if chat_id not in self.protected_dialogs:
                await message.reply_text(self._("chat_not_protected", default="این چت در لیست محافظت شده نیست."))
                return

            # حذف چت از لیست محافظت شده
            self.protected_dialogs.remove(chat_id)

            # ذخیره در دیتابیس
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.protected_dialogs), 'protected_dialogs')
            )

            # بروزرسانی در دیتابیس
            await self.update(
                'chats',
                {
                    'is_managed': False,
                    'updated_at': 'NOW()'
                },
                'id = $1',
                (chat_id,)
            )

            # دریافت اطلاعات چت
            try:
                chat = await client.get_chat(chat_id)
                chat_title = chat.title if hasattr(chat, 'title') \
                    else chat.first_name if hasattr(chat, 'first_name') \
                    else str(chat_id) \
            except Exception:
                chat_title = str(chat_id)

            # ارسال پاسخ
            await message.reply_text(self._("chat_unprotected", default=f"چت {chat_title} از لیست محافظت شده حذف شد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور unprotect: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def on_message(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر پیام‌ها برای محافظت از چت

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        # بروزرسانی زمان آنلاین
        if message.outgoing:
            self.last_online = time.time()

        # اگر چت در لیست محافظت شده است
        if message.chat and message.chat.id in self.protected_dialogs:
            # ذخیره تاریخچه پیام
            if message.text or message.caption:
                content = message.text or message.caption
                try:
                    await self.insert('message_history', {
                        'message_id': message.id,
                        'user_id': message.from_user.id if message.from_user else None,
                        'chat_id': message.chat.id,
                        'message_type': 'text',
                        'content': content,
                        'is_outgoing': message.outgoing
                    })
                except Exception as e:
                    logger.error(f"خطا در ذخیره تاریخچه پیام: {str(e)}")

    async def on_protect_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور محافظت از چت

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_protect_chat(client, message)

    async def on_unprotect_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور حذف محافظت از چت

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_unprotect_chat(client, message)
