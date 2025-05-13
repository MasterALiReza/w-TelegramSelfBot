"""
ادامه پلاگین فایروال امنیتی - بخش چهارم (هندلرها و دستورات اضافی)
"""

# این بخش‌ها باید به فایل firewall.py اضافه شوند

    async def cmd_status(self, client: TelegramClient, message: Message) -> None:
        """
        دستور نمایش وضعیت فایروال

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            # جمع‌آوری آمار
            unique_active_users = len(self.user_message_count)
            blocklist_count = len(self.blocked_users)
            keyword_count = len(self.blocked_keywords)
            whitelist_count = len(self.whitelist)

            # ساخت پاسخ
            status = "فعال" if self.is_enabled else "غیرفعال"
            notifications = "فعال" if self.notification_enabled else "غیرفعال"

            response = f"""🛡️ **وضعیت فایروال**

• **وضعیت**: {status}
• **نوتیفیکیشن‌ها**: {notifications}
• **تنظیمات ضد اسپم**:
  - آستانه: {self.spam_threshold} پیام
  - پنجره زمانی: {self.spam_window} ثانیه
  - حذف خودکار: {'فعال' if self.auto_delete_spam else 'غیرفعال'}
• **آمار**:
  - کاربران فعال: {unique_active_users}
  - کاربران مسدود شده: {blocklist_count}
  - کلمات کلیدی مسدود: {keyword_count}
  - لیست سفید: {whitelist_count}

💡 برای دریافت کمک بیشتر از `.fw_help` استفاده کنید.
"""

            await message.reply_text(response)

        except Exception as e:
            logger.error(f"خطا در اجرای دستور status: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")

    async def cmd_toggle_notification(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تغییر وضعیت نوتیفیکیشن

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if args and args[0].lower() in ['on', 'off']:
                self.notification_enabled = args[0].lower() == 'on'
            else:
                # تغییر وضعیت فعلی
                self.notification_enabled = not self.notification_enabled

            # ذخیره در دیتابیس
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.notification_enabled), 'firewall_notification')
            )

            # ارسال پاسخ
            status = "فعال" if self.notification_enabled else "غیرفعال"
            await message.reply_text(f"✅ نوتیفیکیشن‌های فایروال {status} شد.")

        except Exception as e:
            logger.error(f"خطا در اجرای دستور toggle_notification: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")

    # هندلرهای دستورات

    async def on_block_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور مسدود کردن کاربر
        """
        await self.cmd_block_user(client, message)

    async def on_unblock_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور رفع مسدودیت کاربر
        """
        await self.cmd_unblock_user(client, message)

    async def on_blocklist_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور نمایش لیست مسدودشده‌ها
        """
        await self.cmd_show_blocklist(client, message)

    async def on_keyword_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور مدیریت کلمات کلیدی
        """
        await self.cmd_manage_keyword(client, message)

    async def on_whitelist_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور مدیریت لیست سفید
        """
        await self.cmd_manage_whitelist(client, message)

    async def on_spam_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تنظیمات ضد اسپم
        """
        await self.cmd_spam_settings(client, message)

    async def on_status_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور نمایش وضعیت فایروال
        """
        await self.cmd_status(client, message)

    async def on_notify_command(self, client: TelegramClient, message: Message) -> None:
        """
        هندلر دستور تغییر وضعیت نوتیفیکیشن
        """
        await self.cmd_toggle_notification(client, message)
