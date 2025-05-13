"""
ابزارهای رمزنگاری و امنیت داده‌ها برای حفاظت از اطلاعات حساس
"""
import os
import base64
import hashlib
import logging
import json
import secrets
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

# تنظیم سیستم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/crypto.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CryptoManager:
    """
    مدیریت رمزنگاری اطلاعات
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CryptoManager, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """
        مقداردهی اولیه
        """
        self.app_secret_key = os.getenv('APP_SECRET_KEY')
        if not self.app_secret_key:
            logger.warning("APP_SECRET_KEY یافت نشد، یک کلید جدید ایجاد می‌شود")
            self.app_secret_key = secrets.token_hex(32)

            # ذخیره در فایل .env
            self._update_env_file('APP_SECRET_KEY', self.app_secret_key)

        # مقداردهی Fernet
        self.fernet = self._create_fernet(self.app_secret_key)

    def _update_env_file(self, key: str, value: str):
        """
        بروزرسانی فایل .env

        Args:
            key: کلید
            value: مقدار
        """
        try:
            env_path = '.env'

            # خواندن فایل موجود
            lines = []
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

            # بررسی وجود کلید
            key_exists = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    key_exists = True
                    break

            # افزودن کلید اگر وجود نداشته باشد
            if not key_exists:
                lines.append(f"{key}={value}\n")

            # ذخیره فایل
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        except Exception as e:
            logger.error(f"خطا در بروزرسانی فایل .env: {str(e)}")

    def _create_fernet(self, key: str) -> Fernet:
        """
        ساخت شیء Fernet با کلید داده شده

        Args:
            key: کلید

        Returns:
            Fernet: شیء Fernet
        """
        # تولید کلید Fernet از کلید برنامه
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'selfbot_salt',  # از یک salt ثابت برای کلید برنامه استفاده می‌کنیم
            iterations=100000,
            backend=default_backend()
        )
        key_bytes = key.encode('utf-8')
        key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        return Fernet(key)

    def encrypt(self, data: Union[str, bytes, Dict[str, Any]]) -> str:
        """
        رمزنگاری داده

        Args:
            data: داده

        Returns:
            str: داده رمزنگاری شده به صورت base64
        """
        try:
            # تبدیل داده به bytes
            if isinstance(data, dict):
                data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            elif isinstance(data, str):
                data = data.encode('utf-8')

            # رمزنگاری
            encrypted = self.fernet.encrypt(data)

            # تبدیل به رشته
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"خطا در رمزنگاری داده: {str(e)}")
            return ""

    def decrypt(self, encrypted_data: str) -> Union[str, Dict[str, Any], None]:
        """
        رمزگشایی داده

        Args:
            encrypted_data: داده رمزنگاری شده

        Returns:
            Union[str, Dict[str, Any], None]: داده رمزگشایی شده یا None
        """
        try:
            # تبدیل از base64
            encrypted = base64.urlsafe_b64decode(encrypted_data)

            # رمزگشایی
            decrypted = self.fernet.decrypt(encrypted)

            # تلاش برای تبدیل به JSON
            try:
                return json.loads(decrypted)
            except:
                return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"خطا در رمزگشایی داده: {str(e)}")
            return None

    def hash_password(self, password: str) -> str:
        """
        هش کردن رمز عبور با salt

        Args:
            password: رمز عبور

        Returns:
            str: هش رمز عبور
        """
        # تولید salt تصادفی
        salt = os.urandom(32)

        # هش کردن
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )

        # ترکیب salt و هش
        return base64.b64encode(salt + hash_obj).decode('utf-8')

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """
        بررسی صحت رمز عبور

        Args:
            password: رمز عبور
            stored_hash: هش ذخیره شده

        Returns:
            bool: نتیجه بررسی
        """
        try:
            # جدا کردن salt و هش
            decoded = base64.b64decode(stored_hash)
            salt = decoded[:32]
            stored_hash_obj = decoded[32:]

            # هش کردن رمز عبور ورودی با همان salt
            hash_obj = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                100000
            )

            # مقایسه
            return hash_obj == stored_hash_obj
        except Exception as e:
            logger.error(f"خطا در بررسی رمز عبور: {str(e)}")
            return False

    def generate_token(self, length: int = 32) -> str:
        """
        تولید توکن امن

        Args:
            length: طول توکن

        Returns:
            str: توکن
        """
        return secrets.token_hex(length // 2)

    def generate_api_key(self) -> str:
        """
        تولید API Key امن

        Returns:
            str: API Key
        """
        return f"sk_{secrets.token_urlsafe(32)}"

    def encrypt_config(self, config: Dict[str, Any]) -> str:
        """
        رمزنگاری فایل تنظیمات

        Args:
            config: تنظیمات

        Returns:
            str: تنظیمات رمزنگاری شده
        """
        return self.encrypt(config)

    def decrypt_config(self, encrypted_config: str) -> Optional[Dict[str, Any]]:
        """
        رمزگشایی فایل تنظیمات

        Args:
            encrypted_config: تنظیمات رمزنگاری شده

        Returns:
            Optional[Dict[str, Any]]: تنظیمات یا None
        """
        result = self.decrypt(encrypted_config)
        if isinstance(result, dict):
            return result
        return None
