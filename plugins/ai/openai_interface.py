"""
پلاگین اتصال به OpenAI
این پلاگین امکان استفاده از API های هوش مصنوعی OpenAI را فراهم می‌کند.
"""
import asyncio
import logging
import time
import os
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import aiohttp

from pyrogram import filters
from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient
from core.crypto import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class OpenAIInterface(BasePlugin):
    """
    پلاگین اتصال به OpenAI
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="OpenAIInterface",
            version="1.0.0",
            description="اتصال به سرویس‌های هوش مصنوعی OpenAI",
            author="SelfBot Team",
            category="ai"
        )
        self.api_key = None
        self.default_model = "gpt-4o"
        self.models = [
            "gpt-4o",
            "gpt-4",
            "gpt-3.5-turbo"
        ]
        self.max_tokens = 1000
        self.temperature = 0.7
        self.session = None

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین اتصال به OpenAI در حال راه‌اندازی...")

            # بارگیری تنظیمات از دیتابیس
            api_key_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'openai_api_key'"
            )

            model_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'openai_default_model'"
            )

            max_tokens_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'openai_max_tokens'"
            )

            temperature_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'openai_temperature'"
            )

            # اگر تنظیمات موجود نیست، مقادیر پیش‌فرض را تنظیم کنیم
            if api_key_setting and 'value' in api_key_setting:
                self.api_key = decrypt_data(api_key_setting['value'])
            else:
                # دریافت از متغیر محیطی
                self.api_key = os.environ.get("OPENAI_API_KEY")
                if self.api_key:
                    # ذخیره در دیتابیس (به صورت رمزنگاری شده)
                    await self.db.execute(
                        "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                        ('openai_api_key', encrypt_data(self.api_key), 'کلید API شرکت OpenAI')
                    )
                else:
                    logger.warning("کلید API برای OpenAI مشخص نشده است")

            if model_setting and 'value' in model_setting:
                self.default_model = model_setting['value']
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('openai_default_model', self.default_model, 'مدل پیش‌فرض OpenAI')
                )

            if max_tokens_setting and 'value' in max_tokens_setting:
                self.max_tokens = int(max_tokens_setting['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('openai_max_tokens', str(self.max_tokens), 'حداکثر تعداد توکن‌های درخواستی')
                )

            if temperature_setting and 'value' in temperature_setting:
                self.temperature = float(temperature_setting['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('openai_temperature', str(self.temperature), 'دمای (خلاقیت) مدل')
                )

            # ایجاد جلسه HTTP
            self.session = aiohttp.ClientSession()

            # ثبت دستورات
            self.register_command('ai', self.cmd_ai_complete, 'درخواست تکمیل از هوش مصنوعی', '.ai [متن درخواست]')
            self.register_command('ai_models', self.cmd_ai_models, 'مشاهده مدل‌های موجود', '.ai_models')
            self.register_command('ai_set', self.cmd_ai_settings, 'تنظیم پارامترهای هوش مصنوعی', '.ai_set [پارامتر] [مقدار]')
            self.register_command('ai_key', self.cmd_ai_set_key, 'تنظیم کلید API', '.ai_key [کلید]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_ai_command, {'text_startswith': ['.ai ', '/ai ', '!ai ']})
            self.register_event_handler(EventType.MESSAGE, self.on_ai_models_command, {'text': ['.ai_models', '/ai_models', '!ai_models']})
            self.register_event_handler(EventType.MESSAGE, self.on_ai_settings_command, {'text_startswith': ['.ai_set ', '/ai_set ', '!ai_set ']})
            self.register_event_handler(EventType.MESSAGE, self.on_ai_key_command, {'text_startswith': ['.ai_key ', '/ai_key ', '!ai_key ']})

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

            # بستن جلسه HTTP
            if self.session:
                await self.session.close()

            # ذخیره تنظیمات در دیتابیس
            await self.update(
                'plugins',
                {'config': json.dumps(self.config)},
                'name = $1',
                (self.name,)
            )

            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def openai_completion(self, prompt: str, model: Optional[str] = None, max_tokens: Optional[int] = None, temperature: Optional[float] = None) \
        \ \
        \ \
        -> Optional[str]: \
        """
        درخواست تکمیل از API OpenAI

        Args:
            prompt: متن درخواست
            model: مدل مورد استفاده (اختیاری)
            max_tokens: حداکثر تعداد توکن‌های خروجی (اختیاری)
            temperature: دمای مدل (خلاقیت) (اختیاری)

        Returns:
            Optional[str]: متن پاسخ یا None در صورت خطا
        """
        if not self.api_key:
            logger.error("کلید API برای OpenAI مشخص نشده است")
            return None

        # استفاده از مقادیر پیش‌فرض اگر پارامترها تعیین نشده‌اند
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        try:
            # ساخت درخواست
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            # ارسال درخواست به API
            async with self.session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload) \
                \ \
                \ \
                as response: \
                if response.status != 200:
                    error_data = await response.text()
                    logger.error(f"خطا در درخواست OpenAI: {response.status} - {error_data}")
                    return None

                result = await response.json()

                # استخراج پاسخ
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content'].strip()

                return None

        except Exception as e:
            logger.error(f"خطا در اتصال به OpenAI: {str(e)}")
            return None

    async def cmd_ai_complete(self, client: TelegramClient, message: Message) -> None:
        """
        دستور درخواست تکمیل از هوش مصنوعی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت متن درخواست
            prompt = message.text.split(maxsplit=1)

            if len(prompt) < 2:
                await message.reply_text(self._("invalid_ai_command", default="لطفاً متن درخواست را وارد کنید. استفاده صحیح: `.ai [متن درخواست]`"))
                return

            prompt = prompt[1]

            # ارسال پیام در حال بارگیری
            processing_message = await message.reply_text(self._("ai_processing", default="در حال پردازش درخواست شما..."))

            # درخواست تکمیل از API
            response = await self.openai_completion(prompt)

            if response:
                # ارسال پاسخ
                await processing_message.edit_text(f"🤖 **پاسخ AI:**\n\n{response}")
            else:
                await processing_message.edit_text(self._("ai_error", default="خطا در دریافت پاسخ از هوش مصنوعی. لطفاً بعداً دوباره تلاش کنید."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور ai: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_ai_models(self, client: TelegramClient, message: Message) -> None:
        """
        دستور مشاهده مدل‌های موجود

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # ساخت پاسخ
            response = self._("available_models", default="🤖 **مدل‌های موجود:**\n\n")

            for model in self.models:
                current = "✓ " if model == self.default_model else ""
                response += f"- {current}`{model}`\n"

            response += f"\n🔧 **مدل پیش‌فرض:** `{self.default_model}`"
            response += f"\n🔢 **حداکثر توکن:** `{self.max_tokens}`"
            response += f"\n🌡️ **دما (خلاقیت):** `{self.temperature}`"

            # ارسال پاسخ
            await message.reply_text(response)

        except Exception as e:
            logger.error(f"خطا در اجرای دستور ai_models: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_ai_settings(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تنظیم پارامترهای هوش مصنوعی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if len(args) < 2:
                await message.reply_text(self._("invalid_ai_set_command", default="استفاده صحیح: `.ai_set [model|max_tokens|temperature] [مقدار]`"))
                return

            param = args[0].lower()
            value = args[1]

            if param == "model":
                if value not in self.models:
                    models_str = ", ".join(self.models)
                    await message.reply_text(self._("invalid_model", default=f"مدل نامعتبر است. مدل‌های موجود: {models_str}"))
                    return

                self.default_model = value
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (value, 'openai_default_model')
                )

                await message.reply_text(self._("model_updated", default=f"مدل پیش‌فرض به `{value}` تغییر یافت."))

            elif param == "max_tokens":
                try:
                    max_tokens = int(value)
                    if max_tokens < 1 or max_tokens > 4000:
                        await message.reply_text(self._("invalid_max_tokens", default="تعداد توکن باید بین 1 تا 4000 باشد."))
                        return

                    self.max_tokens = max_tokens
                    await self.db.execute(
                        "UPDATE settings SET value = $1 WHERE key = $2",
                        (str(max_tokens), 'openai_max_tokens')
                    )

                    await message.reply_text(self._("max_tokens_updated", default=f"حداکثر تعداد توکن به `{max_tokens}` تغییر یافت."))

                except ValueError:
                    await message.reply_text(self._("invalid_number", default="مقدار باید یک عدد باشد."))

            elif param == "temperature":
                try:
                    temperature = float(value)
                    if temperature < 0 or temperature > 2:
                        await message.reply_text(self._("invalid_temperature", default="دما باید بین 0 تا 2 باشد."))
                        return

                    self.temperature = temperature
                    await self.db.execute(
                        "UPDATE settings SET value = $1 WHERE key = $2",
                        (str(temperature), 'openai_temperature')
                    )

                    await message.reply_text(self._("temperature_updated", default=f"دما به `{temperature}` تغییر یافت."))

                except ValueError:
                    await message.reply_text(self._("invalid_number", default="مقدار باید یک عدد باشد."))

            else:
                await message.reply_text(self._("invalid_param", default="پارامتر نامعتبر است. پارامترهای مجاز: model, max_tokens, temperature"))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور ai_set: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_ai_set_key(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تنظیم کلید API

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split(maxsplit=1)

            if len(args) < 2:
                await message.reply_text(self._("invalid_ai_key_command", default="لطفاً کلید API را وارد کنید. استفاده صحیح: `.ai_key [کلید]`"))
                return

            api_key = args[1].strip()

            # بررسی اعتبار کلید (بررسی ساده)
            if not api_key.startswith("sk-") or len(api_key) < 20:
                await message.reply_text(self._("invalid_api_key", default="کلید API نامعتبر است. کلید OpenAI باید با 'sk-' شروع شود."))
                return

            # ذخیره کلید (رمزنگاری شده)
            self.api_key = api_key
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (encrypt_data(api_key), 'openai_api_key')
            )

            # حذف پیام حاوی کلید API برای امنیت
            await message.delete()

            # ارسال پاسخ
            await client.send_message(message.chat.id, self._("api_key_updated", default="کلید API با موفقیت بروزرسانی شد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور ai_key: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def on_ai_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور درخواست تکمیل از هوش مصنوعی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_ai_complete(client, message)

    async def on_ai_models_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور مشاهده مدل‌های موجود

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_ai_models(client, message)

    async def on_ai_settings_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تنظیم پارامترهای هوش مصنوعی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_ai_settings(client, message)

    async def on_ai_key_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تنظیم کلید API

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_ai_set_key(client, message)
