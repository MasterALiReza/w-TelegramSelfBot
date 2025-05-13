"""
پلاگین فایروال امنیتی
این پلاگین مسئول محافظت از حساب کاربری در برابر اسپم، محتوای نامناسب و سایر تهدیدات امنیتی است.
"""
import logging
import time
import json


from plugins.base_plugin import BasePlugin
from core.event_handler import EventType

logger = logging.getLogger(__name__)


class FirewallPlugin(BasePlugin):
    """
    پلاگین فایروال امنیتی
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="Firewall",
            version="1.0.0",
            description="فایروال امنیتی برای محافظت در برابر تهدیدات",
            author="SelfBot Team",
            category="security"
        )
        self.is_enabled = True
        self.blocked_users = []  # لیست کاربران مسدود شده
        self.blocked_keywords = []  # کلمات کلیدی مسدود شده
        self.spam_threshold = 5  # آستانه تشخیص اسپم
        self.spam_window = 60  # پنجره زمانی (ثانیه) برای بررسی اسپم
        self.user_message_count = {}  # تعداد پیام کاربران در پنجره زمانی
        self.last_cleanup_time = time.time()
        self.whitelist = []  # لیست سفید کاربران و گروه‌ها
        self.auto_delete_spam = True  # حذف خودکار پیام‌های اسپم
        self.notification_enabled = True  # فعال‌سازی نوتیفیکیشن برای تهدیدات

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین فایروال در حال راه‌اندازی...")

            # بارگیری لیست کاربران مسدود شده
            blocked_users = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'firewall_blocked_users'"
            )

            if blocked_users and 'value' in blocked_users:
                self.blocked_users = json.loads(blocked_users['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('firewall_blocked_users', json.dumps(self.blocked_users), 'لیست کاربران مسدود شده توسط فایروال')
                )

            # بارگیری کلمات کلیدی مسدود شده
            blocked_keywords = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'firewall_blocked_keywords'"
            )

            if blocked_keywords and 'value' in blocked_keywords:
                self.blocked_keywords = json.loads(blocked_keywords['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('firewall_blocked_keywords', json.dumps(self.blocked_keywords), 'کلمات کلیدی مسدود شده توسط فایروال')
                )

            # بارگیری لیست سفید
            whitelist = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'firewall_whitelist'"
            )

            if whitelist and 'value' in whitelist:
                self.whitelist = json.loads(whitelist['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('firewall_whitelist', json.dumps(self.whitelist), 'لیست سفید کاربران و گروه‌های استثنا شده از فایروال')
                )

            # بارگیری تنظیمات اسپم
            spam_settings = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'firewall_spam_settings'"
            )

            if spam_settings and 'value' in spam_settings:
                settings = json.loads(spam_settings['value'])
                self.spam_threshold = settings.get('threshold', 5)
                self.spam_window = settings.get('window', 60)
                self.auto_delete_spam = settings.get('auto_delete', True)
            else:
                spam_settings_data = {
                    'threshold': self.spam_threshold,
                    'window': self.spam_window,
                    'auto_delete': self.auto_delete_spam
                }
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('firewall_spam_settings', json.dumps(spam_settings_data), 'تنظیمات تشخیص اسپم فایروال')
                )

            # بارگیری وضعیت نوتیفیکیشن
            notification_setting = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'firewall_notification'"
            )

            if notification_setting and 'value' in notification_setting:
                self.notification_enabled = json.loads(notification_setting['value'])
            else:
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('firewall_notification', json.dumps(self.notification_enabled), 'وضعیت نوتیفیکیشن فایروال')
                )

            # ثبت دستورات
            self.register_command('fw_block', self.cmd_block_user, 'مسدود کردن کاربر', '.fw_block [user_id]')
            self.register_command('fw_unblock', self.cmd_unblock_user, 'رفع مسدودیت کاربر', '.fw_unblock [user_id]')
            self.register_command('fw_blocklist', self.cmd_show_blocklist, 'نمایش لیست مسدودشده‌ها', '.fw_blocklist')
            self.register_command('fw_keyword', self.cmd_manage_keyword, 'مدیریت کلمات کلیدی', '.fw_keyword [add|remove] [keyword]')
            self.register_command('fw_whitelist', self.cmd_manage_whitelist, 'مدیریت لیست سفید', '.fw_whitelist [add|remove] [id]')
            self.register_command('fw_spam', self.cmd_spam_settings, 'تنظیمات ضد اسپم', '.fw_spam [threshold|window|autodelete] [value]')
            self.register_command('fw_status', self.cmd_status, 'وضعیت فایروال', '.fw_status')
            self.register_command('fw_notify', self.cmd_toggle_notification, 'تغییر وضعیت نوتیفیکیشن', '.fw_notify [on|off]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_message, {})
            self.register_event_handler(EventType.MESSAGE, self.on_block_command, {'text_startswith': ['.fw_block', '/fw_block', '!fw_block']})
            self.register_event_handler(EventType.MESSAGE, self.on_unblock_command, {'text_startswith': ['.fw_unblock', '/fw_unblock', '!fw_unblock']})
            self.register_event_handler(EventType.MESSAGE, self.on_blocklist_command, {'text_startswith': ['.fw_blocklist', '/fw_blocklist', '!fw_blocklist']})
            self.register_event_handler(EventType.MESSAGE, self.on_keyword_command, {'text_startswith': ['.fw_keyword', '/fw_keyword', '!fw_keyword']})
            self.register_event_handler(EventType.MESSAGE, self.on_whitelist_command, {'text_startswith': ['.fw_whitelist', '/fw_whitelist', '!fw_whitelist']})
            self.register_event_handler(EventType.MESSAGE, self.on_spam_command, {'text_startswith': ['.fw_spam', '/fw_spam', '!fw_spam']})
            self.register_event_handler(EventType.MESSAGE, self.on_status_command, {'text_startswith': ['.fw_status', '/fw_status', '!fw_status']})
            self.register_event_handler(EventType.MESSAGE, self.on_notify_command, {'text_startswith': ['.fw_notify', '/fw_notify', '!fw_notify']})

            # زمان‌بندی پاکسازی منظم داده‌های موقت
            self.schedule(self.cleanup_temporary_data, interval=300, name="firewall_cleanup") \
                # هر 5 دقیقه \

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
