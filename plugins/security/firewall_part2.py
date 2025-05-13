"""
ادامه پلاگین فایروال امنیتی - بخش دوم
"""

# این بخش‌ها باید به فایل firewall.py اضافه شوند

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

            # ذخیره لیست کاربران مسدود شده
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_users), 'firewall_blocked_users')
            )

            # ذخیره کلمات کلیدی مسدود شده
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_keywords), 'firewall_blocked_keywords')
            )

            # ذخیره لیست سفید
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.whitelist), 'firewall_whitelist')
            )

            # ذخیره تنظیمات اسپم
            spam_settings_data = {
                'threshold': self.spam_threshold,
                'window': self.spam_window,
                'auto_delete': self.auto_delete_spam
            }
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(spam_settings_data), 'firewall_spam_settings')
            )

            # ذخیره وضعیت نوتیفیکیشن
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.notification_enabled), 'firewall_notification')
            )

            return True
        except Exception as e:
            logger.error(f"خطا در پاکسازی پلاگین {self.name}: {str(e)}")
            return False

    async def on_message(self, client: TelegramClient, message: Message) -> None:
        """
        پردازش پیام‌های دریافتی

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        if not self.is_enabled:
            return

        # بررسی لیست سفید
        if message.from_user and message.from_user.id in self.whitelist:
            return

        if message.chat and message.chat.id in self.whitelist:
            return

        # بررسی لیست مسدود شده
        if message.from_user and message.from_user.id in self.blocked_users:
            logger.info(f"پیام از کاربر مسدود شده {message.from_user.id} حذف شد")

            # ثبت رویداد امنیتی
            await self.record_security_event("پیام از کاربر مسدود شده", {
                "user_id": message.from_user.id,
                "username": message.from_user.username if message.from_user.username else "نامشخص",
                "chat_id": message.chat.id if message.chat else 0,
                "chat_title": message.chat.title if message.chat and hasattr(message.chat, 'title') \
                    \ \
                    \ \
                    else "نامشخص", \
                "message_text": message.text if message.text else "(بدون متن)"
            })

            # حذف پیام (اگر اجازه دسترسی داریم)
            try:
                await message.delete()
            except Exception as e:
                logger.error(f"خطا در حذف پیام از کاربر مسدود شده: {str(e)}")

            return

        # بررسی کلمات کلیدی مسدود شده
        if message.text:
            for keyword in self.blocked_keywords:
                if re.search(rf"\b{re.escape(keyword)}\b", message.text, re.IGNORECASE):
                    logger.info(f"پیام حاوی کلمه کلیدی مسدود شده '{keyword}' از کاربر {message.from_user.id if message.from_user else 'نامشخص'} شناسایی شد")

                    # ثبت رویداد امنیتی
                    await self.record_security_event("پیام حاوی کلمه کلیدی مسدود شده", {
                        "keyword": keyword,
                        "user_id": message.from_user.id if message.from_user else 0,
                        "username": message.from_user.username if message.from_user and message.from_user.username else "نامشخص",
                        "chat_id": message.chat.id if message.chat else 0,
                        "message_text": message.text
                    })

                    # حذف پیام (اگر اجازه دسترسی داریم)
                    try:
                        await message.delete()
                    except Exception as e:
                        logger.error(f"خطا در حذف پیام حاوی کلمه کلیدی مسدود شده: {str(e)}")

                    # اطلاع به کاربر
                    if self.notification_enabled and message.from_user:
                        try:
                            await client.send_message(
                                message.chat.id,
                                f"⚠️ پیام از کاربر {message.from_user.mention() \
                                    } به دلیل محتوای نامناسب حذف شد." \
                            )
                        except Exception as e:
                            logger.error(f"خطا در ارسال نوتیفیکیشن برای کلمه کلیدی مسدود شده: {str(e)}")

                    return

        # بررسی اسپم
        if message.from_user:
            # بروزرسانی تعداد پیام‌های کاربر
            current_time = time.time()

            # پاکسازی داده‌های قدیمی
            if current_time - self.last_cleanup_time > 60:
                await self.cleanup_temporary_data()

            user_id = message.from_user.id

            if user_id not in self.user_message_count:
                self.user_message_count[user_id] = []

            # اضافه کردن زمان پیام جاری
            self.user_message_count[user_id].append(current_time)

            # حذف پیام‌های قدیمی‌تر از پنجره زمانی
            self.user_message_count[user_id] = [
                t for t in self.user_message_count[user_id]
                if current_time - t <= self.spam_window
            ]

            # بررسی آستانه اسپم
            if len(self.user_message_count[user_id]) > self.spam_threshold:
                logger.warning(f"فعالیت اسپم از کاربر {user_id} شناسایی شد! {len(self.user_message_count[user_id])} پیام در {self.spam_window} ثانیه")

                # ثبت رویداد امنیتی
                await self.record_security_event("تشخیص اسپم", {
                    "user_id": user_id,
                    "username": message.from_user.username if message.from_user.username else "نامشخص",
                    "chat_id": message.chat.id if message.chat else 0,
                    "message_count": len(self.user_message_count[user_id]),
                    "time_window": self.spam_window
                })

                # حذف پیام اگر تنظیم شده باشد
                if self.auto_delete_spam:
                    try:
                        await message.delete()
                    except Exception as e:
                        logger.error(f"خطا در حذف پیام اسپم: {str(e)}")

                # هشدار به کاربر
                if self.notification_enabled:
                    try:
                        await client.send_message(
                            message.chat.id,
                            f"⚠️ کاربر {message.from_user.mention() \
                                }: لطفاً از ارسال پیام‌های متعدد (اسپم) خودداری کنید." \
                        )
                    except Exception as e:
                        logger.error(f"خطا در ارسال هشدار اسپم: {str(e)}")

    async def cleanup_temporary_data(self) -> None:
        """
        پاکسازی داده‌های موقت
        """
        try:
            current_time = time.time()
            self.last_cleanup_time = current_time

            # پاکسازی تعداد پیام کاربران
            for user_id in list(self.user_message_count.keys()):
                # حذف پیام‌های قدیمی‌تر از پنجره زمانی
                self.user_message_count[user_id] = [
                    t for t in self.user_message_count[user_id]
                    if current_time - t <= self.spam_window
                ]

                # حذف کاربرانی که پیامی ندارند
                if not self.user_message_count[user_id]:
                    del self.user_message_count[user_id]

            logger.debug(f"پاکسازی داده‌های موقت فایروال انجام شد، {len(self.user_message_count)} کاربر در حافظه")

        except Exception as e:
            logger.error(f"خطا در پاکسازی داده‌های موقت فایروال: {str(e)}")

    async def record_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        ثبت رویداد امنیتی

        Args:
            event_type (str): نوع رویداد
            details (Dict[str, Any]): جزئیات رویداد
        """
        try:
            # دسترسی به پلاگین رویدادهای امنیتی
            security_events_plugin = self.plugin_manager.get_plugin("SecurityEvents")

            if security_events_plugin:
                # استفاده از متد پلاگین برای ثبت رویداد
                await security_events_plugin.record_security_event(
                    f"firewall_{event_type}",
                    details
                )
            else:
                # ثبت مستقیم در دیتابیس اگر پلاگین در دسترس نیست
                await self.insert('security_events', {
                    'event_type': f"firewall_{event_type}",
                    'details': json.dumps(details),
                    'is_resolved': False,
                    'created_at': 'NOW()'
                })

        except Exception as e:
            logger.error(f"خطا در ثبت رویداد امنیتی فایروال: {str(e)}")
