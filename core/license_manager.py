"""
ماژول مدیریت لایسنس برای سلف بات تلگرام
این ماژول وظیفه بررسی اعتبار و مدیریت لایسنس‌های نرم‌افزار را بر عهده دارد
"""

import os
import json
import time
import uuid
import hashlib
import hmac
import asyncio
import logging
import aiohttp
from typing import Dict, Any, Tuple
from datetime import datetime

from core.crypto import CryptoManager
from core.database_cache import DatabaseCache

logger = logging.getLogger(__name__)


class LicenseManager:
    """
    کلاس مدیریت لایسنس برای سلف بات تلگرام
    این کلاس امکان بررسی اعتبار، فعال‌سازی و مدیریت لایسنس‌ها را فراهم می‌کند
    """

    def __init__(self, db_cache: DatabaseCache, crypto_manager: CryptoManager):
        """
        مقداردهی اولیه مدیریت لایسنس

        Args:
            db_cache: نمونه کلاس DatabaseCache برای دسترسی به دیتابیس
            crypto_manager: نمونه کلاس CryptoManager برای رمزنگاری
        """
        self.db = db_cache
        self.crypto = crypto_manager
        self.license_data = None
        self.verification_lock = asyncio.Lock()
        self.license_server_url = os.getenv("LICENSE_SERVER_URL", "https://api.telegramSelfBot.com/license")
        self.app_signature = os.getenv("APP_SIGNATURE", "SelfBotTelegram2025")

        # زمان آخرین بررسی آنلاین
        self.last_online_check = 0
        # حداقل فاصله بین بررسی‌های آنلاین (به ثانیه)
        self.min_check_interval = 86400  # 24 ساعت

        # بارگذاری اطلاعات لایسنس در شروع
        asyncio.create_task(self.load_license_data())

    async def load_license_data(self) -> None:
        """بارگذاری اطلاعات لایسنس از دیتابیس"""
        try:
            # بررسی وجود جدول لایسنس
            await self._ensure_license_table()

            # دریافت اطلاعات لایسنس از دیتابیس
            license_record = await self.db.fetch_one(
                "licenses",
                "SELECT * FROM licenses WHERE is_active = true ORDER BY created_at DESC LIMIT 1"
            )

            if license_record:
                # رمزگشایی داده‌های لایسنس
                encrypted_data = license_record.get("license_data")
                if encrypted_data:
                    try:
                        decrypted_data = self.crypto.decrypt(encrypted_data)
                        self.license_data = json.loads(decrypted_data)
                        logger.info("اطلاعات لایسنس با موفقیت بارگذاری شد")
                    except Exception as e:
                        logger.error(f"خطا در رمزگشایی داده‌های لایسنس: {str(e)}")
                        self.license_data = None
            else:
                logger.warning("لایسنس فعالی یافت نشد")
                self.license_data = None

        except Exception as e:
            logger.error(f"خطا در بارگذاری اطلاعات لایسنس: {str(e)}")
            self.license_data = None

    async def _ensure_license_table(self) -> None:
        """اطمینان از وجود جدول لایسنس در دیتابیس"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS licenses (
            id SERIAL PRIMARY KEY,
            license_key TEXT NOT NULL UNIQUE,
            license_data TEXT NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
        """

        try:
            await self.db.execute(["licenses"], create_table_query)
            logger.debug("جدول لایسنس با موفقیت بررسی شد")
        except Exception as e:
            logger.error(f"خطا در ایجاد جدول لایسنس: {str(e)}")
            raise

    async def verify_license(self, force_online_check: bool = False) -> Tuple[bool, str]:
        """
        بررسی اعتبار لایسنس

        Args:
            force_online_check: اجبار به بررسی آنلاین حتی اگر زمان زیادی از بررسی قبلی نگذشته باشد

        Returns:
            یک tuple شامل وضعیت اعتبار (bool) و پیام توضیحی (str)
        """
        async with self.verification_lock:
            # بررسی وجود اطلاعات لایسنس
            if not self.license_data:
                return False, "لایسنس فعالی یافت نشد"

            # بررسی آنلاین اگر زمان کافی از بررسی قبلی گذشته یا اجبار به بررسی باشد
            current_time = time.time()
            should_check_online = (
                force_online_check or
                (current_time - self.last_online_check) > self.min_check_interval
            )

            # تاریخ انقضا
            expires_at = self.license_data.get("expires_at", 0)

            # اگر تاریخ انقضا از زمان فعلی کمتر باشد، لایسنس منقضی شده است
            if expires_at < current_time:
                return False, "لایسنس منقضی شده است"

            # بررسی امضای داخلی لایسنس
            if not self._verify_license_signature():
                return False, "امضای لایسنس نامعتبر است"

            # بررسی آنلاین لایسنس
            if should_check_online:
                try:
                    online_status, online_message = await self._check_license_online()
                    self.last_online_check = current_time

                    if not online_status:
                        return False, online_message
                except Exception as e:
                    logger.warning(f"خطا در بررسی آنلاین لایسنس: {str(e)}")
                    # اگر بررسی آنلاین با خطا مواجه شود، به بررسی آفلاین اکتفا می‌کنیم

            # اگر به اینجا رسیدیم، لایسنس معتبر است
            return True, "لایسنس معتبر است"

    def _verify_license_signature(self) -> bool:
        """
        بررسی امضای داخلی لایسنس

        Returns:
            True اگر امضا معتبر باشد، False در غیر این صورت
        """
        try:
            if not self.license_data:
                return False

            license_signature = self.license_data.get("signature")
            if not license_signature:
                return False

            # مقادیری که باید امضا شوند
            data_to_sign = {
                "license_key": self.license_data.get("license_key"),
                "user_id": self.license_data.get("user_id"),
                "email": self.license_data.get("email"),
                "created_at": self.license_data.get("created_at"),
                "expires_at": self.license_data.get("expires_at"),
                "features": self.license_data.get("features", []),
                "device_id": self.license_data.get("device_id")
            }

            # تبدیل به رشته JSON و سپس امضا
            data_string = json.dumps(data_to_sign, sort_keys=True)
            expected_signature = hmac.new(
                self.app_signature.encode(),
                data_string.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, license_signature)
        except Exception as e:
            logger.error(f"خطا در بررسی امضای لایسنس: {str(e)}")
            return False

    async def _check_license_online(self) -> Tuple[bool, str]:
        """
        بررسی آنلاین لایسنس از سرور

        Returns:
            یک tuple شامل وضعیت اعتبار (bool) و پیام توضیحی (str)
        """
        try:
            # تهیه داده‌های لازم برای بررسی آنلاین
            check_data = {
                "license_key": self.license_data.get("license_key"),
                "device_id": self.license_data.get("device_id"),
                "user_id": self.license_data.get("user_id"),
                "timestamp": int(time.time())
            }

            # امضای درخواست
            check_string = json.dumps(check_data, sort_keys=True)
            check_signature = hmac.new(
                self.app_signature.encode(),
                check_string.encode(),
                hashlib.sha256
            ).hexdigest()

            check_data["signature"] = check_signature

            # ارسال درخواست به سرور
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.license_server_url}/verify",
                    json=check_data,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "valid":
                            # به‌روزرسانی اطلاعات لایسنس اگر نیاز باشد
                            if data.get("license_data"):
                                await self._update_license_data(data["license_data"])
                            return True, "لایسنس معتبر است"
                        else:
                            reason = data.get("reason", "دلیل نامشخص")
                            return False, f"لایسنس نامعتبر است: {reason}"
                    else:
                        return False, f"خطا در بررسی آنلاین لایسنس: کد وضعیت {response.status}"
        except asyncio.TimeoutError:
            logger.warning("زمان بررسی آنلاین لایسنس به پایان رسید")
            # اگر نتوانیم با سرور ارتباط برقرار کنیم، به صورت آفلاین بررسی می‌کنیم
            return True, "لایسنس به صورت آفلاین تأیید شد"
        except Exception as e:
            logger.error(f"خطا در بررسی آنلاین لایسنس: {str(e)}")
            # در صورت خطا، به صورت آفلاین بررسی می‌کنیم
            return True, "لایسنس به صورت آفلاین تأیید شد"

    async def _update_license_data(self, new_data: Dict[str, Any]) -> None:
        """
        به‌روزرسانی اطلاعات لایسنس

        Args:
            new_data: داده‌های جدید لایسنس
        """
        try:
            # بررسی امضای داده‌های جدید
            license_signature = new_data.get("signature")
            if not license_signature:
                logger.error("امضا در داده‌های جدید لایسنس یافت نشد")
                return

            # مقادیری که باید امضا شوند
            data_to_sign = {
                "license_key": new_data.get("license_key"),
                "user_id": new_data.get("user_id"),
                "email": new_data.get("email"),
                "created_at": new_data.get("created_at"),
                "expires_at": new_data.get("expires_at"),
                "features": new_data.get("features", []),
                "device_id": new_data.get("device_id")
            }

            # تبدیل به رشته JSON و سپس امضا
            data_string = json.dumps(data_to_sign, sort_keys=True)
            expected_signature = hmac.new(
                self.app_signature.encode(),
                data_string.encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, license_signature):
                logger.error("امضای نامعتبر در داده‌های جدید لایسنس")
                return

            # ذخیره داده‌های جدید
            self.license_data = new_data

            # رمزنگاری و ذخیره در دیتابیس
            encrypted_data = self.crypto.encrypt(json.dumps(new_data))

            # به‌روزرسانی رکورد لایسنس
            await self.db.execute(
                ["licenses"],
                """
                UPDATE licenses
                SET license_data = $1, updated_at = CURRENT_TIMESTAMP, expires_at = $2
                WHERE license_key = $3
                """,
                (encrypted_data, datetime.fromtimestamp(new_data.get("expires_at", 0)), new_data.get("license_key"))
            )

            logger.info("اطلاعات لایسنس با موفقیت به‌روزرسانی شد")
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی اطلاعات لایسنس: {str(e)}")

    async def activate_license(self, license_key: str, email: str) -> Tuple[bool, str]:
        """
        فعال‌سازی لایسنس جدید

        Args:
            license_key: کلید لایسنس
            email: ایمیل مرتبط با لایسنس

        Returns:
            یک tuple شامل وضعیت عملیات (bool) و پیام نتیجه (str)
        """
        try:
            # تولید شناسه دستگاه منحصر به فرد
            device_id = self._generate_device_id()

            # تهیه داده‌های لازم برای فعال‌سازی
            activation_data = {
                "license_key": license_key,
                "email": email,
                "device_id": device_id,
                "timestamp": int(time.time()),
                "app_version": os.getenv("APP_VERSION", "1.0.0")
            }

            # امضای درخواست
            activation_string = json.dumps(activation_data, sort_keys=True)
            activation_signature = hmac.new(
                self.app_signature.encode(),
                activation_string.encode(),
                hashlib.sha256
            ).hexdigest()

            activation_data["signature"] = activation_signature

            # ارسال درخواست به سرور
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.license_server_url}/activate",
                    json=activation_data,
                    timeout=30
                ) as response:
                    data = await response.json()

                    if response.status == 200 and data.get("status") == "success":
                        # ذخیره اطلاعات لایسنس
                        license_data = data.get("license_data")
                        if not license_data:
                            return False, "اطلاعات لایسنس از سرور دریافت نشد"

                        # ذخیره لایسنس جدید
                        await self._save_license(license_data)
                        return True, "لایسنس با موفقیت فعال شد"
                    else:
                        error_message = data.get("message", "خطای نامشخص در فعال‌سازی لایسنس")
                        return False, error_message
        except asyncio.TimeoutError:
            return False, "زمان فعال‌سازی لایسنس به پایان رسید. لطفاً دوباره تلاش کنید"
        except Exception as e:
            logger.error(f"خطا در فعال‌سازی لایسنس: {str(e)}")
            return False, f"خطا در فعال‌سازی لایسنس: {str(e)}"

    async def _save_license(self, license_data: Dict[str, Any]) -> None:
        """
        ذخیره اطلاعات لایسنس در دیتابیس

        Args:
            license_data: داده‌های لایسنس
        """
        try:
            # بررسی امضای لایسنس
            if not self._verify_license_signature_data(license_data):
                raise ValueError("امضای لایسنس نامعتبر است")

            # غیرفعال کردن تمام لایسنس‌های قبلی
            await self.db.execute(
                ["licenses"],
                "UPDATE licenses SET is_active = false, updated_at = CURRENT_TIMESTAMP WHERE is_active = true"
            )

            # رمزنگاری داده‌های لایسنس
            encrypted_data = self.crypto.encrypt(json.dumps(license_data))

            # ذخیره لایسنس جدید
            expires_at = datetime.fromtimestamp(license_data.get("expires_at", 0))

            await self.db.execute(
                ["licenses"],
                """
                INSERT INTO licenses (license_key, license_data, is_active, expires_at)
                VALUES ($1, $2, true, $3)
                ON CONFLICT (license_key)
                DO UPDATE SET
                license_data = $2, is_active = true, updated_at = CURRENT_TIMESTAMP, expires_at = $3
                """,
                (license_data.get("license_key"), encrypted_data, expires_at)
            )

            # به‌روزرسانی متغیر اطلاعات لایسنس
            self.license_data = license_data
            self.last_online_check = time.time()

            logger.info("لایسنس جدید با موفقیت ذخیره شد")
        except Exception as e:
            logger.error(f"خطا در ذخیره لایسنس: {str(e)}")
            raise

    def _verify_license_signature_data(self, license_data: Dict[str, Any]) -> bool:
        """
        بررسی امضای داده‌های لایسنس

        Args:
            license_data: داده‌های لایسنس برای بررسی

        Returns:
            True اگر امضا معتبر باشد، False در غیر این صورت
        """
        try:
            license_signature = license_data.get("signature")
            if not license_signature:
                return False

            # مقادیری که باید امضا شوند
            data_to_sign = {
                "license_key": license_data.get("license_key"),
                "user_id": license_data.get("user_id"),
                "email": license_data.get("email"),
                "created_at": license_data.get("created_at"),
                "expires_at": license_data.get("expires_at"),
                "features": license_data.get("features", []),
                "device_id": license_data.get("device_id")
            }

            # تبدیل به رشته JSON و سپس امضا
            data_string = json.dumps(data_to_sign, sort_keys=True)
            expected_signature = hmac.new(
                self.app_signature.encode(),
                data_string.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, license_signature)
        except Exception as e:
            logger.error(f"خطا در بررسی امضای لایسنس: {str(e)}")
            return False

    def _generate_device_id(self) -> str:
        """
        تولید شناسه دستگاه منحصر به فرد

        Returns:
            شناسه دستگاه
        """
        try:
            # بررسی وجود فایل device_id
            device_id_file = os.path.join(os.path.expanduser("~"), ".selfbot_device_id")

            if os.path.exists(device_id_file):
                # خواندن شناسه دستگاه از فایل
                with open(device_id_file, "r") as f:
                    device_id = f.read().strip()
                    if device_id:
                        return device_id

            # تولید شناسه دستگاه جدید
            device_id = str(uuid.uuid4())

            # ذخیره شناسه دستگاه در فایل
            with open(device_id_file, "w") as f:
                f.write(device_id)

            return device_id
        except Exception as e:
            logger.error(f"خطا در تولید شناسه دستگاه: {str(e)}")
            # در صورت خطا، یک شناسه موقت تولید می‌کنیم
            return str(uuid.uuid4())

    def has_feature(self, feature_name: str) -> bool:
        """
        بررسی دسترسی به یک ویژگی خاص در لایسنس

        Args:
            feature_name: نام ویژگی مورد نظر

        Returns:
            True اگر ویژگی در لایسنس وجود داشته باشد، False در غیر این صورت
        """
        if not self.license_data:
            return False

        features = self.license_data.get("features", [])
        return feature_name in features or "all_features" in features

    async def get_license_info(self) -> Dict[str, Any]:
        """
        دریافت اطلاعات لایسنس

        Returns:
            Dictionary حاوی اطلاعات لایسنس
        """
        # بررسی وجود لایسنس
        if not self.license_data:
            return {
                "status": "no_license",
                "message": "لایسنسی فعال نیست"
            }

        # بررسی اعتبار لایسنس
        is_valid, message = await self.verify_license()

        # زمان انقضا
        expires_at = self.license_data.get("expires_at", 0)
        expires_date = datetime.fromtimestamp(expires_at).strftime("%Y-%m-%d %H:%M:%S")

        # محاسبه روزهای باقی‌مانده
        days_left = max(0, int((expires_at - time.time()) / 86400))

        return {
            "status": "valid" if is_valid else "invalid",
            "message": message,
            "license_key": self.license_data.get("license_key"),
            "email": self.license_data.get("email"),
            "expires_at": expires_date,
            "days_left": days_left,
            "features": self.license_data.get("features", []),
            "user_id": self.license_data.get("user_id")
        }

    async def deactivate_license(self) -> Tuple[bool, str]:
        """
        غیرفعال کردن لایسنس فعلی

        Returns:
            یک tuple شامل وضعیت عملیات (bool) و پیام نتیجه (str)
        """
        try:
            # بررسی وجود لایسنس
            if not self.license_data:
                return False, "لایسنسی فعال نیست"

            # تهیه داده‌های لازم برای غیرفعال‌سازی
            deactivation_data = {
                "license_key": self.license_data.get("license_key"),
                "device_id": self.license_data.get("device_id"),
                "timestamp": int(time.time())
            }

            # امضای درخواست
            deactivation_string = json.dumps(deactivation_data, sort_keys=True)
            deactivation_signature = hmac.new(
                self.app_signature.encode(),
                deactivation_string.encode(),
                hashlib.sha256
            ).hexdigest()

            deactivation_data["signature"] = deactivation_signature

            # ارسال درخواست به سرور
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.license_server_url}/deactivate",
                    json=deactivation_data,
                    timeout=30
                ) as response:
                    data = await response.json()

                    if response.status == 200 and data.get("status") == "success":
                        # غیرفعال کردن لایسنس در دیتابیس
                        await self.db.execute(
                            ["licenses"],
                            "UPDATE licenses SET is_active = false, updated_at = CURRENT_TIMESTAMP WHERE license_key = $1",
                            (self.license_data.get("license_key"),)
                        )

                        # پاک کردن اطلاعات لایسنس از حافظه
                        self.license_data = None

                        return True, "لایسنس با موفقیت غیرفعال شد"
                    else:
                        error_message = data.get("message", "خطای نامشخص در غیرفعال‌سازی لایسنس")
                        return False, error_message
        except Exception as e:
            logger.error(f"خطا در غیرفعال‌سازی لایسنس: {str(e)}")
            return False, f"خطا در غیرفعال‌سازی لایسنس: {str(e)}"
