"""
ادامه پلاگین فایروال امنیتی - بخش سوم (دستورات کاربری)
"""

# این بخش‌ها باید به فایل firewall.py اضافه شوند

    async def cmd_block_user(self, client: TelegramClient, message: Message) -> None:
        """
        دستور مسدود کردن کاربر

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if not args:
                await message.reply_text("لطفاً شناسه کاربر مورد نظر را وارد کنید. مثال: `.fw_block 123456789`")
                return

            try:
                user_id = int(args[0])
            except ValueError:
                await message.reply_text("شناسه کاربر باید یک عدد صحیح باشد.")
                return

            # بررسی تکراری نبودن
            if user_id in self.blocked_users:
                await message.reply_text(f"کاربر {user_id} قبلاً در لیست مسدود شده‌ها قرار دارد.")
                return

            # اضافه کردن به لیست مسدود شده
            self.blocked_users.append(user_id)

            # ذخیره در دیتابیس
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_users), 'firewall_blocked_users')
            )

            # ثبت رویداد
            await self.record_security_event("مسدود کردن کاربر", {
                "user_id": user_id,
                "blocked_by": message.from_user.id if message.from_user else 0,
                "reason": args[1] if len(args) > 1 else "دلیل ذکر نشده است"
            })

            await message.reply_text(f"✅ کاربر {user_id} به لیست مسدود شده‌ها اضافه شد.")

        except Exception as e:
            logger.error(f"خطا در اجرای دستور block_user: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")

    async def cmd_unblock_user(self, client: TelegramClient, message: Message) -> None:
        """
        دستور رفع مسدودیت کاربر

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if not args:
                await message.reply_text("لطفاً شناسه کاربر مورد نظر را وارد کنید. مثال: `.fw_unblock 123456789`")
                return

            try:
                user_id = int(args[0])
            except ValueError:
                await message.reply_text("شناسه کاربر باید یک عدد صحیح باشد.")
                return

            # بررسی وجود در لیست
            if user_id not in self.blocked_users:
                await message.reply_text(f"کاربر {user_id} در لیست مسدود شده‌ها وجود ندارد.")
                return

            # حذف از لیست مسدود شده
            self.blocked_users.remove(user_id)

            # ذخیره در دیتابیس
            await self.db.execute(
                "UPDATE settings SET value = $1 WHERE key = $2",
                (json.dumps(self.blocked_users), 'firewall_blocked_users')
            )

            # ثبت رویداد
            await self.record_security_event("رفع مسدودیت کاربر", {
                "user_id": user_id,
                "unblocked_by": message.from_user.id if message.from_user else 0
            })

            await message.reply_text(f"✅ کاربر {user_id} از لیست مسدود شده‌ها حذف شد.")

        except Exception as e:
            logger.error(f"خطا در اجرای دستور unblock_user: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")

    async def cmd_show_blocklist(self, client: TelegramClient, message: Message) -> None:
        """
        دستور نمایش لیست مسدودشده‌ها

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            if not self.blocked_users and not self.blocked_keywords:
                await message.reply_text("📝 لیست مسدودشده‌ها خالی است.")
                return

            response = "📝 **لیست مسدودشده‌های فایروال**\n\n"

            if self.blocked_users:
                response += "👤 **کاربران مسدود شده**:\n"
                for user_id in self.blocked_users:
                    response += f"• `{user_id}`\n"
                response += "\n"

            if self.blocked_keywords:
                response += "🔤 **کلمات کلیدی مسدود شده**:\n"
                for keyword in self.blocked_keywords:
                    response += f"• `{keyword}`\n"

            await message.reply_text(response)

        except Exception as e:
            logger.error(f"خطا در اجرای دستور show_blocklist: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")

    async def cmd_manage_keyword(self, client: TelegramClient, message: Message) -> None:
        """
        دستور مدیریت کلمات کلیدی

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if len(args) < 2:
                await message.reply_text(
                    "لطفاً عملیات و کلمه کلیدی را وارد کنید.\n"
                    "مثال برای افزودن: `.fw_keyword add کلمه_ممنوع`\n"
                    "مثال برای حذف: `.fw_keyword remove کلمه_ممنوع`"
                )
                return

            action = args[0].lower()
            keyword = args[1]

            if action == "add":
                # بررسی تکراری نبودن
                if keyword in self.blocked_keywords:
                    await message.reply_text(f"کلمه کلیدی '{keyword}' قبلاً در لیست قرار دارد.")
                    return

                # اضافه کردن به لیست
                self.blocked_keywords.append(keyword)

                # ذخیره در دیتابیس
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (json.dumps(self.blocked_keywords), 'firewall_blocked_keywords')
                )

                await message.reply_text(f"✅ کلمه کلیدی '{keyword}' به لیست مسدود شده‌ها اضافه شد.")

            elif action == "remove":
                # بررسی وجود در لیست
                if keyword not in self.blocked_keywords:
                    await message.reply_text(f"کلمه کلیدی '{keyword}' در لیست وجود ندارد.")
                    return

                # حذف از لیست
                self.blocked_keywords.remove(keyword)

                # ذخیره در دیتابیس
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (json.dumps(self.blocked_keywords), 'firewall_blocked_keywords')
                )

                await message.reply_text(f"✅ کلمه کلیدی '{keyword}' از لیست مسدود شده‌ها حذف شد.")

            else:
                await message.reply_text("عملیات نامعتبر. از `add` یا `remove` استفاده کنید.")

        except Exception as e:
            logger.error(f"خطا در اجرای دستور manage_keyword: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")

    async def cmd_manage_whitelist(self, client: TelegramClient, message: Message) -> None:
        """
        دستور مدیریت لیست سفید

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if len(args) < 2:
                await message.reply_text(
                    "لطفاً عملیات و شناسه را وارد کنید.\n"
                    "مثال برای افزودن: `.fw_whitelist add 123456789`\n"
                    "مثال برای حذف: `.fw_whitelist remove 123456789`\n"
                    "مثال برای مشاهده: `.fw_whitelist show`"
                )
                return

            action = args[0].lower()

            if action == "show":
                if not self.whitelist:
                    await message.reply_text("📝 لیست سفید خالی است.")
                    return

                response = "📝 **لیست سفید فایروال**\n\n"
                for item_id in self.whitelist:
                    response += f"• `{item_id}`\n"

                await message.reply_text(response)
                return

            try:
                item_id = int(args[1])
            except ValueError:
                await message.reply_text("شناسه باید یک عدد صحیح باشد.")
                return

            if action == "add":
                # بررسی تکراری نبودن
                if item_id in self.whitelist:
                    await message.reply_text(f"شناسه {item_id} قبلاً در لیست سفید قرار دارد.")
                    return

                # اضافه کردن به لیست
                self.whitelist.append(item_id)

                # ذخیره در دیتابیس
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (json.dumps(self.whitelist), 'firewall_whitelist')
                )

                await message.reply_text(f"✅ شناسه {item_id} به لیست سفید اضافه شد.")

            elif action == "remove":
                # بررسی وجود در لیست
                if item_id not in self.whitelist:
                    await message.reply_text(f"شناسه {item_id} در لیست سفید وجود ندارد.")
                    return

                # حذف از لیست
                self.whitelist.remove(item_id)

                # ذخیره در دیتابیس
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (json.dumps(self.whitelist), 'firewall_whitelist')
                )

                await message.reply_text(f"✅ شناسه {item_id} از لیست سفید حذف شد.")

            else:
                await message.reply_text("عملیات نامعتبر. از `add`، `remove` یا `show` استفاده کنید.")

        except Exception as e:
            logger.error(f"خطا در اجرای دستور manage_whitelist: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")

    async def cmd_spam_settings(self, client: TelegramClient, message: Message) -> None:
        """
        دستور تنظیمات ضد اسپم

        Args:
            client (TelegramClient): کلاینت تلگرام
            message (Message): پیام دریافتی
        """
        try:
            # دریافت آرگومان‌ها
            args = message.text.split()[1:]

            if not args:
                # نمایش تنظیمات فعلی
                response = "🛡️ **تنظیمات ضد اسپم**\n\n"
                response += f"• **آستانه**: {self.spam_threshold} پیام\n"
                response += f"• **پنجره زمانی**: {self.spam_window} ثانیه\n"
                response += f"• **حذف خودکار**: {'فعال' if self.auto_delete_spam else 'غیرفعال'}"

                await message.reply_text(response)
                return

            if len(args) < 2:
                await message.reply_text(
                    "لطفاً پارامتر و مقدار را وارد کنید.\n"
                    "مثال: `.fw_spam threshold 5`\n"
                    "پارامترهای موجود: threshold, window, autodelete"
                )
                return

            param = args[0].lower()
            value = args[1].lower()

            if param == "threshold":
                try:
                    threshold = int(value)
                    if threshold < 1:
                        await message.reply_text("آستانه باید یک عدد مثبت باشد.")
                        return
                    self.spam_threshold = threshold

                    # ذخیره در دیتابیس
                    spam_settings_data = {
                        'threshold': self.spam_threshold,
                        'window': self.spam_window,
                        'auto_delete': self.auto_delete_spam
                    }
                    await self.db.execute(
                        "UPDATE settings SET value = $1 WHERE key = $2",
                        (json.dumps(spam_settings_data), 'firewall_spam_settings')
                    )

                    await message.reply_text(f"✅ آستانه اسپم به {threshold} پیام تغییر یافت.")
                except ValueError:
                    await message.reply_text("مقدار آستانه باید یک عدد صحیح باشد.")

            elif param == "window":
                try:
                    window = int(value)
                    if window < 1:
                        await message.reply_text("پنجره زمانی باید یک عدد مثبت باشد.")
                        return
                    self.spam_window = window

                    # ذخیره در دیتابیس
                    spam_settings_data = {
                        'threshold': self.spam_threshold,
                        'window': self.spam_window,
                        'auto_delete': self.auto_delete_spam
                    }
                    await self.db.execute(
                        "UPDATE settings SET value = $1 WHERE key = $2",
                        (json.dumps(spam_settings_data), 'firewall_spam_settings')
                    )

                    await message.reply_text(f"✅ پنجره زمانی اسپم به {window} ثانیه تغییر یافت.")
                except ValueError:
                    await message.reply_text("مقدار پنجره زمانی باید یک عدد صحیح باشد.")

            elif param == "autodelete":
                if value in ["on", "true", "1", "yes"]:
                    self.auto_delete_spam = True
                    status = "فعال"
                elif value in ["off", "false", "0", "no"]:
                    self.auto_delete_spam = False
                    status = "غیرفعال"
                else:
                    await message.reply_text("مقدار نامعتبر. از on یا off استفاده کنید.")
                    return

                # ذخیره در دیتابیس
                spam_settings_data = {
                    'threshold': self.spam_threshold,
                    'window': self.spam_window,
                    'auto_delete': self.auto_delete_spam
                }
                await self.db.execute(
                    "UPDATE settings SET value = $1 WHERE key = $2",
                    (json.dumps(spam_settings_data), 'firewall_spam_settings')
                )

                await message.reply_text(f"✅ حذف خودکار پیام‌های اسپم {status} شد.")

            else:
                await message.reply_text(
                    "پارامتر نامعتبر. از یکی از موارد زیر استفاده کنید:\n"
                    "• threshold: آستانه تعداد پیام\n"
                    "• window: پنجره زمانی (ثانیه)\n"
                    "• autodelete: حذف خودکار (on/off)"
                )

        except Exception as e:
            logger.error(f"خطا در اجرای دستور spam_settings: {str(e)}")
            await message.reply_text("خطا در اجرای دستور. لطفاً بعداً دوباره تلاش کنید.")
