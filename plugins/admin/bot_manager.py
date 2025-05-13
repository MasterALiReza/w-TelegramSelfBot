"""
پلاگین مدیریت سلف بات
این پلاگین امکان کنترل و مدیریت اصلی سلف بات را فراهم می‌کند.
"""
import logging
import time
from typing import List, Optional
import json

from pyrogram.types import Message

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient

logger = logging.getLogger(__name__)


class BotManagerPlugin(BasePlugin):
    """
    پلاگین مدیریت سلف بات
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="BotManager",
            version="1.0.0",
            description="مدیریت سلف بات و دستورات اصلی",
            author="SelfBot Team",
            category="admin"
        )
        self.client: Optional[TelegramClient] = None
        self.admin_users: List[int] = []

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین مدیریت سلف بات در حال راه‌اندازی...")

            # بررسی و ایجاد جدول ادمین‌ها اگر وجود ندارد
            admin_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'admin_users'"
            )

            if admin_config and 'value' in admin_config:
                self.admin_users = admin_config['value']
            else:
                # مقدار پیش‌فرض
                self.admin_users = []
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('admin_users', json.dumps(self.admin_users), 'لیست کاربران ادمین')
                )

            # ثبت دستورات
            self.register_command('help', self.cmd_help, 'نمایش راهنمای دستورات', '.help [نام_دستور]')
            self.register_command('restart', self.cmd_restart, 'راه‌اندازی مجدد سلف بات', '.restart')
            self.register_command('status', self.cmd_status, 'نمایش وضعیت سلف بات', '.status')
            self.register_command('plugins', self.cmd_plugins, 'مدیریت پلاگین‌ها', '.plugins [list|enable|disable] [نام_پلاگین]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_help_command, {'text': ['.help', '/help', '!help']})
            self.register_event_handler(EventType.MESSAGE, self.on_restart_command, {'text': ['.restart', '/restart', '!restart']})
            self.register_event_handler(EventType.MESSAGE, self.on_status_command, {'text': ['.status', '/status', '!status']})
            self.register_event_handler(EventType.MESSAGE, self.on_plugins_command, {'text_startswith': ['.plugins', '/plugins', '!plugins']})

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
            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def is_admin(self, user_id: int) -> bool:
        """
        بررسی ادمین بودن کاربر

        Args:
            user_id: شناسه کاربر

        Returns:
            bool: ادمین بودن کاربر
        """
        return user_id in self.admin_users

    async def cmd_help(self, client: TelegramClient, message: Message) -> None:
        """
        دستور راهنما

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت لیست دستورات از دیتابیس
            commands = await self.fetch_all(
                """
                SELECT c.name, c.description, c.usage, p.name as plugin_name
                FROM commands c
                JOIN plugins p ON c.plugin_id = p.id
                WHERE p.is_enabled = TRUE
                ORDER BY p.name, c.name
                """
            )

            if not commands:
                await message.reply_text(self._("no_commands_found", default="دستوری یافت نشد."))
                return

            help_text = self._("help_header", default="📚 **راهنمای دستورات**\n\n")
            current_plugin = None

            for cmd in commands:
                if current_plugin != cmd['plugin_name']:
                    current_plugin = cmd['plugin_name']
                    help_text += f"\n**🔹 {current_plugin}:**\n"

                help_text += f"  • `{cmd['name']}`: {cmd['description']}\n"
                if cmd['usage']:
                    help_text += f"    استفاده: `{cmd['usage']}`\n"

            help_text += f"\n{self._('help_footer', default='برای اطلاعات بیشتر درباره هر دستور، از `.help [نام_دستور]` استفاده کنید.') \
                \ \
                \ \
                }" \

            await message.reply_text(help_text)

        except Exception as e:
            logger.error(f"خطا در اجرای دستور help: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_restart(self, client: TelegramClient, message: Message) -> None:
        """
        دستور راه‌اندازی مجدد

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        if not await self.is_admin(message.from_user.id):
            await message.reply_text(self._("not_admin", default="شما دسترسی لازم برای این دستور را ندارید."))
            return

        await message.reply_text(self._("restarting", default="♻️ در حال راه‌اندازی مجدد..."))

        # اجرای مجدد با تاخیر 3 ثانیه
        self.schedule_once(self._restart_bot, time.time() + 3, "restart_bot")

    async def _restart_bot(self) -> None:
        """
        راه‌اندازی مجدد سلف بات
        """
        try:
            logger.info("در حال راه‌اندازی مجدد سلف بات...")
            # ذخیره وضعیت فعلی
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps({'last_restart': time.time()}), 'bot_status')
            )

            # در اینجا باید لاجیک راه‌اندازی مجدد برنامه پیاده‌سازی شود
            # معمولاً این کار با اجرای مجدد اسکریپت اصلی انجام می‌شود
            # اما فعلاً یک پیغام لاگ می‌زنیم
            logger.info("درخواست راه‌اندازی مجدد دریافت شد. این عملیات نیاز به پیاده‌سازی در برنامه اصلی دارد.")

        except Exception as e:
            logger.error(f"خطا در راه‌اندازی مجدد سلف بات: {str(e)}")

    async def cmd_status(self, client: TelegramClient, message: Message) -> None:
        """
        دستور نمایش وضعیت

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        try:
            # دریافت آمار از دیتابیس
            plugin_count = await self.fetch_one("SELECT COUNT(*) as count FROM plugins WHERE is_enabled = TRUE")
            user_count = await self.fetch_one("SELECT COUNT(*) as count FROM users")
            chat_count = await self.fetch_one("SELECT COUNT(*) as count FROM chats")
            command_count = await self.fetch_one("SELECT COUNT(*) as count FROM commands")

            # آمار سیستم
            import psutil
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            uptime = int(time.time() - psutil.boot_time())
            days, remainder = divmod(uptime, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)

            status_text = f"""
📊 **وضعیت سلف بات**

⏱ زمان کارکرد سیستم: {days}d {hours}h {minutes}m {seconds}s
💾 مصرف حافظه: {memory.percent}% ({memory.used / (1024**3):.2f} GB / {memory.total / (1024**3):.2f} GB)
💽 مصرف دیسک: {disk.percent}% ({disk.used / (1024**3):.2f} GB / {disk.total / (1024**3):.2f} GB)
🔌 پلاگین‌های فعال: {plugin_count['count']}
👤 کاربران: {user_count['count']}
💬 گروه‌ها: {chat_count['count']}
🔧 دستورات: {command_count['count']}
            """

            await message.reply_text(status_text)

        except Exception as e:
            logger.error(f"خطا در اجرای دستور status: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_plugins(self, client: TelegramClient, message: Message) -> None:
        """
        دستور مدیریت پلاگین‌ها

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        if not await self.is_admin(message.from_user.id):
            await message.reply_text(self._("not_admin", default="شما دسترسی لازم برای این دستور را ندارید."))
            return

        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if not args or args[0].lower() == "list":
                # نمایش لیست پلاگین‌ها
                plugins = await self.fetch_all(
                    """
                    SELECT name, version, description, author, category, is_enabled
                    FROM plugins
                    ORDER BY category, name
                    """
                )

                if not plugins:
                    await message.reply_text(self._("no_plugins_found", default="پلاگینی یافت نشد."))
                    return

                plugins_text = self._("plugins_header", default="🧩 **لیست پلاگین‌ها**\n\n")
                current_category = None

                for plugin in plugins:
                    if current_category != plugin['category']:
                        current_category = plugin['category']
                        plugins_text += f"\n**📁 {current_category}:**\n"

                    status = "✅" if plugin['is_enabled'] else "❌"
                    plugins_text += f"  • {status} `{plugin['name']}` (v{plugin['version']}) \
                        : {plugin['description']}\n" \

                await message.reply_text(plugins_text)

            elif args[0].lower() in ["enable", "disable"] and len(args) > 1:
                # فعال/غیرفعال‌سازی پلاگین
                action = args[0].lower()
                plugin_name = args[1]

                # بررسی وجود پلاگین
                plugin = await self.fetch_one(
                    "SELECT id, is_enabled FROM plugins WHERE name = $1",
                    (plugin_name,)
                )

                if not plugin:
                    await message.reply_text(self._("plugin_not_found", default="پلاگین مورد نظر یافت نشد."))
                    return

                is_enabled = True if action == "enable" else False

                # بروزرسانی وضعیت پلاگین
                await self.db.execute(
                    "UPDATE plugins SET is_enabled = $1, updated_at = NOW() WHERE name = $2",
                    (is_enabled, plugin_name)
                )

                action_text = "فعال" if is_enabled else "غیرفعال"
                await message.reply_text(self._("plugin_status_changed", default=f"وضعیت پلاگین {plugin_name} به {action_text} تغییر یافت."))

            else:
                await message.reply_text(self._("invalid_plugin_command", default="دستور نامعتبر است. استفاده صحیح: `.plugins [list|enable|disable] [نام_پلاگین]`"))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور plugins: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def on_help_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور راهنما

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_help(client, message)

    async def on_restart_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور راه‌اندازی مجدد

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_restart(client, message)

    async def on_status_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور وضعیت

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_status(client, message)

    async def on_plugins_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور مدیریت پلاگین‌ها

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        await self.cmd_plugins(client, message)
