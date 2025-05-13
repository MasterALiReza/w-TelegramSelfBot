"""
پلاگین تولید تصویر با هوش مصنوعی
این پلاگین امکان تولید تصویر با استفاده از API های هوش مصنوعی را فراهم می‌کند.
"""
import asyncio
import logging
import time
import os
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import aiohttp
import base64
from datetime import datetime

from pyrogram import filters
from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient
from core.crypto import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class ImageGenerator(BasePlugin):
    """
    پلاگین تولید تصویر با هوش مصنوعی
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="ImageGenerator",
            version="1.0.0",
            description="تولید تصویر با هوش مصنوعی",
            author="SelfBot Team",
            category="ai"
        )
        self.openai_api_key = None
        self.stability_api_key = None
        self.default_provider = "openai"  # یا "stability"
        self.default_style = "vivid"  # یا "natural"
        self.default_size = "1024x1024"
        self.session = None
        self.save_path = "data/images"

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین تولید تصویر در حال راه‌اندازی...")

            # بارگیری تنظیمات از دیتابیس
            openai_key_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'openai_api_key'"
            )

            stability_key_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'stability_api_key'"
            )

            provider_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'image_gen_provider'"
            )

            style_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'image_gen_style'"
            )

            size_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'image_gen_size'"
            )

            # اعمال تنظیمات
            if openai_key_setting and 'value' in openai_key_setting:
                self.openai_api_key = decrypt_data(openai_key_setting['value'])
            else:
                # دریافت از متغیر محیطی
                self.openai_api_key = os.environ.get("OPENAI_API_KEY")
                if self.openai_api_key:
                    await self.db.execute(
                        "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                        ('openai_api_key', encrypt_data(self.openai_api_key), 'کلید API شرکت OpenAI')
                    )

            if stability_key_setting and 'value' in stability_key_setting:
                self.stability_api_key = decrypt_data(stability_key_setting['value'])
            else:
                # دریافت از متغیر محیطی
                self.stability_api_key = os.environ.get("STABILITY_API_KEY")
                if self.stability_api_key:
                    await self.db.execute(
                        "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                        ('stability_api_key', encrypt_data(self.stability_api_key), 'کلید API شرکت Stability AI')
                    )

            if provider_setting and 'value' in provider_setting:
                self.default_provider = provider_setting['value']
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('image_gen_provider', self.default_provider, 'سرویس‌دهنده پیش‌فرض تولید تصویر')
                )

            if style_setting and 'value' in style_setting:
                self.default_style = style_setting['value']
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('image_gen_style', self.default_style, 'سبک پیش‌فرض تصاویر')
                )

            if size_setting and 'value' in size_setting:
                self.default_size = size_setting['value']
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('image_gen_size', self.default_size, 'اندازه پیش‌فرض تصاویر')
                )

            # اطمینان از وجود دایرکتوری ذخیره تصاویر
            os.makedirs(self.save_path, exist_ok=True)

            # ایجاد جلسه HTTP
            self.session = aiohttp.ClientSession()

            # ثبت دستورات
            self.register_command('img', self.cmd_generate_image, 'تولید تصویر با هوش مصنوعی', '.img [توضیحات تصویر]')
            self.register_command('img_set', self.cmd_image_settings, 'تنظیم پارامترهای تولید تصویر', '.img_set [پارامتر] [مقدار]')
            self.register_command('img_key', self.cmd_set_api_key, 'تنظیم کلید API تولید تصویر', '.img_key [openai|stability] [کلید]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_img_command, {'text_startswith': ['.img ', '/img ', '!img ']})
            self.register_event_handler(EventType.MESSAGE, self.on_img_settings_command, {'text_startswith': ['.img_set ', '/img_set ', '!img_set ']})
            self.register_event_handler(EventType.MESSAGE, self.on_img_key_command, {'text_startswith': ['.img_key ', '/img_key ', '!img_key ']})

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
                await self.update(
                    'plugins',
                    {k: v for k, v in plugin_data.items() if k != 'name'},
                    'name = $1',
                    (self.name,)
                )
            else:
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

    async def generate_image_openai(self, prompt: str, size: str = "1024x1024", style: str = "vivid") \
        \ \
        \ \
        -> Optional[str]: \
        """
        تولید تصویر با API OpenAI (DALL-E)

        Args:
            prompt: توضیحات تصویر
            size: اندازه تصویر
            style: سبک تصویر

        Returns:
            Optional[str]: مسیر فایل تصویر یا None در صورت خطا
        """
        if not self.openai_api_key:
            logger.error("کلید API برای OpenAI مشخص نشده است")
            return None

        try:
            # ساخت درخواست
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "style": style
            }

            # ارسال درخواست به API
            async with self.session.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload) \
                \ \
                \ \
                as response: \
                if response.status != 200:
                    error_data = await response.text()
                    logger.error(f"خطا در درخواست OpenAI: {response.status} - {error_data}")
                    return None

                result = await response.json()

                # استخراج URL تصویر
                if 'data' in result and len(result['data']) > 0 and 'url' in result['data'][0]:
                    image_url = result['data'][0]['url']

                    # دانلود تصویر
                    async with self.session.get(image_url) as img_response:
                        if img_response.status != 200:
                            logger.error(f"خطا در دانلود تصویر: {img_response.status}")
                            return None

                        # ذخیره تصویر
                        timestamp = int(datetime.now().timestamp())
                        image_path = os.path.join(self.save_path, f"openai_{timestamp}.png")

                        with open(image_path, 'wb') as f:
                            f.write(await img_response.read())

                        return image_path

                return None

        except Exception as e:
            logger.error(f"خطا در تولید تصویر با OpenAI: {str(e)}")
            return None

    async def generate_image_stability(self, prompt: str, size: str = "1024x1024") -> Optional[str]:
        """
        تولید تصویر با API Stability AI

        Args:
            prompt: توضیحات تصویر
            size: اندازه تصویر

        Returns:
            Optional[str]: مسیر فایل تصویر یا None در صورت خطا
        """
        if not self.stability_api_key:
            logger.error("کلید API برای Stability AI مشخص نشده است")
            return None

        try:
            # تبدیل اندازه به عرض و ارتفاع
            width, height = map(int, size.split('x'))

            # محدودیت اندازه برای Stability API
            if width > 1024 or height > 1024:
                width = height = 1024

            # ساخت درخواست
            headers = {
                "Authorization": f"Bearer {self.stability_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "text_prompts": [{"text": prompt}],
                "cfg_scale": 7.0,
                "height": height,
                "width": width,
                "samples": 1,
                "steps": 30,
            }

            # ارسال درخواست به API
            async with self.session.post("https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image", headers=headers, json=payload) \
                \ \
                \ \
                as response: \
                if response.status != 200:
                    error_data = await response.text()
                    logger.error(f"خطا در درخواست Stability AI: {response.status} - {error_data}")
                    return None

                result = await response.json()

                # استخراج داده تصویر
                if 'artifacts' in result and len(result['artifacts']) > 0:
                    image_data_base64 = result['artifacts'][0]['base64']
                    image_data = base64.b64decode(image_data_base64)

                    # ذخیره تصویر
                    timestamp = int(datetime.now().timestamp())
                    image_path = os.path.join(self.save_path, f"stability_{timestamp}.png")

                    with open(image_path, 'wb') as f:
                        f.write(image_data)

                    return image_path

                return None

        except Exception as e:
            logger.error(f"خطا در تولید تصویر با Stability AI: {str(e)}")
            return None

    async def cmd_generate_image(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تولید تصویر

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت توضیحات تصویر
            parts = message.text.split(maxsplit=1)

            if len(parts) < 2:
                await message.reply_text(self._("invalid_img_command", default="لطفاً توضیحات تصویر را وارد کنید. استفاده صحیح: `.img [توضیحات تصویر]`"))
                return

            prompt = parts[1]

            # ارسال پیام در حال بارگیری
            processing_message = await message.reply_text(self._("img_processing", default="در حال پردازش درخواست تصویر..."))

            # انتخاب سرویس‌دهنده مناسب
            image_path = None
            if self.default_provider == "openai" and self.openai_api_key:
                image_path = await self.generate_image_openai(prompt, self.default_size, self.default_style)
            elif self.default_provider == "stability" and self.stability_api_key:
                image_path = await self.generate_image_stability(prompt, self.default_size)
            else:
                # اگر سرویس‌دهنده پیش‌فرض در دسترس نیست، سعی کنید سرویس‌دهنده دیگر را استفاده کنید
                if self.openai_api_key:
                    image_path = await self.generate_image_openai(prompt, self.default_size, self.default_style)
                elif self.stability_api_key:
                    image_path = await self.generate_image_stability(prompt, self.default_size)
                else:
                    await processing_message.edit_text(self._("no_api_key", default="کلید API برای سرویس‌های تولید تصویر تنظیم نشده است."))
                    return

            if image_path:
                # ارسال تصویر
                await processing_message.delete()
                await client.send_photo(
                    message.chat.id,
                    image_path,
                    caption=f"🖼️ {prompt}\n\n🤖 {self.default_provider.upper() \
                        } • {self.default_size}" \
                )
            else:
                await processing_message.edit_text(self._("img_error", default="خطا در تولید تصویر. لطفاً بعداً دوباره تلاش کنید."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور img: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_image_settings(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تنظیم پارامترهای تولید تصویر

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if len(args) < 2:
                await message.reply_text(self._("invalid_img_set_command", default="استفاده صحیح: `.img_set [provider|style|size] [مقدار]`"))
                return

            param = args[0].lower()
            value = args[1]

            if param == "provider":
                if value not in ["openai", "stability"]:
                    await message.reply_text(self._("invalid_provider", default="سرویس‌دهنده نامعتبر است. گزینه‌های مجاز: openai, stability"))
                    return

                self.default_provider = value
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (value, 'image_gen_provider')
                )

                await message.reply_text(self._("provider_updated", default=f"سرویس‌دهنده پیش‌فرض به `{value}` تغییر یافت."))

            elif param == "style":
                if value not in ["vivid", "natural"]:
                    await message.reply_text(self._("invalid_style", default="سبک نامعتبر است. گزینه‌های مجاز: vivid, natural"))
                    return

                self.default_style = value
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (value, 'image_gen_style')
                )

                await message.reply_text(self._("style_updated", default=f"سبک پیش‌فرض به `{value}` تغییر یافت."))

            elif param == "size":
                valid_sizes = ["256x256", "512x512", "1024x1024", "1024x1792", "1792x1024"]
                if value not in valid_sizes:
                    sizes_str = ", ".join(valid_sizes)
                    await message.reply_text(self._("invalid_size", default=f"اندازه نامعتبر است. اندازه‌های مجاز: {sizes_str}"))
                    return

                self.default_size = value
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (value, 'image_gen_size')
                )

                await message.reply_text(self._("size_updated", default=f"اندازه پیش‌فرض به `{value}` تغییر یافت."))

            else:
                await message.reply_text(self._("invalid_param", default="پارامتر نامعتبر است. پارامترهای مجاز: provider, style, size"))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور img_set: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_set_api_key(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تنظیم کلید API

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()

            if len(args) < 3:
                await message.reply_text(self._("invalid_img_key_command", default="استفاده صحیح: `.img_key [openai|stability] [کلید]`"))
                return

            provider = args[1].lower()
            api_key = args[2]

            if provider == "openai":
                # بررسی اعتبار کلید (بررسی ساده)
                if not api_key.startswith("sk-") or len(api_key) < 20:
                    await message.reply_text(self._("invalid_openai_key", default="کلید API نامعتبر است. کلید OpenAI باید با 'sk-' شروع شود."))
                    return

                # ذخیره کلید (رمزنگاری شده)
                self.openai_api_key = api_key
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (encrypt_data(api_key), 'openai_api_key')
                )

            elif provider == "stability":
                # بررسی اعتبار کلید (بررسی ساده)
                if len(api_key) < 10:
                    await message.reply_text(self._("invalid_stability_key", default="کلید API نامعتبر است."))
                    return

                # ذخیره کلید (رمزنگاری شده)
                self.stability_api_key = api_key
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (encrypt_data(api_key), 'stability_api_key')
                )

            else:
                await message.reply_text(self._("invalid_provider", default="سرویس‌دهنده نامعتبر است. گزینه‌های مجاز: openai, stability"))
                return

            # حذف پیام حاوی کلید API برای امنیت
            await message.delete()

            # ارسال پاسخ
            await client.send_message(message.chat.id, self._("api_key_updated", default=f"کلید API برای {provider} با موفقیت بروزرسانی شد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور img_key: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def on_img_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تولید تصویر

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_generate_image(client, message)

    async def on_img_settings_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تنظیم پارامترهای تولید تصویر

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_image_settings(client, message)

    async def on_img_key_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تنظیم کلید API

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_set_api_key(client, message)
