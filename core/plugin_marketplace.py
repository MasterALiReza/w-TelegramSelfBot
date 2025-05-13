"""
ماژول بازارچه پلاگین برای سلف بات تلگرام
این ماژول امکان جستجو، دانلود و مدیریت پلاگین‌های آنلاین را فراهم می‌کند
"""

import os
import json
import aiohttp
import zipfile
import tempfile
import logging
import asyncio
import shutil
import hmac
import hashlib
import time
from io import BytesIO
from typing import Dict, Any, List, Optional, Tuple, Union

from core.database_cache import DatabaseCache
from core.license_manager import LicenseManager

logger = logging.getLogger(__name__)


class PluginMarketplace:
    """
    کلاس بازارچه پلاگین برای سلف بات تلگرام
    این کلاس امکان جستجو، دانلود و مدیریت پلاگین‌های آنلاین را فراهم می‌کند
    """

    def __init__(self, db_cache: DatabaseCache, license_manager: LicenseManager):
        """
        مقداردهی اولیه بازارچه پلاگین

        Args:
            db_cache: نمونه کلاس DatabaseCache برای دسترسی به دیتابیس
            license_manager: نمونه کلاس LicenseManager برای بررسی لایسنس
        """
        self.db = db_cache
        self.license_manager = license_manager
        self.marketplace_url = os.getenv("MARKETPLACE_URL", "https://api.telegramSelfBot.com/marketplace")
        self.app_signature = os.getenv("APP_SIGNATURE", "SelfBotTelegram2025")
        self.plugins_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins"))
        self.cached_plugins = {}
        self.cache_timestamp = 0
        self.cache_ttl = 3600  # یک ساعت
        self.lock = asyncio.Lock()

    async def _ensure_marketplace_table(self) -> None:
        """اطمینان از وجود جدول بازارچه در دیتابیس"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS marketplace_plugins (
            id SERIAL PRIMARY KEY,
            plugin_id TEXT NOT NULL UNIQUE,
            plugin_name TEXT NOT NULL,
            version TEXT NOT NULL,
            author TEXT NOT NULL,
            description TEXT,
            category TEXT,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_installed BOOLEAN DEFAULT true
        )
        """

        try:
            await self.db.execute(["marketplace_plugins"], create_table_query)
            logger.debug("جدول بازارچه پلاگین با موفقیت بررسی شد")
        except Exception as e:
            logger.error(f"خطا در ایجاد جدول بازارچه پلاگین: {str(e)}")
            raise

    async def get_available_plugins(self, category: Optional[str] = None, refresh: bool = False) \
        -> List[Dict[str, Any]]: \
        """
        دریافت لیست پلاگین‌های موجود در بازارچه

        Args:
            category: دسته‌بندی پلاگین‌ها (اختیاری)
            refresh: بازنشانی کش و دریافت مجدد اطلاعات

        Returns:
            لیست پلاگین‌های موجود
        """
        async with self.lock:
            # بررسی اعتبار لایسنس
            is_valid, _ = await self.license_manager.verify_license()
            if not is_valid:
                logger.warning("لایسنس معتبر نیست، دسترسی به بازارچه محدود شده است")
                return []

            current_time = time.time()

            # اگر داده‌ها در کش وجود دارند و بازنشانی درخواست نشده است
            if not refresh and self.cached_plugins and (current_time - self.cache_timestamp) \
                < self.cache_ttl: \
                if category:
                    return [p for p in self.cached_plugins.get("plugins", []) \
                        if p.get("category") == category] \
                return self.cached_plugins.get("plugins", [])

            try:
                # تهیه داده‌های لازم برای درخواست
                request_data = {
                    "license_key": self.license_manager.license_data.get("license_key"),
                    "device_id": self.license_manager.license_data.get("device_id"),
                    "timestamp": int(current_time),
                    "category": category
                }

                # امضای درخواست
                request_string = json.dumps(request_data, sort_keys=True)
                request_signature = hmac.new(
                    self.app_signature.encode(),
                    request_string.encode(),
                    hashlib.sha256
                ).hexdigest()

                request_data["signature"] = request_signature

                # ارسال درخواست به سرور
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.marketplace_url}/plugins",
                        json=request_data,
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.cached_plugins = data
                            self.cache_timestamp = current_time

                            if category:
                                return [p for p in data.get("plugins", []) \
                                    if p.get("category") == category] \
                            return data.get("plugins", [])
                        else:
                            logger.error(f"خطا در دریافت پلاگین‌ها: کد وضعیت {response.status}")
                            return []
            except Exception as e:
                logger.error(f"خطا در دریافت پلاگین‌های بازارچه: {str(e)}")
                return []

    async def search_plugins(self, query: str) -> List[Dict[str, Any]]:
        """
        جستجوی پلاگین‌ها در بازارچه

        Args:
            query: عبارت جستجو

        Returns:
            لیست پلاگین‌های یافت شده
        """
        try:
            # دریافت تمام پلاگین‌ها
            all_plugins = await self.get_available_plugins()

            # جستجو در نام، توضیحات و برچسب‌ها
            query = query.lower()
            results = []

            for plugin in all_plugins:
                name = plugin.get("name", "").lower()
                description = plugin.get("description", "").lower()
                tags = [tag.lower() for tag in plugin.get("tags", [])]

                if (query in name or query in description or
                    any(query in tag for tag in tags)):
                    results.append(plugin)

            return results
        except Exception as e:
            logger.error(f"خطا در جستجوی پلاگین‌ها: {str(e)}")
            return []

    async def get_plugin_details(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        دریافت جزئیات یک پلاگین خاص

        Args:
            plugin_id: شناسه یکتای پلاگین

        Returns:
            اطلاعات کامل پلاگین یا None در صورت عدم موفقیت
        """
        try:
            # بررسی اعتبار لایسنس
            is_valid, _ = await self.license_manager.verify_license()
            if not is_valid:
                logger.warning("لایسنس معتبر نیست، دسترسی به بازارچه محدود شده است")
                return None

            # تهیه داده‌های لازم برای درخواست
            request_data = {
                "license_key": self.license_manager.license_data.get("license_key"),
                "device_id": self.license_manager.license_data.get("device_id"),
                "plugin_id": plugin_id,
                "timestamp": int(time.time())
            }

            # امضای درخواست
            request_string = json.dumps(request_data, sort_keys=True)
            request_signature = hmac.new(
                self.app_signature.encode(),
                request_string.encode(),
                hashlib.sha256
            ).hexdigest()

            request_data["signature"] = request_signature

            # ارسال درخواست به سرور
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.marketplace_url}/plugin/{plugin_id}",
                    json=request_data,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("plugin")
                    else:
                        logger.error(f"خطا در دریافت جزئیات پلاگین: کد وضعیت {response.status}")
                        return None
        except Exception as e:
            logger.error(f"خطا در دریافت جزئیات پلاگین: {str(e)}")
            return None

    async def download_and_install_plugin(self, plugin_id: str) -> Tuple[bool, str]:
        """
        دانلود و نصب یک پلاگین از بازارچه

        Args:
            plugin_id: شناسه یکتای پلاگین

        Returns:
            یک tuple شامل وضعیت عملیات (bool) و پیام نتیجه (str)
        """
        try:
            # بررسی اعتبار لایسنس
            is_valid, _ = await self.license_manager.verify_license()
            if not is_valid:
                return False, "لایسنس معتبر نیست، دسترسی به بازارچه محدود شده است"

            # دریافت جزئیات پلاگین
            plugin_details = await self.get_plugin_details(plugin_id)
            if not plugin_details:
                return False, f"جزئیات پلاگین {plugin_id} یافت نشد"

            # بررسی قابلیت‌های مورد نیاز
            required_features = plugin_details.get("required_features", [])
            for feature in required_features:
                if not self.license_manager.has_feature(feature):
                    return False, f"این پلاگین نیاز به ویژگی '{feature}' دارد که در لایسنس شما وجود ندارد"

            # تهیه داده‌های لازم برای دانلود
            download_data = {
                "license_key": self.license_manager.license_data.get("license_key"),
                "device_id": self.license_manager.license_data.get("device_id"),
                "plugin_id": plugin_id,
                "timestamp": int(time.time())
            }

            # امضای درخواست
            download_string = json.dumps(download_data, sort_keys=True)
            download_signature = hmac.new(
                self.app_signature.encode(),
                download_string.encode(),
                hashlib.sha256
            ).hexdigest()

            download_data["signature"] = download_signature

            # ارسال درخواست به سرور
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.marketplace_url}/download/{plugin_id}",
                    json=download_data,
                    timeout=60
                ) as response:
                    if response.status != 200:
                        return False, f"خطا در دانلود پلاگین: کد وضعیت {response.status}"

                    # دریافت فایل zip
                    content = await response.read()

                    # نصب پلاگین
                    result = await self._install_plugin_from_zip(
                        content,
                        plugin_details.get("name"),
                        plugin_details.get("plugin_id"),
                        plugin_details
                    )

                    return result
        except Exception as e:
            logger.error(f"خطا در دانلود و نصب پلاگین: {str(e)}")
            return False, f"خطا در دانلود و نصب پلاگین: {str(e)}"

    async def _install_plugin_from_zip(self, zip_content: bytes, plugin_name: str, plugin_id: str, plugin_details: Dict[str, Any]) \
        \ \
        \ \
        -> Tuple[bool, str]: \
        """
        نصب پلاگین از فایل زیپ

        Args:
            zip_content: محتوای فایل زیپ پلاگین
            plugin_name: نام پلاگین
            plugin_id: شناسه یکتای پلاگین
            plugin_details: جزئیات پلاگین

        Returns:
            یک tuple شامل وضعیت عملیات (bool) و پیام نتیجه (str)
        """
        temp_dir = None
        try:
            # اطمینان از وجود پوشه plugins
            os.makedirs(self.plugins_dir, exist_ok=True)

            # ایجاد پوشه موقت برای استخراج فایل‌ها
            temp_dir = tempfile.mkdtemp()

            # باز کردن فایل زیپ
            with zipfile.ZipFile(BytesIO(zip_content)) as zip_ref:
                # بررسی ساختار فایل زیپ
                file_list = zip_ref.namelist()

                # بررسی وجود فایل meta.json
                if "meta.json" not in file_list:
                    return False, "ساختار پلاگین نامعتبر است: فایل meta.json یافت نشد"

                # استخراج تمام فایل‌ها به پوشه موقت
                zip_ref.extractall(temp_dir)

                # خواندن فایل meta.json
                with open(os.path.join(temp_dir, "meta.json"), "r", encoding="utf-8") as f:
                    meta_data = json.load(f)

                # بررسی تطابق نام پلاگین
                if meta_data.get("name") != plugin_name:
                    return False, f"نام پلاگین در meta.json ({meta_data.get('name')}) \
                        با نام مورد انتظار ({plugin_name}) مطابقت ندارد" \

                # تعیین مسیر نهایی پلاگین
                plugin_dir = os.path.join(self.plugins_dir, plugin_name)

                # اگر پلاگین از قبل وجود دارد، پشتیبان‌گیری و حذف آن
                if os.path.exists(plugin_dir):
                    backup_dir = os.path.join(self.plugins_dir, f"{plugin_name}_backup_{int(time.time())}")
                    shutil.move(plugin_dir, backup_dir)
                    logger.info(f"نسخه قبلی پلاگین به {backup_dir} منتقل شد")

                # کپی فایل‌ها به پوشه پلاگین‌ها
                shutil.copytree(temp_dir, plugin_dir)

                # ثبت پلاگین در دیتابیس
                await self._register_plugin_in_database(plugin_id, plugin_details)

                # نصب وابستگی‌ها
                requirements_file = os.path.join(plugin_dir, "requirements.txt")
                if os.path.exists(requirements_file):
                    await self._install_plugin_requirements(requirements_file)

                return True, f"پلاگین {plugin_name} با موفقیت نصب شد"

        except Exception as e:
            logger.error(f"خطا در نصب پلاگین از فایل زیپ: {str(e)}")
            return False, f"خطا در نصب پلاگین: {str(e)}"
        finally:
            # پاکسازی پوشه موقت
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    async def _register_plugin_in_database(self, plugin_id: str, plugin_details: Dict[str, Any]) \
        -> None: \
        """
        ثبت پلاگین در دیتابیس

        Args:
            plugin_id: شناسه یکتای پلاگین
            plugin_details: جزئیات پلاگین
        """
        try:
            # اطمینان از وجود جدول
            await self._ensure_marketplace_table()

            # آماده‌سازی داده‌ها
            plugin_name = plugin_details.get("name")
            version = plugin_details.get("version")
            author = plugin_details.get("author")
            description = plugin_details.get("description")
            category = plugin_details.get("category")

            # بررسی وجود رکورد قبلی
            existing_record = await self.db.fetch_one(
                "marketplace_plugins",
                "SELECT id FROM marketplace_plugins WHERE plugin_id = $1",
                (plugin_id,)
            )

            if existing_record:
                # به‌روزرسانی رکورد موجود
                await self.db.execute(
                    ["marketplace_plugins"],
                    """
                    UPDATE marketplace_plugins
                    SET version = $1, updated_at = CURRENT_TIMESTAMP, is_installed = true,
                    description = $2, category = $3
                    WHERE plugin_id = $4
                    """,
                    (version, description, category, plugin_id)
                )
                logger.debug(f"اطلاعات پلاگین {plugin_name} در دیتابیس به‌روزرسانی شد")
            else:
                # درج رکورد جدید
                await self.db.execute(
                    ["marketplace_plugins"],
                    """
                    INSERT INTO marketplace_plugins
                    (plugin_id, plugin_name, version, author, description, category, is_installed)
                    VALUES ($1, $2, $3, $4, $5, $6, true)
                    """,
                    (plugin_id, plugin_name, version, author, description, category)
                )
                logger.debug(f"پلاگین {plugin_name} در دیتابیس ثبت شد")

        except Exception as e:
            logger.error(f"خطا در ثبت پلاگین در دیتابیس: {str(e)}")
            raise

    async def _install_plugin_requirements(self, requirements_file: str) -> None:
        """
        نصب وابستگی‌های پلاگین

        Args:
            requirements_file: مسیر فایل requirements.txt
        """
        try:
            import subprocess
            import sys

            logger.info(f"نصب وابستگی‌های پلاگین از {requirements_file}")

            # اجرای pip برای نصب وابستگی‌ها
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", "-r", requirements_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"خطا در نصب وابستگی‌ها: {stderr.decode()}")
            else:
                logger.info("وابستگی‌های پلاگین با موفقیت نصب شدند")

        except Exception as e:
            logger.error(f"خطا در نصب وابستگی‌های پلاگین: {str(e)}")

    async def get_installed_plugins(self) -> List[Dict[str, Any]]:
        """
        دریافت لیست پلاگین‌های نصب شده از بازارچه

        Returns:
            لیست پلاگین‌های نصب شده
        """
        try:
            # اطمینان از وجود جدول
            await self._ensure_marketplace_table()

            # دریافت پلاگین‌های نصب شده
            records = await self.db.fetch_all(
                "marketplace_plugins",
                "SELECT * FROM marketplace_plugins WHERE is_installed = true ORDER BY updated_at DESC"
            )

            return [dict(record) for record in records] if records else []

        except Exception as e:
            logger.error(f"خطا در دریافت پلاگین‌های نصب شده: {str(e)}")
            return []

    async def uninstall_plugin(self, plugin_id: str) -> Tuple[bool, str]:
        """
        حذف یک پلاگین نصب شده

        Args:
            plugin_id: شناسه یکتای پلاگین

        Returns:
            یک tuple شامل وضعیت عملیات (bool) و پیام نتیجه (str)
        """
        try:
            # دریافت اطلاعات پلاگین
            plugin_record = await self.db.fetch_one(
                "marketplace_plugins",
                "SELECT * FROM marketplace_plugins WHERE plugin_id = $1",
                (plugin_id,)
            )

            if not plugin_record:
                return False, f"پلاگین با شناسه {plugin_id} یافت نشد"

            plugin_name = plugin_record.get("plugin_name")

            # مسیر پوشه پلاگین
            plugin_dir = os.path.join(self.plugins_dir, plugin_name)

            # حذف پوشه پلاگین
            if os.path.exists(plugin_dir):
                shutil.rmtree(plugin_dir)

            # به‌روزرسانی وضعیت در دیتابیس
            await self.db.execute(
                ["marketplace_plugins"],
                "UPDATE marketplace_plugins SET is_installed = false, updated_at = CURRENT_TIMESTAMP WHERE plugin_id = $1",
                (plugin_id,)
            )

            return True, f"پلاگین {plugin_name} با موفقیت حذف شد"

        except Exception as e:
            logger.error(f"خطا در حذف پلاگین: {str(e)}")
            return False, f"خطا در حذف پلاگین: {str(e)}"

    async def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        بررسی وجود به‌روزرسانی برای پلاگین‌های نصب شده

        Returns:
            لیست پلاگین‌هایی که به‌روزرسانی برای آنها موجود است
        """
        try:
            # دریافت پلاگین‌های نصب شده
            installed_plugins = await self.get_installed_plugins()

            if not installed_plugins:
                return []

            # دریافت پلاگین‌های موجود در بازارچه
            marketplace_plugins = await self.get_available_plugins(refresh=True)

            # ایجاد دیکشنری برای جستجوی سریع
            marketplace_dict = {p["plugin_id"]: p for p in marketplace_plugins}

            # بررسی به‌روزرسانی
            updates_available = []

            for plugin in installed_plugins:
                plugin_id = plugin.get("plugin_id")

                if plugin_id in marketplace_dict:
                    # مقایسه نسخه‌ها
                    installed_version = plugin.get("version")
                    latest_version = marketplace_dict[plugin_id].get("version")

                    if installed_version != latest_version:
                        updates_available.append({
                            "plugin_id": plugin_id,
                            "plugin_name": plugin.get("plugin_name"),
                            "installed_version": installed_version,
                            "latest_version": latest_version,
                            "update_info": marketplace_dict[plugin_id].get("update_info", "")
                        })

            return updates_available

        except Exception as e:
            logger.error(f"خطا در بررسی به‌روزرسانی‌ها: {str(e)}")
            return []

    async def update_plugin(self, plugin_id: str) -> Tuple[bool, str]:
        """
        به‌روزرسانی یک پلاگین

        Args:
            plugin_id: شناسه یکتای پلاگین

        Returns:
            یک tuple شامل وضعیت عملیات (bool) و پیام نتیجه (str)
        """
        # استفاده از متد دانلود و نصب برای به‌روزرسانی
        return await self.download_and_install_plugin(plugin_id)

    async def get_plugin_categories(self) -> List[str]:
        """
        دریافت لیست دسته‌بندی‌های پلاگین‌ها

        Returns:
            لیست دسته‌بندی‌ها
        """
        try:
            # دریافت پلاگین‌های بازارچه
            plugins = await self.get_available_plugins()

            # استخراج دسته‌بندی‌های منحصر به فرد
            categories = set()
            for plugin in plugins:
                category = plugin.get("category")
                if category:
                    categories.add(category)

            return sorted(list(categories))

        except Exception as e:
            logger.error(f"خطا در دریافت دسته‌بندی‌های پلاگین: {str(e)}")
            return []

    async def get_featured_plugins(self) -> List[Dict[str, Any]]:
        """
        دریافت پلاگین‌های ویژه

        Returns:
            لیست پلاگین‌های ویژه
        """
        try:
            # دریافت تمام پلاگین‌ها
            all_plugins = await self.get_available_plugins()

            # فیلتر کردن پلاگین‌های ویژه
            featured_plugins = [p for p in all_plugins if p.get("is_featured", False)]

            return featured_plugins

        except Exception as e:
            logger.error(f"خطا در دریافت پلاگین‌های ویژه: {str(e)}")
            return []

    async def submit_plugin_rating(self, plugin_id: str, rating: int, review: Optional[str] = None) \
        \ \
        \ \
        -> Tuple[bool, str]: \
        """
        ثبت امتیاز و نظر برای یک پلاگین

        Args:
            plugin_id: شناسه یکتای پلاگین
            rating: امتیاز (1-5)
            review: نظر کاربر (اختیاری)

        Returns:
            یک tuple شامل وضعیت عملیات (bool) و پیام نتیجه (str)
        """
        try:
            # بررسی اعتبار لایسنس
            is_valid, _ = await self.license_manager.verify_license()
            if not is_valid:
                return False, "لایسنس معتبر نیست، دسترسی به بازارچه محدود شده است"

            # اعتبارسنجی امتیاز
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return False, "امتیاز باید عددی بین 1 تا 5 باشد"

            # تهیه داده‌های لازم برای درخواست
            request_data = {
                "license_key": self.license_manager.license_data.get("license_key"),
                "device_id": self.license_manager.license_data.get("device_id"),
                "plugin_id": plugin_id,
                "rating": rating,
                "review": review,
                "timestamp": int(time.time())
            }

            # امضای درخواست
            request_string = json.dumps(request_data, sort_keys=True)
            request_signature = hmac.new(
                self.app_signature.encode(),
                request_string.encode(),
                hashlib.sha256
            ).hexdigest()

            request_data["signature"] = request_signature

            # ارسال درخواست به سرور
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.marketplace_url}/rate/{plugin_id}",
                    json=request_data,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return True, "امتیاز و نظر شما با موفقیت ثبت شد"
                    else:
                        logger.error(f"خطا در ثبت امتیاز: کد وضعیت {response.status}")
                        return False, f"خطا در ثبت امتیاز: کد وضعیت {response.status}"

        except Exception as e:
            logger.error(f"خطا در ثبت امتیاز: {str(e)}")
            return False, f"خطا در ثبت امتیاز: {str(e)}"

    async def get_plugin_reviews(self, plugin_id: str) -> List[Dict[str, Any]]:
        """
        دریافت نظرات و امتیازات یک پلاگین

        Args:
            plugin_id: شناسه یکتای پلاگین

        Returns:
            لیست نظرات و امتیازات
        """
        try:
            # بررسی اعتبار لایسنس
            is_valid, _ = await self.license_manager.verify_license()
            if not is_valid:
                logger.warning("لایسنس معتبر نیست، دسترسی به بازارچه محدود شده است")
                return []

            # تهیه داده‌های لازم برای درخواست
            request_data = {
                "license_key": self.license_manager.license_data.get("license_key"),
                "device_id": self.license_manager.license_data.get("device_id"),
                "plugin_id": plugin_id,
                "timestamp": int(time.time())
            }

            # امضای درخواست
            request_string = json.dumps(request_data, sort_keys=True)
            request_signature = hmac.new(
                self.app_signature.encode(),
                request_string.encode(),
                hashlib.sha256
            ).hexdigest()

            request_data["signature"] = request_signature

            # ارسال درخواست به سرور
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.marketplace_url}/reviews/{plugin_id}",
                    json=request_data,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("reviews", [])
                    else:
                        logger.error(f"خطا در دریافت نظرات: کد وضعیت {response.status}")
                        return []

        except Exception as e:
            logger.error(f"خطا در دریافت نظرات پلاگین: {str(e)}")
            return []
