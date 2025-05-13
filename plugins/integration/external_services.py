"""
پلاگین اتصال به سرویس‌های خارجی
این پلاگین امکان اتصال به سرویس‌های مختلف مانند Trello، GitHub و سایر APIها را فراهم می‌کند.
"""
import asyncio
import logging
import json
import time
import hmac
import hashlib
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import os

import aiohttp
from pyrogram import filters
from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient
from core.crypto import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class ExternalServicesConnector(BasePlugin):
    """
    پلاگین اتصال به سرویس‌های خارجی
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="ExternalServicesConnector",
            version="1.0.0",
            description="اتصال به سرویس‌های خارجی مانند Trello، GitHub و غیره",
            author="SelfBot Team",
            category="integration"
        )

        self.services = {}  # {name: {type, config, enabled}}
        self.timeout = 30.0  # زمان انتظار برای ارسال درخواست‌ها (ثانیه)
        self.service_types = ["github", "trello", "notion", "generic_api"]

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین اتصال به سرویس‌های خارجی در حال راه‌اندازی...")

            # بارگیری سرویس‌ها
            services_data = await self.fetch_all(
                "SELECT * FROM external_services"
            )

            if services_data:
                for service in services_data:
                    # رمزگشایی اطلاعات حساس
                    config = json.loads(service['config'])
                    if 'api_key' in config and config['api_key']:
                        config['api_key'] = await decrypt_data(config['api_key'])
                    if 'api_secret' in config and config['api_secret']:
                        config['api_secret'] = await decrypt_data(config['api_secret'])
                    if 'token' in config and config['token']:
                        config['token'] = await decrypt_data(config['token'])

                    self.services[service['name']] = {
                        'type': service['type'],
                        'config': config,
                        'enabled': service['enabled']
                    }

            # ثبت دستورات
            self.register_command('service_add', self.cmd_add_service, 'افزودن سرویس خارجی جدید', '.service_add [name] [type] [params...]')
            self.register_command('service_list', self.cmd_list_services, 'نمایش لیست سرویس‌های متصل', '.service_list')
            self.register_command('service_delete', self.cmd_delete_service, 'حذف سرویس', '.service_delete [name]')
            self.register_command('service_toggle', self.cmd_toggle_service, 'فعال/غیرفعال‌سازی سرویس', '.service_toggle [name] [on|off]')
            self.register_command('service_test', self.cmd_test_service, 'تست اتصال به سرویس', '.service_test [name]')

            # دستورات مختص هر سرویس
            self.register_command('github', self.cmd_github, 'ارسال درخواست به GitHub', '.github [action] [params...]')
            self.register_command('trello', self.cmd_trello, 'ارسال درخواست به Trello', '.trello [action] [params...]')
            self.register_command('api_call', self.cmd_api_call, 'ارسال درخواست به API دلخواه', '.api_call [service_name] [method] [endpoint] [data?]')

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
            # هیچ عملیات پاکسازی خاصی نیاز نیست
            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def cmd_add_service(self, client: TelegramClient, message: Message) -> None:
        """
        افزودن سرویس خارجی جدید

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            args = message.text.strip().split(maxsplit=2)

            if len(args) < 3:
                await message.reply(
                    "❌ **استفاده نادرست!**\n"
                    "روش صحیح: `.service_add [name] [type] [params...]`\n"
                    "مثال: `.service_add my_github github`\n\n"
                    f"انواع سرویس‌های موجود: `{', '.join(self.service_types)}`"
                )
                return

            name = args[1].lower()
            service_type = args[2].lower()

            # بررسی تکراری نبودن نام
            if name in self.services:
                await message.reply(f"❌ **خطا**: سرویس با نام `{name}` قبلاً وجود دارد.")
                return

            # بررسی نوع سرویس
            if service_type not in self.service_types:
                await message.reply(f"❌ **خطا**: نوع سرویس نامعتبر است. انواع موجود: `{', '.join(self.service_types)}`")
                return

            # دریافت اطلاعات اتصال بر اساس نوع سرویس
            config = {}

            if service_type == "github":
                await message.reply(
                    "🔑 **تنظیمات GitHub**\n\n"
                    "لطفاً توکن دسترسی GitHub خود را وارد کنید.\n"
                    "می‌توانید این توکن را از Settings > Developer settings > Personal access tokens در GitHub دریافت کنید."
                )
                token_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=120)

                if token_msg is None:
                    await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                    return

                token = token_msg.text.strip()
                # رمزنگاری توکن
                token_encrypted = await encrypt_data(token)

                config = {
                    "token": token,
                    "base_url": "https://api.github.com",
                }

                # ذخیره در دیتابیس با مقدار رمزنگاری شده
                db_config = {
                    "token": token_encrypted,
                    "base_url": "https://api.github.com",
                }

            elif service_type == "trello":
                await message.reply(
                    "🔑 **تنظیمات Trello**\n\n"
                    "لطفاً کلید API خود را وارد کنید."
                )
                key_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=60)

                if key_msg is None:
                    await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                    return

                api_key = key_msg.text.strip()

                await message.reply("اکنون توکن Trello خود را وارد کنید.")
                token_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=60)

                if token_msg is None:
                    await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                    return

                token = token_msg.text.strip()

                # رمزنگاری اطلاعات حساس
                api_key_encrypted = await encrypt_data(api_key)
                token_encrypted = await encrypt_data(token)

                config = {
                    "api_key": api_key,
                    "token": token,
                    "base_url": "https://api.trello.com/1",
                }

                # ذخیره در دیتابیس با مقادیر رمزنگاری شده
                db_config = {
                    "api_key": api_key_encrypted,
                    "token": token_encrypted,
                    "base_url": "https://api.trello.com/1",
                }

            elif service_type == "notion":
                await message.reply(
                    "🔑 **تنظیمات Notion**\n\n"
                    "لطفاً توکن Notion Integration خود را وارد کنید."
                )
                token_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=60)

                if token_msg is None:
                    await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                    return

                token = token_msg.text.strip()
                # رمزنگاری توکن
                token_encrypted = await encrypt_data(token)

                config = {
                    "token": token,
                    "base_url": "https://api.notion.com/v1",
                }

                # ذخیره در دیتابیس با مقدار رمزنگاری شده
                db_config = {
                    "token": token_encrypted,
                    "base_url": "https://api.notion.com/v1",
                }

            elif service_type == "generic_api":
                await message.reply(
                    "🔗 **تنظیمات API عمومی**\n\n"
                    "لطفاً آدرس پایه API را وارد کنید (مثال: https://api.example.com)."
                )
                base_url_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=60)

                if base_url_msg is None:
                    await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                    return

                base_url = base_url_msg.text.strip()

                await message.reply(
                    "🔑 **آیا این API نیاز به احراز هویت دارد؟**\n\n"
                    "1. بدون احراز هویت\n"
                    "2. API Key\n"
                    "3. توکن Bearer\n"
                    "4. احراز هویت Basic (نام کاربری و رمز عبور)\n\n"
                    "لطفاً عدد گزینه مورد نظر را وارد کنید."
                )

                auth_type_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=60)

                if auth_type_msg is None:
                    await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                    return

                auth_type = auth_type_msg.text.strip()

                config = {
                    "base_url": base_url,
                    "auth_type": auth_type,
                }

                db_config = {
                    "base_url": base_url,
                    "auth_type": auth_type,
                }

                # دریافت اطلاعات احراز هویت بر اساس نوع انتخاب شده
                if auth_type == "2":  # API Key
                    await message.reply("لطفاً نام پارامتر API Key را وارد کنید (مثال: api_key یا x-api-key).")
                    key_name_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=60)

                    if key_name_msg is None:
                        await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                        return

                    key_name = key_name_msg.text.strip()

                    await message.reply("حالا مقدار API Key را وارد کنید.")
                    key_value_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=60)

                    if key_value_msg is None:
                        await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                        return

                    key_value = key_value_msg.text.strip()
                    # رمزنگاری مقدار کلید
                    key_value_encrypted = await encrypt_data(key_value)

                    config["api_key_name"] = key_name
                    config["api_key"] = key_value

                    db_config["api_key_name"] = key_name
                    db_config["api_key"] = key_value_encrypted

                elif auth_type == "3":  # Bearer Token
                    await message.reply("لطفاً توکن Bearer را وارد کنید.")
                    token_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=60)

                    if token_msg is None:
                        await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                        return

                    token = token_msg.text.strip()
                    # رمزنگاری توکن
                    token_encrypted = await encrypt_data(token)

                    config["token"] = token
                    db_config["token"] = token_encrypted

                elif auth_type == "4":  # Basic Auth
                    await message.reply("لطفاً نام کاربری را وارد کنید.")
                    username_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=60)

                    if username_msg is None:
                        await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                        return

                    username = username_msg.text.strip()

                    await message.reply("لطفاً رمز عبور را وارد کنید.")
                    password_msg = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=60)

                    if password_msg is None:
                        await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                        return

                    password = password_msg.text.strip()

                    # رمزنگاری اطلاعات حساس
                    username_encrypted = await encrypt_data(username)
                    password_encrypted = await encrypt_data(password)

                    config["username"] = username
                    config["password"] = password

                    db_config["username"] = username_encrypted
                    db_config["password"] = password_encrypted

            # ذخیره سرویس در دیتابیس
            await self.db.execute(
                "INSERT INTO external_services (name, type, config, enabled) \
                    VALUES ($1, $2, $3, $4)", \
                (name, service_type, json.dumps(db_config), True)
            )

            # اضافه کردن به لیست سرویس‌های فعال
            self.services[name] = {
                'type': service_type,
                'config': config,
                'enabled': True
            }

            # ارسال پیام تأیید
            await message.reply(f"✅ **سرویس `{name}` با موفقیت اضافه شد!**\n\n"
                              f"🔧 **نوع**: `{service_type}`\n"
                              f"⚙️ **وضعیت**: فعال")

        except Exception as e:
            logger.error(f"خطا در افزودن سرویس خارجی: {str(e)}")
            await message.reply(f"❌ **خطا در افزودن سرویس**: {str(e)}")

    async def cmd_list_services(self, client: TelegramClient, message: Message) -> None:
        """
        نمایش لیست سرویس‌های خارجی متصل

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            if not self.services:
                await message.reply("📍 **هیچ سرویس خارجی تنظیم نشده است!**\n\n"
                                  "برای افزودن سرویس جدید از دستور `.service_add` استفاده کنید.")
                return

            response = "📍 **لیست سرویس‌های خارجی:**\n\n"

            for i, (name, service) in enumerate(self.services.items(), 1):
                status = "✅ فعال" if service['enabled'] else "❌ غیرفعال"
                service_type = service['type']

                # اطلاعات خاص هر نوع سرویس
                service_info = ""
                if service_type == "github":
                    service_info = "🔗 GitHub API"
                elif service_type == "trello":
                    service_info = "🔗 Trello API"
                elif service_type == "notion":
                    service_info = "🔗 Notion API"
                elif service_type == "generic_api":
                    service_info = f"🔗 {service['config'].get('base_url', 'Generic API')}"

                response += f"{i}. **{name}** ({service_info})\n"
                response += f"   💻 نوع: `{service_type}`\n"
                response += f"   ⚙️ وضعیت: {status}\n\n"

            await message.reply(response)

        except Exception as e:
            logger.error(f"خطا در نمایش لیست سرویس‌ها: {str(e)}")
            await message.reply(f"❌ **خطا در نمایش لیست سرویس‌ها**: {str(e)}")

    async def cmd_delete_service(self, client: TelegramClient, message: Message) -> None:
        """
        حذف سرویس خارجی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            args = message.text.strip().split(maxsplit=1)

            if len(args) < 2:
                await message.reply(
                    "❌ **استفاده نادرست!**\n"
                    "روش صحیح: `.service_delete [name]`\n"
                    "مثال: `.service_delete my_github`"
                )
                return

            name = args[1].lower()

            # بررسی وجود سرویس
            if name not in self.services:
                await message.reply(f"❌ **خطا**: سرویس با نام `{name}` یافت نشد.")
                return

            # درخواست تأیید حذف
            service_type = self.services[name]['type']
            await message.reply(f"⚠️ **تأیید حذف**\n\n"
                              f"آیا مطمئن هستید که می‌خواهید سرویس `{name}` از نوع `{service_type}` را حذف کنید؟\n"
                              f"برای تأیید `yes` و برای انصراف `no` بنویسید.")

            # منتظر پاسخ کاربر می‌مانیم
            response = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=30)

            if response is None:
                await message.reply("⏱️ **زمان پاسخ به پایان رسید!**")
                return

            if response.text.lower() not in ["yes", "بله", "y", "آره"]:
                await message.reply("❌ **عملیات حذف لغو شد!**")
                return

            # حذف از دیتابیس
            await self.db.execute("DELETE FROM external_services WHERE name = $1", (name,))

            # حذف از لیست سرویس‌ها
            del self.services[name]

            await message.reply(f"✅ **سرویس `{name}` با موفقیت حذف شد!**")

    async def cmd_toggle_service(self, client: TelegramClient, message: Message) -> None:
        """
        فعال/غیرفعال‌سازی سرویس خارجی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            args = message.text.strip().split(maxsplit=2)

            if len(args) < 2:
                await message.reply(
                    "❌ **استفاده نادرست!**\n"
                    "روش صحیح: `.service_toggle [name] [on|off]`\n"
                    "مثال: `.service_toggle my_github on`"
                )
                return

            name = args[1].lower()
            state = args[2].lower() if len(args) > 2 else None

            # بررسی وجود سرویس
            if name not in self.services:
                await message.reply(f"❌ **خطا**: سرویس با نام `{name}` یافت نشد.")
                return

            # تنظیم وضعیت
            if state in ["on", "enable", "روشن", "فعال"]:
                new_state = True
            elif state in ["off", "disable", "خاموش", "غیرفعال"]:
                new_state = False
            else:
                # تغییر وضعیت فعلی
                new_state = not self.services[name]['enabled']

            # به‌روزرسانی وضعیت در دیتابیس
            await self.db.execute(
                "UPDATE external_services SET enabled = $1 WHERE name = $2",
                (new_state, name)
            )

            # به‌روزرسانی در حافظه
            self.services[name]['enabled'] = new_state

            status = "فعال" if new_state else "غیرفعال"
            await message.reply(f"✅ **سرویس `{name}` {status} شد!**")

        except Exception as e:
            logger.error(f"خطا در تغییر وضعیت سرویس: {str(e)}")
            await message.reply(f"❌ **خطا در تغییر وضعیت سرویس**: {str(e)}")

    async def cmd_test_service(self, client: TelegramClient, message: Message) -> None:
        """
        تست اتصال به سرویس خارجی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            args = message.text.strip().split(maxsplit=1)

            if len(args) < 2:
                await message.reply(
                    "❌ **استفاده نادرست!**\n"
                    "روش صحیح: `.service_test [name]`\n"
                    "مثال: `.service_test my_github`"
                )
                return

            name = args[1].lower()

            # بررسی وجود سرویس
            if name not in self.services:
                await message.reply(f"❌ **خطا**: سرویس با نام `{name}` یافت نشد.")
                return

            # بررسی فعال بودن سرویس
            if not self.services[name]['enabled']:
                await message.reply(f"⚠️ **هشدار**: سرویس `{name}` غیرفعال است. آیا می‌خواهید با این حال تست کنید؟ (yes/no)")

                confirm = await client.listen(message.chat.id, filters=filters.user(message.from_user.id), timeout=30)
                if confirm is None or confirm.text.lower() not in ["yes", "بله", "y", "آره"]:
                    await message.reply("❌ **تست لغو شد!**")
                    return

            service = self.services[name]
            service_type = service['type']

            await message.reply(f"🔄 **در حال تست اتصال به سرویس `{name}` از نوع `{service_type}`...**")

            # تست بر اساس نوع سرویس
            if service_type == "github":
                # تست دریافت اطلاعات کاربر
                test_result = await self._test_github_service(service)

            elif service_type == "trello":
                # تست دریافت تخته‌ها
                test_result = await self._test_trello_service(service)

            elif service_type == "notion":
                # تست دریافت دیتابیس‌ها
                test_result = await self._test_notion_service(service)

            elif service_type == "generic_api":
                # تست دریافت پاسخ پایه
                test_result = await self._test_generic_api(service)

            else:
                await message.reply(f"❌ **خطا**: نوع سرویس `{service_type}` از تست‌های خودکار پشتیبانی نمی‌کند.")
                return

            if test_result['success']:
                await message.reply(f"✅ **تست موفقیت‌آمیز!**\n\n"
                                  f"**سرویس**: `{name}`\n"
                                  f"**نوع**: `{service_type}`\n"
                                  f"**نتیجه**: {test_result['message']}")
            else:
                await message.reply(f"❌ **تست ناموفق!**\n\n"
                                  f"**سرویس**: `{name}`\n"
                                  f"**نوع**: `{service_type}`\n"
                                  f"**خطا**: {test_result['message']}")

        except Exception as e:
            logger.error(f"خطا در تست سرویس: {str(e)}")
            await message.reply(f"❌ **خطا در تست سرویس**: {str(e)}")

