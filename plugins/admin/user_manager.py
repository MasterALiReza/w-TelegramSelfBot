"""
پلاگین مدیریت کاربران
این پلاگین امکان مدیریت کاربران و دسترسی‌های آنها را فراهم می‌کند.
"""
import logging
from typing import List, Optional
import json

from pyrogram.types import Message, User

from plugins.base_plugin import BasePlugin
from core.event_handler import EventType
from core.client import TelegramClient

logger = logging.getLogger(__name__)


class UserManagerPlugin(BasePlugin):
    """
    پلاگین مدیریت کاربران
    """

    def __init__(self):
        """
        مقداردهی اولیه
        """
        super().__init__()
        self.set_metadata(
            name="UserManager",
            version="1.0.0",
            description="مدیریت کاربران و دسترسی‌ها",
            author="SelfBot Team",
            category="admin"
        )
        self.client: Optional[TelegramClient] = None
        self.admin_users: List[int] = []
        self.trusted_users: List[int] = []
        self.blocked_users: List[int] = []

    async def initialize(self) -> bool:
        """
        راه‌اندازی پلاگین

        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # بارگیری تنظیمات از دیتابیس
            await self.get_db_connection()
            logger.info("پلاگین مدیریت کاربران در حال راه‌اندازی...")

            # بارگیری لیست کاربران از دیتابیس
            admin_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'admin_users'"
            )

            trusted_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'trusted_users'"
            )

            blocked_config = await self.fetch_one(
                "SELECT value FROM settings WHERE key = 'blocked_users'"
            )

            if admin_config and 'value' in admin_config:
                self.admin_users = json.loads(admin_config['value'])
            else:
                self.admin_users = []
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('admin_users', json.dumps(self.admin_users), 'لیست کاربران ادمین')
                )

            if trusted_config and 'value' in trusted_config:
                self.trusted_users = json.loads(trusted_config['value'])
            else:
                self.trusted_users = []
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('trusted_users', json.dumps(self.trusted_users), 'لیست کاربران مورد اعتماد')
                )

            if blocked_config and 'value' in blocked_config:
                self.blocked_users = json.loads(blocked_config['value'])
            else:
                self.blocked_users = []
                await self.db.execute(
                    "INSERT INTO settings (key, value, description) VALUES ($1, $2, $3)",
                    ('blocked_users', json.dumps(self.blocked_users), 'لیست کاربران مسدود شده')
                )

            # ثبت دستورات
            self.register_command('adduser', self.cmd_add_user, 'افزودن کاربر به لیست کاربران', '.adduser [شناسه_کاربر] [دسترسی]')
            self.register_command('deluser', self.cmd_del_user, 'حذف کاربر از لیست کاربران', '.deluser [شناسه_کاربر]')
            self.register_command('block', self.cmd_block_user, 'مسدود کردن کاربر', '.block [شناسه_کاربر]')
            self.register_command('unblock', self.cmd_unblock_user, 'رفع مسدودیت کاربر', '.unblock [شناسه_کاربر]')
            self.register_command('users', self.cmd_list_users, 'مشاهده لیست کاربران', '.users [admin|trusted|blocked]')

            # ثبت هندلرهای رویداد
            self.register_event_handler(EventType.MESSAGE, self.on_add_user_command, {'text_startswith': ['.adduser', '/adduser', '!adduser']})
            self.register_event_handler(EventType.MESSAGE, self.on_del_user_command, {'text_startswith': ['.deluser', '/deluser', '!deluser']})
            self.register_event_handler(EventType.MESSAGE, self.on_block_user_command, {'text_startswith': ['.block', '/block', '!block']})
            self.register_event_handler(EventType.MESSAGE, self.on_unblock_user_command, {'text_startswith': ['.unblock', '/unblock', '!unblock']})
            self.register_event_handler(EventType.MESSAGE, self.on_list_users_command, {'text_startswith': ['.users', '/users', '!users']})
            self.register_event_handler(EventType.MESSAGE, self.on_private_message, {'is_private': True})

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

            # ذخیره لیست‌های کاربران
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.admin_users), 'admin_users')
            )

            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.trusted_users), 'trusted_users')
            )

            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_users), 'blocked_users')
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

    async def is_trusted(self, user_id: int) -> bool:
        """
        بررسی مورد اعتماد بودن کاربر

        Args:
            user_id: شناسه کاربر

        Returns:
            bool: مورد اعتماد بودن کاربر
        """
        return user_id in self.trusted_users or user_id in self.admin_users

    async def is_blocked(self, user_id: int) -> bool:
        """
        بررسی مسدود بودن کاربر

        Args:
            user_id: شناسه کاربر

        Returns:
            bool: مسدود بودن کاربر
        """
        return user_id in self.blocked_users

    async def add_user_to_database(self, user: User, access_level: str = 'user') -> bool:
        """
        افزودن کاربر به دیتابیس

        Args:
            user: کاربر تلگرام
            access_level: سطح دسترسی

        Returns:
            bool: وضعیت افزودن
        """
        try:
            # بررسی وجود کاربر
            existing_user = await self.fetch_one(
                "SELECT id FROM users WHERE id = $1",
                (user.id,)
            )

            user_data = {
                'id': user.id,
                'username': user.username or '',
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'access_level': access_level,
                'is_admin': access_level == 'admin',
                'is_blocked': access_level == 'blocked',
                'updated_at': 'NOW()'
            }

            if existing_user:
                # بروزرسانی
                await self.update(
                    'users',
                    {k: v for k, v in user_data.items() if k != 'id'},
                    'id = $1',
                    (user.id,)
                )
            else:
                # ایجاد
                await self.insert('users', user_data)

            return True
        except Exception as e:
            logger.error(f"خطا در افزودن کاربر به دیتابیس: {str(e)}")
            return False

    async def cmd_add_user(self, client: TelegramClient, message: Message) -> None:
        """
        دستور افزودن کاربر

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

            if len(args) < 2:
                await message.reply_text(self._("invalid_adduser_command", default="دستور نامعتبر است. استفاده صحیح: `.adduser [شناسه_کاربر] [admin|trusted|user]`"))
                return

            try:
                user_id = int(args[0])
            except ValueError:
                await message.reply_text(self._("invalid_user_id", default="شناسه کاربر نامعتبر است."))
                return

            access_level = args[1].lower()
            if access_level not in ['admin', 'trusted', 'user']:
                await message.reply_text(self._("invalid_access_level", default="سطح دسترسی نامعتبر است. گزینه‌های مجاز: admin, trusted, user"))
                return

            # بررسی وجود کاربر در دیتابیس
            user_info = await self.fetch_one("SELECT * FROM users WHERE id = $1", (user_id,))

            # تلاش برای دریافت اطلاعات کاربر از تلگرام
            try:
                telegram_user = await client.get_users(user_id)
            except Exception:
                telegram_user = None

            # افزودن کاربر به لیست مربوطه
            if access_level == 'admin':
                if user_id not in self.admin_users:
                    self.admin_users.append(user_id)
                if user_id in self.trusted_users:
                    self.trusted_users.remove(user_id)
                if user_id in self.blocked_users:
                    self.blocked_users.remove(user_id)
            elif access_level == 'trusted':
                if user_id not in self.trusted_users:
                    self.trusted_users.append(user_id)
                if user_id in self.admin_users:
                    self.admin_users.remove(user_id)
                if user_id in self.blocked_users:
                    self.blocked_users.remove(user_id)
            elif access_level == 'user':
                if user_id in self.admin_users:
                    self.admin_users.remove(user_id)
                if user_id in self.trusted_users:
                    self.trusted_users.remove(user_id)
                if user_id in self.blocked_users:
                    self.blocked_users.remove(user_id)

            # ذخیره تغییرات در دیتابیس
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.admin_users), 'admin_users')
            )

            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.trusted_users), 'trusted_users')
            )

            # افزودن کاربر به دیتابیس
            if telegram_user:
                await self.add_user_to_database(telegram_user, access_level)
            elif user_info:
                # بروزرسانی سطح دسترسی
                await self.update(
                    'users',
                    {
                        'access_level': access_level,
                        'is_admin': access_level == 'admin',
                        'is_blocked': False,
                        'updated_at': 'NOW()'
                    },
                    'id = $1',
                    (user_id,)
                )
            else:
                # ایجاد کاربر با حداقل اطلاعات
                await self.insert('users', {
                    'id': user_id,
                    'access_level': access_level,
                    'is_admin': access_level == 'admin',
                    'is_blocked': False
                })

            # ارسال پاسخ
            username = f"@{telegram_user.username}" if telegram_user and telegram_user.username else f"ID: {user_id}"
            await message.reply_text(self._("user_added", default=f"کاربر {username} با سطح دسترسی {access_level} اضافه شد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور adduser: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_del_user(self, client: TelegramClient, message: Message) -> None:
        """
        دستور حذف کاربر

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

            if not args:
                await message.reply_text(self._("invalid_deluser_command", default="دستور نامعتبر است. استفاده صحیح: `.deluser [شناسه_کاربر]`"))
                return

            try:
                user_id = int(args[0])
            except ValueError:
                await message.reply_text(self._("invalid_user_id", default="شناسه کاربر نامعتبر است."))
                return

            # حذف کاربر از لیست‌ها
            if user_id in self.admin_users:
                self.admin_users.remove(user_id)

            if user_id in self.trusted_users:
                self.trusted_users.remove(user_id)

            if user_id in self.blocked_users:
                self.blocked_users.remove(user_id)

            # ذخیره تغییرات در دیتابیس
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.admin_users), 'admin_users')
            )

            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.trusted_users), 'trusted_users')
            )

            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_users), 'blocked_users')
            )

            # بروزرسانی در دیتابیس
            await self.update(
                'users',
                {
                    'access_level': 'user',
                    'is_admin': False,
                    'is_blocked': False,
                    'updated_at': 'NOW()'
                },
                'id = $1',
                (user_id,)
            )

            # ارسال پاسخ
            await message.reply_text(self._("user_removed", default=f"کاربر با شناسه {user_id} از لیست‌های دسترسی حذف شد."))

        except Exception as e:
            logger.error(f"خطا در اجرای دستور deluser: {str(e)}")
            await message.reply_text(self._("command_error", default="خطا در اجرای دستور."))

    async def cmd_block_user(self, client: TelegramClient, message: Message) -> None:
        """
        دستور مسدود کردن کاربر

        Args:
            client: کلاینت تلگرام
            message: پیام دریافتی
        """
        if not await self.is_admin(message.from_user.id):
            await message.reply_text(self._("not_admin", default="شما دسترسی لازم برای این دستور را ندارید."))
            return
