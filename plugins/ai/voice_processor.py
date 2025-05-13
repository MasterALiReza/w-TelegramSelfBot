"""
پلاگین پردازش صوت
این پلاگین برای تبدیل متن به صوت و صوت به متن استفاده می‌شود و همچنین قابلیت‌های تشخیص صدا را فراهم می‌کند.
"""
import asyncio
import os
import json
import logging
import tempfile
from typing import Optional

from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient

# وابستگی‌های خارجی
try:
    import openai
    import speech_recognition as sr
    from pydub import AudioSegment
    from gtts import gTTS
except ImportError:
    openai = None
    sr = None
    AudioSegment = None
    gTTS = None

logger = logging.getLogger(__name__)


class VoiceProcessor(BasePlugin):
    """
    پلاگین پردازش صوت برای تبدیل صوت به متن و متن به صوت
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="VoiceProcessor",
            version="1.0.0",
            description="پردازش صوت، تبدیل متن به صوت و صوت به متن",
            author="SelfBot Team",
            category="ai"
        )
        self.is_enabled = True
        self.recognizer = sr.Recognizer() if sr else None
        self.openai_api_key = None
        self.google_tts_lang = "fa"  # زبان پیش‌فرض برای تبدیل متن به صوت
        self.transcription_model = "whisper-1"  # مدل پیش‌فرض Whisper
        self.max_voice_duration = 300  # حداکثر مدت زمان صوت (ثانیه)

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بررسی وابستگی‌های خارجی
            if not all([openai, sr, AudioSegment, gTTS]):
                logger.error("وابستگی‌های مورد نیاز نصب نشده‌اند. لطفاً بسته‌های زیر را نصب کنید:")
                logger.error("pip install openai SpeechRecognition pydub gtts")
                return False

            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین پردازش صوت در حال راه‌اندازی...")

            # بارگیری کلید API از دیتابیس
            api_key = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'openai_api_key'"
            )

            if api_key and 'value' in api_key:
                self.openai_api_key = api_key['value']
                openai.api_key = self.openai_api_key
            else:
                logger.warning("کلید API برای OpenAI یافت نشد!")

            # بارگیری سایر تنظیمات
            tts_lang = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'google_tts_lang'"
            )

            if tts_lang and 'value' in tts_lang:
                self.google_tts_lang = tts_lang['value']
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('google_tts_lang', self.google_tts_lang, 'زبان پیش‌فرض برای تبدیل متن به صوت Google')
                )

            # ثبت دستورات
            self.register_command('tts', self.cmd_text_to_speech, 'تبدیل متن به صوت', '.tts [متن]')
            self.register_command('stt', self.cmd_speech_to_text, 'تبدیل صوت به متن (در پاسخ به پیام صوتی)', '.stt')
            self.register_command('vp_lang', self.cmd_set_language, 'تنظیم زبان پیش‌فرض برای TTS', '.vp_lang [کد زبان]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_tts_command, {'text_startswith': ['.tts', '/tts', '!tts']})
            self.register_event_handler(EventType.MESSAGE, self.on_stt_command, {'text_startswith': ['.stt', '/stt', '!stt']})
            self.register_event_handler(EventType.MESSAGE, self.on_set_language_command, {'text_startswith': ['.vp_lang', '/vp_lang', '!vp_lang']})

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

            # ذخیره زبان پیش‌فرض TTS
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (self.google_tts_lang, 'google_tts_lang')
            )

            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def text_to_speech(self, text: str, lang: str = None) -> Optional[str]:
        """
        تبدیل متن به صوت

        Args:
            text (str): متن برای تبدیل به صوت
            lang (str, optional): کد زبان (ISO 639-1)

        Returns:
            Optional[str]: مسیر فایل صوتی تولید شده
        """
        try:
            if not text:
                return None

            # استفاده از زبان پیش‌فرض اگر زبان مشخص نشده باشد
            if not lang:
                lang = self.google_tts_lang

            # ایجاد فایل موقت
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name

            # تبدیل متن به صوت با Google TTS
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(temp_path)

            return temp_path

        except Exception as e:
            logger.error(f"خطا در تبدیل متن به صوت: {str(e)}")
            return None

    async def speech_to_text_google(self, audio_path: str) -> Optional[str]:
        """
        تبدیل صوت به متن با استفاده از Google Speech Recognition

        Args:
            audio_path (str): مسیر فایل صوتی

        Returns:
            Optional[str]: متن استخراج شده
        """
        try:
            # تبدیل فایل صوتی تلگرام به فرمت موردنیاز
            audio = AudioSegment.from_file(audio_path)

            # ذخیره به فرمت WAV
            wav_path = audio_path + ".wav"
            audio.export(wav_path, format="wav")

            # استفاده از کتابخانه SpeechRecognition
            with sr.AudioFile(wav_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language=self.google_tts_lang)

            # حذف فایل‌های موقتی
            os.remove(wav_path)

            return text

        except sr.UnknownValueError:
            logger.warning("Google Speech Recognition نتوانست صدا را تشخیص دهد")
            return None
        except sr.RequestError as e:
            logger.error(f"خطا در درخواست به سرویس Google Speech Recognition: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"خطا در تبدیل صوت به متن: {str(e)}")
            return None

    async def speech_to_text_openai(self, audio_path: str) -> Optional[str]:
        """
        تبدیل صوت به متن با استفاده از OpenAI Whisper

        Args:
            audio_path (str): مسیر فایل صوتی

        Returns:
            Optional[str]: متن استخراج شده
        """
        try:
            if not self.openai_api_key:
                logger.error("کلید API برای OpenAI تنظیم نشده است")
                return None

            # استفاده از OpenAI Whisper
            with open(audio_path, "rb") as audio_file:
                response = await asyncio.to_thread(
                    openai.Audio.transcribe,
                    model=self.transcription_model,
                    file=audio_file
                )

            return response.get("text", "")

        except Exception as e:
            logger.error(f"خطا در تبدیل صوت به متن با OpenAI Whisper: {str(e)}")
            return None

    async def cmd_text_to_speech(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تبدیل متن به صوت

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            # دریافت متن
            text = message.text.split(maxsplit=1)

            if len(text) < 2:
                await message.reply_text("لطفاً متن موردنظر را وارد کنید. مثال: `.tts سلام، این یک تست است`")
                return

            text = text[1]

            # بررسی طول متن
            if len(text) > 500:
                await message.reply_text("متن وارد شده بیش از حد طولانی است. حداکثر 500 کاراکتر مجاز است.")
                return

            # ارسال پیام در حال پردازش
            processing_msg = await message.reply_text("در حال تبدیل متن به صوت...")

            # تبدیل متن به صوت
            audio_path = await self.text_to_speech(text)

            if not audio_path:
                await processing_msg.edit_text("خطا در تبدیل متن به صوت. لطفاً دوباره تلاش کنید.")
                return

            # ارسال فایل صوتی
            await client.send_voice(
                chat_id=message.chat.id,
                voice=audio_path,
                caption="🎙️ تبدیل متن به صوت"
            )

            # حذف پیام در حال پردازش
            await processing_msg.delete()

            # حذف فایل موقتی
            os.remove(audio_path)

        except Exception as e:
            logger.error(f"خطا در اجرای دستور text_to_speech: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")

    async def cmd_speech_to_text(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تبدیل صوت به متن

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            # بررسی پاسخ به پیام صوتی
            if not message.reply_to_message or not message.reply_to_message.voice:
                await message.reply_text("لطفاً این دستور را در پاسخ به یک پیام صوتی استفاده کنید.")
                return

            voice_msg = message.reply_to_message

            # بررسی مدت زمان صوت
            if voice_msg.voice.duration > self.max_voice_duration:
                await message.reply_text(f"مدت زمان فایل صوتی بیش از حد مجاز ({self.max_voice_duration} ثانیه) است.")
                return

            # ارسال پیام در حال پردازش
            processing_msg = await message.reply_text("در حال پردازش فایل صوتی...")

            # دانلود فایل صوتی
            voice_file = await client.download_media(voice_msg)

            # انتخاب روش تبدیل صوت به متن
            if self.openai_api_key:
                text = await self.speech_to_text_openai(voice_file)
                method = "OpenAI Whisper"
            else:
                text = await self.speech_to_text_google(voice_file)
                method = "Google Speech Recognition"

            # حذف فایل صوتی دانلود شده
            os.remove(voice_file)

            if not text:
                await processing_msg.edit_text("متنی در فایل صوتی تشخیص داده نشد یا خطایی رخ داده است.")
                return

            # ارسال متن استخراج شده
            await processing_msg.edit_text(f"🎤 **متن استخراج شده** (با {method}):\n\n{text}")

        except Exception as e:
            logger.error(f"خطا در اجرای دستور speech_to_text: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")

    async def cmd_set_language(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تنظیم زبان پیش‌فرض

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            # دریافت کد زبان
            args = message.text.split()

            if len(args) < 2:
                await message.reply_text(
                    "لطفاً کد زبان موردنظر را وارد کنید. مثال: `.vp_lang fa`\n\n"
                    "نمونه کدهای زبان:\n"
                    "🇮🇷 فارسی: fa\n"
                    "🇬🇧 انگلیسی: en\n"
                    "🇩🇪 آلمانی: de\n"
                    "🇫🇷 فرانسوی: fr\n"
                    "🇪🇸 اسپانیایی: es\n"
                    "🇷🇺 روسی: ru"
                )
                return

            lang_code = args[1].lower()

            # تنظیم زبان جدید
            self.google_tts_lang = lang_code

            # ذخیره در دیتابیس
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (self.google_tts_lang, 'google_tts_lang')
            )

            await message.reply_text(f"✅ زبان پیش‌فرض برای تبدیل متن به صوت به `{lang_code}` تغییر یافت.")

        except Exception as e:
            logger.error(f"خطا در اجرای دستور set_language: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")

    # هندلرهای رویداد

    async def on_tts_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تبدیل متن به صوت
        """
        await self.cmd_text_to_speech(client, message)

    async def on_stt_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تبدیل صوت به متن
        """
        await self.cmd_speech_to_text(client, message)

    async def on_set_language_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تنظیم زبان
        """
        await self.cmd_set_language(client, message)
