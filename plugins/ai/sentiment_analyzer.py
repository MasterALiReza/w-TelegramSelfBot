"""
پلاگین تحلیل احساسات متن
این پلاگین امکان تحلیل احساسات متن با استفاده از هوش مصنوعی را فراهم می‌کند.
"""
import asyncio
import logging
import time
import os
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import aiohttp
from datetime import datetime

from pyrogram import filters
from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient
from core.crypto import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class SentimentAnalyzer(BasePlugin):
    """
    پلاگین تحلیل احساسات متن
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="SentimentAnalyzer",
            version="1.0.0",
            description="تحلیل احساسات متن با هوش مصنوعی",
            author="SelfBot Team",
            category="ai"
        )
        self.openai_api_key = None
        self.default_provider = "openai"  # می‌تواند "huggingface" هم باشد
        self.session = None
        self.chat_analysis_enabled = False
        self.target_chats = []
        self.lang = "fa"  # زبان پیش‌فرض فارسی

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین تحلیل احساسات در حال راه‌اندازی...")

            # بارگیری تنظیمات از دیتابیس
            openai_key_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'openai_api_key'"
            )

            provider_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'sentiment_provider'"
            )

            lang_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'sentiment_lang'"
            )

            chat_analysis_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'sentiment_chat_analysis'"
            )

            target_chats_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'sentiment_target_chats'"
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

            if provider_setting and 'value' in provider_setting:
                self.default_provider = provider_setting['value']
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('sentiment_provider', self.default_provider, 'سرویس‌دهنده پیش‌فرض تحلیل احساسات')
                )

            if lang_setting and 'value' in lang_setting:
                self.lang = lang_setting['value']
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('sentiment_lang', self.lang, 'زبان پیش‌فرض تحلیل احساسات')
                )

            if chat_analysis_setting and 'value' in chat_analysis_setting:
                self.chat_analysis_enabled = chat_analysis_setting['value'].lower() == 'true'
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('sentiment_chat_analysis', str(self.chat_analysis_enabled), 'فعالسازی تحلیل خودکار چت‌ها')
                )

            if target_chats_setting and 'value' in target_chats_setting:
                self.target_chats = json.loads(target_chats_setting['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('sentiment_target_chats', '[]', 'چت‌های هدف برای تحلیل خودکار')
                )

            # ایجاد جلسه HTTP
            self.session = aiohttp.ClientSession()

            # ثبت دستورات
            self.register_command('sentiment', self.cmd_analyze_sentiment, 'تحلیل احساسات متن', '.sentiment [متن]')
            self.register_command('sentiment_set', self.cmd_sentiment_settings, 'تنظیم پارامترهای تحلیل احساسات',
                               '.sentiment_set [پارامتر] [مقدار]')
            self.register_command('sentiment_chat', self.cmd_sentiment_chat, 'فعال/غیرفعال کردن تحلیل خودکار چت',
                                '.sentiment_chat [on|off] [chat_id]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_sentiment_command,
                                     {'text_startswith': ['.sentiment ', '/sentiment ', '!sentiment ']})
            self.register_event_handler(EventType.MESSAGE, self.on_sentiment_settings_command,
                                     {'text_startswith': ['.sentiment_set ', '/sentiment_set ', '!sentiment_set ']})
            self.register_event_handler(EventType.MESSAGE, self.on_sentiment_chat_command,
                                     {'text_startswith': ['.sentiment_chat ', '/sentiment_chat ', '!sentiment_chat ']})

            # اگر تحلیل خودکار چت فعال باشد، هندلر مربوطه را ثبت می‌کنیم
            if self.chat_analysis_enabled:
                self.register_event_handler(EventType.MESSAGE, self.on_chat_message, {})

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

    async def analyze_sentiment_openai(self, text: str) -> Dict[str, Any]:
        """
        تحلیل احساسات متن با استفاده از OpenAI API

        Args:
            text (str): متن ورودی برای تحلیل

        Returns:
            Dict[str, Any]: نتیجه تحلیل احساسات
        """
        if not self.openai_api_key:
            logger.error("کلید API برای OpenAI تنظیم نشده است")
            return {"error": "کلید API تنظیم نشده است"}

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }

            # ساخت پرامپت مناسب برای تحلیل احساسات
            if self.lang == "fa":
                system_message = "شما یک سیستم تحلیل احساسات هستید. وظیفه شما تحلیل احساسات متن و بازگرداندن نتیجه در قالب JSON است."
                user_message = f"لطفا احساسات متن زیر را تحلیل کنید و نتیجه را در قالب JSON با کلیدهای 'sentiment' (مثبت، منفی یا خنثی) \
                    \ \
                    \ \
                    ، 'confidence' (اطمینان بین 0 تا 1)، و 'explanation' (توضیح کوتاه) \
                    برگردانید:\n\n{text}" \
            else:
                system_message = "You are a sentiment analysis system. Your task is to analyze the sentiment of the text and return the result in JSON format."
                user_message = f"Please analyze the sentiment of the following text and return the result in JSON format with keys 'sentiment' (positive, negative, or neutral) \
                    \ \
                    \ \
                    , 'confidence' (confidence between 0 and 1) \
                        , and 'explanation' (brief explanation) \ \
                    :\n\n{text}" \

            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "response_format": {"type": "json_object"}
            }

            async with self.session.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers) \
                \ \
                \ \
                as response: \
                if response.status == 200:
                    response_data = await response.json()
                    result = json.loads(response_data["choices"][0]["message"]["content"])
                    return result
                else:
                    error_data = await response.text()
                    logger.error(f"خطا در تحلیل احساسات: {error_data}")
                    return {"error": f"خطا از سرور: {response.status}"}

        except Exception as e:
            logger.error(f"خطا در تحلیل احساسات: {str(e)}")
            return {"error": str(e)}

    async def analyze_sentiment_huggingface(self, text: str) -> Dict[str, Any]:
        """
        تحلیل احساسات متن با استفاده از Hugging Face API

        Args:
            text (str): متن ورودی برای تحلیل

        Returns:
            Dict[str, Any]: نتیجه تحلیل احساسات
        """
        # این قسمت را می‌توان در آینده پیاده‌سازی کرد
        return {"error": "API هاگینگ فیس هنوز پیاده‌سازی نشده است"}

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        تحلیل احساسات متن با استفاده از سرویس‌دهنده پیش‌فرض

        Args:
            text (str): متن ورودی برای تحلیل

        Returns:
            Dict[str, Any]: نتیجه تحلیل احساسات
        """
        if self.default_provider == "openai":
            return await self.analyze_sentiment_openai(text)
        elif self.default_provider == "huggingface":
            return await self.analyze_sentiment_huggingface(text)
        else:
            return {"error": f"سرویس‌دهنده نامعتبر: {self.default_provider}"}

    async def cmd_analyze_sentiment(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تحلیل احساسات متن

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام درخواست
        """
        # جدا کردن متن از دستور
        if len(message.text.split(" ", 1)) < 2:
            await message.reply_text("لطفاً متنی برای تحلیل وارد کنید. مثال: `.sentiment متن مورد نظر`")
            return

        text = message.text.split(" ", 1)[1]

        # ارسال پیام در حال تحلیل
        processing_msg = await message.reply_text("در حال تحلیل احساسات متن...")

        # تحلیل احساسات
        result = await self.analyze_sentiment(text)

        # ساخت متن پاسخ
        if "error" in result:
            response_text = f"❌ خطا در تحلیل احساسات: {result['error']}"
        else:
            sentiment_fa = {
                "positive": "مثبت",
                "negative": "منفی",
                "neutral": "خنثی"
            }.get(result.get("sentiment", ""), result.get("sentiment", ""))

            confidence = result.get("confidence", 0) * 100
            explanation = result.get("explanation", "")

            response_text = f"🔍 **نتیجه تحلیل احساسات**\n\n"
            response_text += f"• **احساس**: {sentiment_fa}\n"
            response_text += f"• **اطمینان**: {confidence:.1f}%\n"
            response_text += f"• **توضیح**: {explanation}"

        # ارسال پاسخ
        await processing_msg.edit_text(response_text)

        # ثبت در دیتابیس
        try:
            if "error" not in result:
                await self.insert(
                    'activity_logs',
                    {
                        'user_id': message.from_user.id if message.from_user else 0,
                        'chat_id': message.chat.id,
                        'activity_type': 'sentiment_analysis',
                        'details': json.dumps({
                            'text': text,
                            'result': result
                        }),
                        'created_at': datetime.now().isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"خطا در ثبت تحلیل احساسات: {str(e)}")

    async def cmd_sentiment_settings(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تنظیم پارامترهای تحلیل احساسات

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام درخواست
        """
        # بررسی تعداد پارامترها
        parts = message.text.split(" ", 2)
        if len(parts) < 3:
            await message.reply_text(
                "لطفاً پارامتر و مقدار را وارد کنید.\n"
                "پارامترهای موجود: provider, lang\n"
                "مثال: `.sentiment_set provider openai`"
            )
            return

        param = parts[1].lower()
        value = parts[2]

        if param == "provider":
            if value.lower() not in ["openai", "huggingface"]:
                await message.reply_text("سرویس‌دهنده باید یکی از موارد زیر باشد: openai, huggingface")
                return

            self.default_provider = value.lower()
            await self.update(
                'settings',
                {'value': self.default_provider},
                'key = $1',
                ('sentiment_provider',)
            )
            await message.reply_text(f"✅ سرویس‌دهنده پیش‌فرض تحلیل احساسات به '{self.default_provider}' تغییر کرد.")

        elif param == "lang":
            if value.lower() not in ["fa", "en"]:
                await message.reply_text("زبان باید یکی از موارد زیر باشد: fa, en")
                return

            self.lang = value.lower()
            await self.update(
                'settings',
                {'value': self.lang},
                'key = $1',
                ('sentiment_lang',)
            )
            await message.reply_text(f"✅ زبان پیش‌فرض تحلیل احساسات به '{self.lang}' تغییر کرد.")

        else:
            await message.reply_text(
                "پارامتر نامعتبر است.\n"
                "پارامترهای موجود: provider, lang\n"
                "مثال: `.sentiment_set provider openai`"
            )

    async def cmd_sentiment_chat(self, client: TelegramClient, message: Message) -> None:
        """
        دستور فعال/غیرفعال کردن تحلیل خودکار چت

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام درخواست
        """
        # بررسی تعداد پارامترها
        parts = message.text.split(" ", 2)
        if len(parts) < 2:
            await message.reply_text(
                "لطفاً وضعیت را وارد کنید (on یا off).\n"
                "مثال برای فعال کردن در چت فعلی: `.sentiment_chat on`\n"
                "مثال برای فعال کردن در چت دیگر: `.sentiment_chat on 123456789`"
            )
            return

        state = parts[1].lower()
        if state not in ["on", "off"]:
            await message.reply_text("وضعیت باید یکی از موارد زیر باشد: on, off")
            return

        # تعیین چت هدف
        target_chat_id = None
        if len(parts) >= 3:
            try:
                target_chat_id = int(parts[2])
            except ValueError:
                await message.reply_text("شناسه چت باید یک عدد صحیح باشد")
                return
        else:
            target_chat_id = message.chat.id

        # فعال/غیرفعال کردن تحلیل خودکار چت
        if state == "on":
            if target_chat_id not in self.target_chats:
                self.target_chats.append(target_chat_id)

            if not self.chat_analysis_enabled:
                self.chat_analysis_enabled = True
                await self.update(
                    'settings',
                    {'value': 'true'},
                    'key = $1',
                    ('sentiment_chat_analysis',)
                )
                # ثبت هندلر رویداد
                self.register_event_handler(EventType.MESSAGE, self.on_chat_message, {})

            await self.update(
                'settings',
                {'value': json.dumps(self.target_chats)},
                'key = $1',
                ('sentiment_target_chats',)
            )
            await message.reply_text(f"✅ تحلیل خودکار احساسات برای چت {target_chat_id} فعال شد.")

        else:  # state == "off"
            if target_chat_id in self.target_chats:
                self.target_chats.remove(target_chat_id)

            await self.update(
                'settings',
                {'value': json.dumps(self.target_chats)},
                'key = $1',
                ('sentiment_target_chats',)
            )

            if not self.target_chats and self.chat_analysis_enabled:
                self.chat_analysis_enabled = False
                await self.update(
                    'settings',
                    {'value': 'false'},
                    'key = $1',
                    ('sentiment_chat_analysis',)
                )
                # حذف هندلر رویداد
                self.unregister_event_handler(EventType.MESSAGE, self.on_chat_message)

            await message.reply_text(f"✅ تحلیل خودکار احساسات برای چت {target_chat_id} غیرفعال شد.")

    async def on_sentiment_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تحلیل احساسات

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        await self.cmd_analyze_sentiment(client, message)

    async def on_sentiment_settings_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تنظیم پارامترهای تحلیل احساسات

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        await self.cmd_sentiment_settings(client, message)

    async def on_sentiment_chat_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور فعال/غیرفعال کردن تحلیل خودکار چت

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        await self.cmd_sentiment_chat(client, message)

    async def on_chat_message(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر پیام‌های چت برای تحلیل خودکار احساسات

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        # بررسی اینکه آیا این چت در لیست هدف است یا خیر
        if message.chat.id not in self.target_chats:
            return

        # بررسی اینکه پیام متنی است یا خیر
        if not message.text or message.text.startswith(('.', '/', '!')):
            return

        # بررسی اینکه آیا پیام به اندازه کافی طولانی است یا خیر
        if len(message.text) < 10:
            return

        # تحلیل احساسات
        try:
            result = await self.analyze_sentiment(message.text)

            # ثبت در دیتابیس
            if "error" not in result:
                await self.insert(
                    'activity_logs',
                    {
                        'user_id': message.from_user.id if message.from_user else 0,
                        'chat_id': message.chat.id,
                        'activity_type': 'auto_sentiment_analysis',
                        'details': json.dumps({
                            'text': message.text,
                            'result': result
                        }),
                        'created_at': datetime.now().isoformat()
                    }
                )

                # اعلان به کاربران (اختیاری، بسته به نیاز)
                # در حالت پیش‌فرض غیرفعال است تا چت را شلوغ نکند
                # اگر نیاز به اعلان باشد، می‌توان این بخش را فعال کرد

                # اعمال اقدامات بر اساس احساسات (مثلاً مسدود کردن محتوای منفی شدید)
                # این بخش می‌تواند بر اساس نیاز پیاده‌سازی شود

        except Exception as e:
            logger.error(f"خطا در تحلیل خودکار احساسات: {str(e)}")
