"""
پلاگین ردیابی و تحلیل فعالیت‌ها
این پلاگین فعالیت‌های سلف بات را ردیابی و تحلیل می‌کند.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import json
from datetime import datetime, timedelta
import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from pyrogram import filters
from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient

logger = logging.getLogger(__name__)


class ActivityTracker(BasePlugin):
    """
    پلاگین ردیابی و تحلیل فعالیت‌ها
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="ActivityTracker",
            version="1.0.0",
            description="ردیابی و تحلیل فعالیت‌های سلف بات",
            author="SelfBot Team",
            category="analytics"
        )
        self.tracking_enabled = True
        self.charts_path = "data/charts"
        self.daily_stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "media_sent": 0,
            "media_received": 0,
            "most_active_chat": None,
            "most_active_chat_count": 0,
            "time_periods": {hour: 0 for hour in range(24)}
        }
        self.chat_activities = {}  # {chat_id: message_count}
        self.last_reset = datetime.now().date()

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین تحلیل فعالیت‌ها در حال راه‌اندازی...")

            # ایجاد دایرکتوری‌های مورد نیاز
            os.makedirs(self.charts_path, exist_ok=True)

            # بارگیری وضعیت فعال/غیرفعال بودن
            tracking_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'activity_tracking_enabled'"
            )

            if tracking_config and 'value' in tracking_config:
                self.tracking_enabled = json.loads(tracking_config['value'])
            else:
                # مقدار پیش‌فرض
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('activity_tracking_enabled', json.dumps(self.tracking_enabled), 'فعال‌سازی ردیابی فعالیت‌ها')
                )

            # بارگیری آمار روزانه
            daily_stats_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'daily_activity_stats'"
            )

            if daily_stats_config and 'value' in daily_stats_config:
                self.daily_stats = json.loads(daily_stats_config['value'])
                reset_date = datetime.strptime(self.daily_stats.get("last_reset", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d") \
                    \ \
                    \ \
                    .date() \
                self.last_reset = reset_date
            else:
                self.daily_stats["last_reset"] = datetime.now().strftime("%Y-%m-%d")
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('daily_activity_stats', json.dumps(self.daily_stats), 'آمار فعالیت روزانه')
                )

            # بارگیری آمار چت‌ها
            chat_activities_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'chat_activities'"
            )

            if chat_activities_config and 'value' in chat_activities_config:
                self.chat_activities = json.loads(chat_activities_config['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('chat_activities', json.dumps(self.chat_activities), 'آمار فعالیت چت‌ها')
                )

            # ثبت دستورات
            self.register_command('stats', self.cmd_show_stats, 'نمایش آمار فعالیت‌ها', '.stats [daily|weekly|monthly]')
            self.register_command('track', self.cmd_toggle_tracking, 'فعال/غیرفعال‌سازی ردیابی فعالیت‌ها', '.track [on|off]')
            self.register_command('chart', self.cmd_generate_chart, 'تولید نمودار فعالیت‌ها', '.chart [type] [period]')
            self.register_command('export', self.cmd_export_data, 'استخراج داده‌های فعالیت‌ها', '.export [format]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_message_activity, {})
            self.register_event_handler(EventType.EDITED_MESSAGE, self.on_edited_message_activity, {})
            self.register_event_handler(EventType.MESSAGE, self.on_stats_command, {'text_startswith': ['.stats', '/stats', '!stats']})
            self.register_event_handler(EventType.MESSAGE, self.on_track_command, {'text_startswith': ['.track', '/track', '!track']})
            self.register_event_handler(EventType.MESSAGE, self.on_chart_command, {'text_startswith': ['.chart', '/chart', '!chart']})
            self.register_event_handler(EventType.MESSAGE, self.on_export_command, {'text_startswith': ['.export', '/export', '!export']})

            # زمان‌بندی بررسی و ذخیره آمار روزانه
            self.schedule(self.check_daily_reset, interval=3600, name="check_daily_reset") \
                # هر ساعت \
            self.schedule(self.save_statistics, interval=1800, name="save_statistics") \
                # هر 30 دقیقه \

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

            # ذخیره آمار
            await self.save_statistics()

            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def save_statistics(self) -> None:
        """
        ذخیره آمار فعالیت‌ها در دیتابیس
        """
        try:
            # تنظیم تاریخ آخرین بازنشانی
            self.daily_stats["last_reset"] = self.last_reset.strftime("%Y-%m-%d")

            # ذخیره آمار روزانه
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.daily_stats), 'daily_activity_stats')
            )

            # ذخیره آمار چت‌ها
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.chat_activities), 'chat_activities')
            )

            # ذخیره وضعیت ردیابی
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.tracking_enabled), 'activity_tracking_enabled')
            )

        except Exception as e:
            logger.error(f"خطا در ذخیره آمار فعالیت‌ها: {str(e)}")

    async def check_daily_reset(self) -> None:
        """
        بررسی نیاز به بازنشانی آمار روزانه
        """
        try:
            today = datetime.now().date()

            # اگر تاریخ عوض شده است
            if today > self.last_reset:
                # ذخیره آمار روز قبل در تاریخچه
                history_key = f"activity_history_{self.last_reset.strftime('%Y%m%d')}"

                await self.db.execute(
                    "INSERT INTO settings (key, value, description) \
                        VALUES ($1, $2, $3) ON CONFLICT (key) DO UPDATE SET value = $2", \
                    (history_key, json.dumps(self.daily_stats), f"آمار فعالیت در تاریخ {self.last_reset.strftime('%Y-%m-%d')}")
                )

                # بازنشانی آمار روزانه
                self.daily_stats = {
                    "messages_sent": 0,
                    "messages_received": 0,
                    "media_sent": 0,
                    "media_received": 0,
                    "most_active_chat": None,
                    "most_active_chat_count": 0,
                    "time_periods": {hour: 0 for hour in range(24)},
                    "last_reset": today.strftime("%Y-%m-%d")
                }

                self.last_reset = today

                # ذخیره آمار جدید
                await self.save_statistics()

                logger.info(f"آمار روزانه بازنشانی شد. تاریخ جدید: {today}")

        except Exception as e:
            logger.error(f"خطا در بررسی بازنشانی آمار روزانه: {str(e)}")

    async def on_message_activity(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر فعالیت پیام‌ها

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        if not self.tracking_enabled:
            return

        try:
            # بررسی ارسالی یا دریافتی
            is_outgoing = message.outgoing
            has_media = bool(message.media) or bool(message.photo) \
                or bool(message.document) or bool(message.video) or bool(message.animation) \
                or bool(message.voice) or bool(message.audio) \

            # به روزرسانی آمار روزانه
            hour = datetime.now().hour
            self.daily_stats["time_periods"][hour] += 1

            if is_outgoing:
                self.daily_stats["messages_sent"] += 1
                if has_media:
                    self.daily_stats["media_sent"] += 1
            else:
                self.daily_stats["messages_received"] += 1
                if has_media:
                    self.daily_stats["media_received"] += 1

            # به روزرسانی آمار چت
            chat_id = str(message.chat.id)
            if chat_id not in self.chat_activities:
                self.chat_activities[chat_id] = {
                    "title": message.chat.title if hasattr(message.chat, "title") \
                        else message.chat.first_name if hasattr(message.chat, "first_name") \
                        else str(chat_id), \
                    "count": 0,
                    "sent": 0,
                    "received": 0
                }

            self.chat_activities[chat_id]["count"] += 1
            if is_outgoing:
                self.chat_activities[chat_id]["sent"] += 1
            else:
                self.chat_activities[chat_id]["received"] += 1

            # بررسی چت فعال
            if self.chat_activities[chat_id]["count"] > self.daily_stats["most_active_chat_count"]:
                self.daily_stats["most_active_chat"] = self.chat_activities[chat_id]["title"]
                self.daily_stats["most_active_chat_count"] = self.chat_activities[chat_id]["count"]

        except Exception as e:
            logger.error(f"خطا در ردیابی فعالیت پیام: {str(e)}")

    async def on_edited_message_activity(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر فعالیت پیام‌های ویرایش شده

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        # فقط پیام‌های ویرایش شده خودمان را ردیابی می‌کنیم
        if not self.tracking_enabled or not message.outgoing:
            return

        # در اینجا می‌توان آمار ویرایش‌ها را نیز اضافه کرد

    async def cmd_show_stats(self, client: TelegramClient, message: Message) -> None:
        """
        نمایش آمار فعالیت‌ها

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت نوع آمار از ورودی
            args = message.text.split(maxsplit=1)
            period = args[1].lower() if len(args) > 1 else 'daily'

            if period == 'daily' or period == 'روزانه':
                # نمایش آمار روزانه
                sent = self.daily_stats["messages_sent"]
                received = self.daily_stats["messages_received"]
                media_sent = self.daily_stats["media_sent"]
                media_received = self.daily_stats["media_received"]
                total = sent + received
                most_active = self.daily_stats["most_active_chat"]

                # پیدا کردن ساعت فعال
                active_hour = max(self.daily_stats["time_periods"].items(), key=lambda x: x[1])[0]

                response = f"📊 **آمار روزانه - {self.last_reset.strftime('%Y-%m-%d')}**\n\n"
                response += f"📤 **ارسال شده:** {sent} پیام، {media_sent} رسانه\n"
                response += f"📥 **دریافت شده:** {received} پیام، {media_received} رسانه\n"
                response += f"📝 **مجموع:** {total} پیام\n"
                response += f"⏰ **ساعت فعال:** {active_hour}:00 - {active_hour+1}:00\n"

                if most_active:
                    response += f"👥 **فعال‌ترین چت:** {most_active} ({self.daily_stats['most_active_chat_count']} پیام) \
                        \ \
                        \ \
                        \n" \

                # تولید نمودار ساعتی و ذخیره آن
                chart_path = os.path.join(self.charts_path, f"daily_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                await self.generate_hourly_chart(chart_path)

                if os.path.exists(chart_path):
                    # ارسال نمودار
                    await client.send_photo(
                        chat_id=message.chat.id,
                        photo=chart_path,
                        caption=response
                    )
                else:
                    # ارسال متن بدون نمودار
                    await message.reply(response)

            elif period == 'weekly' or period == 'هفتگی':
                # استخراج آمار هفتگی از تاریخچه
                weekly_stats = await self.get_weekly_stats()

                response = f"📊 **آمار هفتگی**\n\n"
                response += f"📤 **ارسال شده:** {weekly_stats['messages_sent']} پیام\n"
                response += f"📥 **دریافت شده:** {weekly_stats['messages_received']} پیام\n"
                response += f"📝 **مجموع:** {weekly_stats['total']} پیام\n"

                await message.reply(response)

            elif period == 'monthly' or period == 'ماهانه':
                # استخراج آمار ماهانه از تاریخچه
                monthly_stats = await self.get_monthly_stats()

                response = f"📊 **آمار ماهانه**\n\n"
                response += f"📤 **ارسال شده:** {monthly_stats['messages_sent']} پیام\n"
                response += f"📥 **دریافت شده:** {monthly_stats['messages_received']} پیام\n"
                response += f"📝 **مجموع:** {monthly_stats['total']} پیام\n"

                await message.reply(response)

            else:
                await message.reply("📊 نوع آمار نامعتبر است. از یکی از گزینه‌های روزانه، هفتگی یا ماهانه استفاده کنید.")

        except Exception as e:
            logger.error(f"خطا در نمایش آمار: {str(e)}")
            await message.reply(f"❌ **خطا در نمایش آمار:** {str(e)}")

    async def cmd_toggle_tracking(self, client: TelegramClient, message: Message) -> None:
        """
        فعال/غیرفعال‌سازی ردیابی فعالیت‌ها

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            args = message.text.split(maxsplit=1)
            state = args[1].lower() if len(args) > 1 else None

            if state == 'on' or state == 'روشن':
                self.tracking_enabled = True
                await message.reply("✅ **ردیابی فعالیت‌ها فعال شد.**")
            elif state == 'off' or state == 'خاموش':
                self.tracking_enabled = False
                await message.reply("❌ **ردیابی فعالیت‌ها غیرفعال شد.**")
            else:
                # تغییر وضعیت فعلی
                self.tracking_enabled = not self.tracking_enabled
                status = "فعال" if self.tracking_enabled else "غیرفعال"
                await message.reply(f"🔄 **ردیابی فعالیت‌ها {status} شد.**")

            # ذخیره وضعیت جدید
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.tracking_enabled), 'activity_tracking_enabled')
            )

        except Exception as e:
            logger.error(f"خطا در تغییر وضعیت ردیابی: {str(e)}")
            await message.reply(f"❌ **خطا در تغییر وضعیت ردیابی:** {str(e)}")

    async def cmd_generate_chart(self, client: TelegramClient, message: Message) -> None:
        """
        تولید نمودار فعالیت‌ها

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            args = message.text.split(maxsplit=2)
            chart_type = args[1].lower() if len(args) > 1 else 'hourly'
            period = args[2].lower() if len(args) > 2 else 'daily'

            chart_path = os.path.join(self.charts_path, f"{chart_type}_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

            if chart_type == 'hourly' or chart_type == 'ساعتی':
                await self.generate_hourly_chart(chart_path)
                caption = "📊 **نمودار فعالیت ساعتی**"
            elif chart_type == 'chat' or chart_type == 'چت':
                await self.generate_chat_chart(chart_path)
                caption = "📊 **نمودار فعالیت چت‌ها**"
            elif chart_type == 'media' or chart_type == 'رسانه':
                await self.generate_media_chart(chart_path)
                caption = "📊 **نمودار رسانه‌ها**"
            else:
                await message.reply("❌ **نوع نمودار نامعتبر است. از یکی از گزینه‌های ساعتی، چت یا رسانه استفاده کنید.**")
                return

            if os.path.exists(chart_path):
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=chart_path,
                    caption=caption
                )
            else:
                await message.reply("❌ **خطا در تولید نمودار.**")

        except Exception as e:
            logger.error(f"خطا در تولید نمودار: {str(e)}")
            await message.reply(f"❌ **خطا در تولید نمودار:** {str(e)}")

    async def cmd_export_data(self, client: TelegramClient, message: Message) -> None:
        """
        استخراج داده‌های فعالیت‌ها

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            args = message.text.split(maxsplit=1)
            format_type = args[1].lower() if len(args) > 1 else 'json'

            export_path = os.path.join("data/exports", f"activity_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(os.path.dirname(export_path), exist_ok=True)

            # آماده‌سازی داده
            export_data = {
                "daily_stats": self.daily_stats,
                "chat_activities": self.chat_activities,
                "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            if format_type == 'json':
                file_path = f"{export_path}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=4)
            elif format_type == 'csv':
                file_path = f"{export_path}.csv"
                # تبدیل به دیتافریم و ذخیره به CSV
                df = pd.DataFrame({
                    "چت": [chat_data["title"] for chat_id, chat_data in self.chat_activities.items() \
                        \ \
                        \ \
                        ], \
                    "تعداد کل": [chat_data["count"] for chat_id, chat_data in self.chat_activities.items() \
                        \ \
                        \ \
                        ], \
                    "ارسالی": [chat_data["sent"] for chat_id, chat_data in self.chat_activities.items() \
                        \ \
                        \ \
                        ], \
                    "دریافتی": [chat_data["received"] for chat_id, chat_data in self.chat_activities.items() \
                        \ \
                        \ \
                        ], \
                })
                df.to_csv(file_path, index=False, encoding='utf-8')
            else:
                await message.reply("❌ **فرمت نامعتبر است. از یکی از گزینه‌های json یا csv استفاده کنید.**")
                return

            # ارسال فایل
            await client.send_document(
                chat_id=message.chat.id,
                document=file_path,
                caption=f"📊 **داده‌های فعالیت - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**"
            )

        except Exception as e:
            logger.error(f"خطا در استخراج داده‌ها: {str(e)}")
            await message.reply(f"❌ **خطا در استخراج داده‌ها:** {str(e)}")

    async def on_stats_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور stats
        """
        await self.cmd_show_stats(client, message)

    async def on_track_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور track
        """
        await self.cmd_toggle_tracking(client, message)

    async def on_chart_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور chart
        """
        await self.cmd_generate_chart(client, message)

    async def on_export_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور export
        """
        await self.cmd_export_data(client, message)

    async def generate_hourly_chart(self, chart_path: str) -> bool:
        """
        تولید نمودار ساعتی فعالیت‌ها

        Args:
            chart_path: مسیر ذخیره نمودار

        Returns:
            bool: وضعیت تولید نمودار
        """
        try:
            plt.figure(figsize=(10, 6))
            plt.style.use('ggplot')

            # آماده‌سازی داده‌ها
            hours = list(range(24))
            counts = [self.daily_stats["time_periods"].get(hour, 0) for hour in hours]

            # تنظیم شکل نمودار
            plt.bar(hours, counts, color='#4CAF50', alpha=0.7, width=0.7)
            plt.title('فعالیت ساعتی', fontsize=16, fontweight='bold')
            plt.xlabel('ساعت', fontsize=12)
            plt.ylabel('تعداد پیام', fontsize=12)
            plt.xticks(hours)
            plt.tight_layout()
            plt.grid(axis='y', linestyle='--', alpha=0.7)

            # ذخیره نمودار
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()

            return True
        except Exception as e:
            logger.error(f"خطا در تولید نمودار ساعتی: {str(e)}")
            return False

    async def generate_chat_chart(self, chart_path: str) -> bool:
        """
        تولید نمودار فعالیت چت‌ها

        Args:
            chart_path: مسیر ذخیره نمودار

        Returns:
            bool: وضعیت تولید نمودار
        """
        try:
            # فیلتر کردن چت‌های با بیشترین فعالیت
            top_chats = sorted(
                [(chat_id, data) for chat_id, data in self.chat_activities.items()],
                key=lambda x: x[1]["count"],
                reverse=True
            )[:10]  # فقط 10 چت برتر

            if not top_chats:
                logger.warning("چتی برای نمایش در نمودار وجود ندارد")
                return False

            plt.figure(figsize=(12, 7))
            plt.style.use('ggplot')

            chat_names = [data["title"][:15] + '...' if len(data["title"]) \
                > 15 else data["title"] for _, data in top_chats] \
            sent_counts = [data["sent"] for _, data in top_chats]
            received_counts = [data["received"] for _, data in top_chats]

            # تنظیم شکل نمودار
            x = range(len(chat_names))
            width = 0.35

            plt.bar([i - width/2 for i in x], sent_counts, width, label='ارسالی', color='#2196F3', alpha=0.7)
            plt.bar([i + width/2 for i in x], received_counts, width, label='دریافتی', color='#FF5722', alpha=0.7)

            plt.title('فعالیت چت‌ها', fontsize=16, fontweight='bold')
            plt.xlabel('چت', fontsize=12)
            plt.ylabel('تعداد پیام', fontsize=12)
            plt.xticks(x, chat_names, rotation=45, ha='right')
            plt.legend()
            plt.tight_layout()
            plt.grid(axis='y', linestyle='--', alpha=0.7)

            # ذخیره نمودار
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()

            return True
        except Exception as e:
            logger.error(f"خطا در تولید نمودار چت: {str(e)}")
            return False

    async def generate_media_chart(self, chart_path: str) -> bool:
        """
        تولید نمودار رسانه‌ها

        Args:
            chart_path: مسیر ذخیره نمودار

        Returns:
            bool: وضعیت تولید نمودار
        """
        try:
            plt.figure(figsize=(10, 8))
            plt.style.use('ggplot')

            # آماده‌سازی داده‌ها
            media_data = [
                self.daily_stats["media_sent"],
                self.daily_stats["media_received"],
                self.daily_stats["messages_sent"] - self.daily_stats["media_sent"],
                self.daily_stats["messages_received"] - self.daily_stats["media_received"]
            ]

            labels = ['رسانه ارسالی', 'رسانه دریافتی', 'متن ارسالی', 'متن دریافتی']
            colors = ['#4CAF50', '#2196F3', '#FFC107', '#FF5722']

            # ترسیم نمودار دایره‌ای
            plt.pie(
                media_data,
                labels=labels,
                colors=colors,
                autopct='%1.1f%%',
                startangle=90,
                shadow=True,
                wedgeprops={'edgecolor': 'white', 'linewidth': 1}
            )

            plt.title('توزیع پیام‌ها و رسانه‌ها', fontsize=16, fontweight='bold')
            plt.axis('equal')  # برای دایره کامل

            # ذخیره نمودار
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close()

            return True
        except Exception as e:
            logger.error(f"خطا در تولید نمودار رسانه: {str(e)}")
            return False

    async def get_weekly_stats(self) -> Dict[str, int]:
        """
        استخراج آمار هفتگی از تاریخچه

        Returns:
            Dict[str, int]: آمار هفتگی
        """
        try:
            # محاسبه تاریخ 7 روز قبل
            today = datetime.now().date()
            week_ago = (today - timedelta(days=7)).strftime("%Y%m%d")

            # جمع‌آوری آمار هفته گذشته
            weekly_stats = {
                "messages_sent": 0,
                "messages_received": 0,
                "media_sent": 0,
                "media_received": 0,
                "total": 0
            }

            # بارگیری تمام رکوردهای تاریخی
            history_records = await self.db.fetch(
                "SELECT key, value FROM settings WHERE key LIKE 'activity_history_%'"
            )

            for record in history_records:
                date_str = record["key"].split("_")[-1]  # activity_history_20250510 -> 20250510

                # بررسی در محدوده هفته گذشته
                if date_str >= week_ago:
                    daily_data = json.loads(record["value"])
                    weekly_stats["messages_sent"] += daily_data.get("messages_sent", 0)
                    weekly_stats["messages_received"] += daily_data.get("messages_received", 0)
                    weekly_stats["media_sent"] += daily_data.get("media_sent", 0)
                    weekly_stats["media_received"] += daily_data.get("media_received", 0)

            # اضافه کردن آمار امروز
            weekly_stats["messages_sent"] += self.daily_stats["messages_sent"]
            weekly_stats["messages_received"] += self.daily_stats["messages_received"]
            weekly_stats["media_sent"] += self.daily_stats["media_sent"]
            weekly_stats["media_received"] += self.daily_stats["media_received"]

            # محاسبه مجموع
            weekly_stats["total"] = weekly_stats["messages_sent"] + weekly_stats["messages_received"]

            return weekly_stats

        except Exception as e:
            logger.error(f"خطا در استخراج آمار هفتگی: {str(e)}")
            return {
                "messages_sent": 0,
                "messages_received": 0,
                "media_sent": 0,
                "media_received": 0,
                "total": 0
            }

    async def get_monthly_stats(self) -> Dict[str, int]:
        """
        استخراج آمار ماهانه از تاریخچه

        Returns:
            Dict[str, int]: آمار ماهانه
        """
        try:
            # محاسبه تاریخ 30 روز قبل
            today = datetime.now().date()
            month_ago = (today - timedelta(days=30)).strftime("%Y%m%d")

            # جمع‌آوری آمار ماه گذشته
            monthly_stats = {
                "messages_sent": 0,
                "messages_received": 0,
                "media_sent": 0,
                "media_received": 0,
                "total": 0
            }

            # بارگیری تمام رکوردهای تاریخی
            history_records = await self.db.fetch(
                "SELECT key, value FROM settings WHERE key LIKE 'activity_history_%'"
            )

            for record in history_records:
                date_str = record["key"].split("_")[-1]  # activity_history_20250510 -> 20250510

                # بررسی در محدوده ماه گذشته
                if date_str >= month_ago:
                    daily_data = json.loads(record["value"])
                    monthly_stats["messages_sent"] += daily_data.get("messages_sent", 0)
                    monthly_stats["messages_received"] += daily_data.get("messages_received", 0)
                    monthly_stats["media_sent"] += daily_data.get("media_sent", 0)
                    monthly_stats["media_received"] += daily_data.get("media_received", 0)

            # اضافه کردن آمار امروز
            monthly_stats["messages_sent"] += self.daily_stats["messages_sent"]
            monthly_stats["messages_received"] += self.daily_stats["messages_received"]
            monthly_stats["media_sent"] += self.daily_stats["media_sent"]
            monthly_stats["media_received"] += self.daily_stats["media_received"]

            # محاسبه مجموع
            monthly_stats["total"] = monthly_stats["messages_sent"] + monthly_stats["messages_received"]

            return monthly_stats

        except Exception as e:
            logger.error(f"خطا در استخراج آمار ماهانه: {str(e)}")
            return {
                "messages_sent": 0,
                "messages_received": 0,
                "media_sent": 0,
                "media_received": 0,
                "total": 0
            }
