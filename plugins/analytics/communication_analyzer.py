"""
پلاگین تحلیل الگوهای ارتباطی
این پلاگین الگوهای ارتباطی کاربر را تحلیل می‌کند.
"""
import logging
import json
from datetime import datetime
import os
from collections import Counter

from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient

logger = logging.getLogger(__name__)


class CommunicationAnalyzer(BasePlugin):
    """
    پلاگین تحلیل الگوهای ارتباطی
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="CommunicationAnalyzer",
            version="1.0.0",
            description="تحلیل الگوهای ارتباطی و کاربران",
            author="SelfBot Team",
            category="analytics"
        )

        self.analyzer_enabled = True
        self.contacts_data = {}  # {user_id: {'name': str, 'count': int, 'last_interaction': timestamp}}
        self.keyword_frequency = Counter()
        self.contacts_path = "data/analytics/contacts"
        self.keywords = []  # کلمات کلیدی برای ردیابی

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین تحلیل ارتباطات در حال راه‌اندازی...")

            # ایجاد دایرکتوری‌های مورد نیاز
            os.makedirs(self.contacts_path, exist_ok=True)

            # بارگیری وضعیت فعال/غیرفعال بودن
            analyzer_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'communication_analyzer_enabled'"
            )

            if analyzer_config and 'value' in analyzer_config:
                self.analyzer_enabled = json.loads(analyzer_config['value'])
            else:
                # مقدار پیش‌فرض
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('communication_analyzer_enabled', json.dumps(self.analyzer_enabled), 'فعال‌سازی تحلیل ارتباطات')
                )

            # بارگیری کلمات کلیدی
            keywords_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'communication_keywords'"
            )

            if keywords_config and 'value' in keywords_config:
                self.keywords = json.loads(keywords_config['value'])
            else:
                # کلمات کلیدی پیش‌فرض
                self.keywords = ["سلام", "خداحافظ", "ممنون", "لطفا", "چطوری", "خوبی"]
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('communication_keywords', json.dumps(self.keywords), 'کلمات کلیدی برای ردیابی در پیام‌ها')
                )

            # بارگیری داده‌های مخاطبین
            contacts_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'contacts_data'"
            )

            if contacts_config and 'value' in contacts_config:
                self.contacts_data = json.loads(contacts_config['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('contacts_data', json.dumps(self.contacts_data), 'داده‌های مخاطبین و میزان ارتباط')
                )

            # بارگیری فراوانی کلمات کلیدی
            keyword_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'keyword_frequency'"
            )

            if keyword_config and 'value' in keyword_config:
                self.keyword_frequency = Counter(json.loads(keyword_config['value']))
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('keyword_frequency', json.dumps(dict(self.keyword_frequency)), 'فراوانی کلمات کلیدی')
                )

            # ثبت دستورات
            self.register_command('contacts', self.cmd_analyze_contacts, 'تحلیل مخاطبین و ارتباطات', '.contacts [count]')
            self.register_command('keywords', self.cmd_analyze_keywords, 'تحلیل کلمات کلیدی', '.keywords [add|remove|list]')
            self.register_command('analyzer', self.cmd_toggle_analyzer, 'فعال/غیرفعال‌سازی تحلیل‌گر', '.analyzer [on|off]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_message, {})
            self.register_event_handler(EventType.MESSAGE, self.on_contacts_command, {'text_startswith': ['.contacts', '/contacts', '!contacts']})
            self.register_event_handler(EventType.MESSAGE, self.on_keywords_command, {'text_startswith': ['.keywords', '/keywords', '!keywords']})
            self.register_event_handler(EventType.MESSAGE, self.on_analyzer_command, {'text_startswith': ['.analyzer', '/analyzer', '!analyzer']})

            # زمان‌بندی ذخیره اطلاعات
            self.schedule(self.save_analytics_data, interval=1800, name="save_analytics_data") \
                # هر 30 دقیقه \

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
            # ذخیره داده‌ها
            await self.save_analytics_data()
            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def save_analytics_data(self) -> None:
        """
        ذخیره داده‌های تحلیلی در دیتابیس
        """
        try:
            # ذخیره داده‌های مخاطبین
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.contacts_data), 'contacts_data')
            )

            # ذخیره فراوانی کلمات کلیدی
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(dict(self.keyword_frequency)), 'keyword_frequency')
            )

            # ذخیره وضعیت فعال/غیرفعال
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.analyzer_enabled), 'communication_analyzer_enabled')
            )

            # ذخیره کلمات کلیدی
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.keywords), 'communication_keywords')
            )

        except Exception as e:
            logger.error(f"خطا در ذخیره داده‌های تحلیلی: {str(e)}")

    async def on_message(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر پیام‌ها

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        if not self.analyzer_enabled:
            return

        try:
            # بررسی پیام‌های خصوصی و کلمات کلیدی
            if message.text and (message.chat.type == 'private' or message.mentioned):
                # تحلیل کلمات کلیدی
                self.analyze_keywords(message.text)

                # ثبت تعامل با کاربر
                if message.chat.type == 'private':
                    user_id = str(message.chat.id)
                    user_name = message.chat.first_name
                    if message.chat.last_name:
                        user_name += f" {message.chat.last_name}"

                    # ثبت یا به‌روزرسانی اطلاعات مخاطب
                    self.update_contact(user_id, user_name, message.date.timestamp())

                # در گروه‌ها، مخاطبینی که ما را منشن کرده‌اند را ثبت می‌کنیم
                elif message.mentioned and hasattr(message, 'from_user') and message.from_user:
                    user_id = str(message.from_user.id)
                    user_name = message.from_user.first_name
                    if message.from_user.last_name:
                        user_name += f" {message.from_user.last_name}"

                    # ثبت یا به‌روزرسانی اطلاعات مخاطب
                    self.update_contact(user_id, user_name, message.date.timestamp())

        except Exception as e:
            logger.error(f"خطا در تحلیل پیام: {str(e)}")

    def update_contact(self, user_id: str, user_name: str, timestamp: float) -> None:
        """
        به‌روزرسانی اطلاعات مخاطب

        Args:
            user_id: شناسه کاربر
            user_name: نام کاربر
            timestamp: زمان آخرین تعامل
        """
        if user_id not in self.contacts_data:
            self.contacts_data[user_id] = {
                'name': user_name,
                'count': 1,
                'last_interaction': timestamp,
                'first_interaction': timestamp
            }
        else:
            self.contacts_data[user_id]['name'] = user_name  # به‌روزرسانی نام
            self.contacts_data[user_id]['count'] += 1
            self.contacts_data[user_id]['last_interaction'] = timestamp

    def analyze_keywords(self, text: str) -> None:
        """
        تحلیل کلمات کلیدی در متن

        Args:
            text: متن پیام
        """
        text_lower = text.lower()
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                self.keyword_frequency[keyword] += 1

    async def cmd_analyze_contacts(self, client: TelegramClient, message: Message) -> None:
        """
        تحلیل مخاطبین و ارتباطات

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            args = message.text.split(maxsplit=1)
            count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10

            if not self.contacts_data:
                await message.reply("📊 **هیچ داده‌ای برای مخاطبین وجود ندارد.**")
                return

            # مرتب‌سازی مخاطبین بر اساس تعداد تعاملات
            sorted_contacts = sorted(
                [(user_id, data) for user_id, data in self.contacts_data.items()],
                key=lambda x: x[1]['count'],
                reverse=True
            )[:count]

            response = "👥 **تحلیل مخاطبین**\n\n"

            for i, (user_id, data) in enumerate(sorted_contacts, 1):
                user_name = data['name']
                interaction_count = data['count']
                last_date = datetime.fromtimestamp(data['last_interaction']) \
                    .strftime("%Y-%m-%d %H:%M") \

                response += f"{i}. **{user_name}**\n"
                response += f"   تعداد تعاملات: {interaction_count}\n"
                response += f"   آخرین تعامل: {last_date}\n\n"

            # اطلاعات کلی
            total_contacts = len(self.contacts_data)
            total_interactions = sum(data['count'] for data in self.contacts_data.values())

            response += f"**مجموع مخاطبین:** {total_contacts}\n"
            response += f"**مجموع تعاملات:** {total_interactions}\n"

            await message.reply(response)

        except Exception as e:
            logger.error(f"خطا در تحلیل مخاطبین: {str(e)}")
            await message.reply(f"❌ **خطا در تحلیل مخاطبین:** {str(e)}")

    async def cmd_analyze_keywords(self, client: TelegramClient, message: Message) -> None:
        """
        تحلیل کلمات کلیدی

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            args = message.text.split()

            if len(args) == 1 or args[1].lower() == 'list':
                # نمایش فراوانی کلمات کلیدی
                if not self.keyword_frequency:
                    await message.reply("📊 **هیچ داده‌ای برای کلمات کلیدی وجود ندارد.**")
                    return

                # مرتب‌سازی کلمات بر اساس فراوانی
                sorted_keywords = self.keyword_frequency.most_common(20)

                response = "🔤 **تحلیل کلمات کلیدی**\n\n"

                for keyword, count in sorted_keywords:
                    response += f"**{keyword}**: {count} بار\n"

                response += f"\n**کلمات کلیدی فعلی:** {', '.join(self.keywords)}"

                await message.reply(response)

            elif args[1].lower() == 'add' and len(args) > 2:
                # افزودن کلمه کلیدی جدید
                new_keyword = args[2]

                if new_keyword not in self.keywords:
                    self.keywords.append(new_keyword)
                    await self.save_analytics_data()
                    await message.reply(f"✅ **کلمه کلیدی '{new_keyword}' اضافه شد.**")
                else:
                    await message.reply(f"⚠️ **کلمه کلیدی '{new_keyword}' قبلاً وجود دارد.**")

            elif args[1].lower() == 'remove' and len(args) > 2:
                # حذف کلمه کلیدی
                keyword_to_remove = args[2]

                if keyword_to_remove in self.keywords:
                    self.keywords.remove(keyword_to_remove)
                    await self.save_analytics_data()
                    await message.reply(f"✅ **کلمه کلیدی '{keyword_to_remove}' حذف شد.**")
                else:
                    await message.reply(f"⚠️ **کلمه کلیدی '{keyword_to_remove}' وجود ندارد.**")

            else:
                await message.reply("📊 **استفاده نادرست. گزینه‌های موجود: `.keywords [list|add <keyword>|remove <keyword>]`**")

        except Exception as e:
            logger.error(f"خطا در تحلیل کلمات کلیدی: {str(e)}")
            await message.reply(f"❌ **خطا در تحلیل کلمات کلیدی:** {str(e)}")

    async def cmd_toggle_analyzer(self, client: TelegramClient, message: Message) -> None:
        """
        فعال/غیرفعال‌سازی تحلیل‌گر

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            args = message.text.split(maxsplit=1)
            state = args[1].lower() if len(args) > 1 else None

            if state == 'on' or state == 'روشن':
                self.analyzer_enabled = True
                await message.reply("✅ **تحلیل‌گر ارتباطات فعال شد.**")
            elif state == 'off' or state == 'خاموش':
                self.analyzer_enabled = False
                await message.reply("❌ **تحلیل‌گر ارتباطات غیرفعال شد.**")
            else:
                # تغییر وضعیت فعلی
                self.analyzer_enabled = not self.analyzer_enabled
                status = "فعال" if self.analyzer_enabled else "غیرفعال"
                await message.reply(f"🔄 **تحلیل‌گر ارتباطات {status} شد.**")

            # ذخیره وضعیت جدید
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.analyzer_enabled), 'communication_analyzer_enabled')
            )

        except Exception as e:
            logger.error(f"خطا در تغییر وضعیت تحلیل‌گر: {str(e)}")
            await message.reply(f"❌ **خطا در تغییر وضعیت تحلیل‌گر:** {str(e)}")

    async def on_contacts_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور contacts
        """
        await self.cmd_analyze_contacts(client, message)

    async def on_keywords_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور keywords
        """
        await self.cmd_analyze_keywords(client, message)

    async def on_analyzer_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور analyzer
        """
        await self.cmd_toggle_analyzer(client, message)
