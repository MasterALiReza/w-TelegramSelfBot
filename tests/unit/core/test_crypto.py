"""
تست‌های واحد برای ماژول crypto.py
"""
import os
import json
import base64
import pytest
from unittest.mock import patch, mock_open

from core.crypto import CryptoManager


class TestCryptoManager:
    """تست‌های مربوط به کلاس CryptoManager"""

    @pytest.fixture
    def crypto_manager(self):
        """فیکسچر برای ایجاد نمونه CryptoManager"""
        # پاک کردن نمونه قبلی برای اطمینان از تست مستقل
        CryptoManager._instance = None
        with patch.dict(os.environ, {'SECRET_KEY': 'test_secret_key'}):
            return CryptoManager()

    def test_singleton_pattern(self, crypto_manager):
        """تست الگوی Singleton در CryptoManager"""
        manager1 = crypto_manager
        manager2 = CryptoManager()
        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    def test_encrypt_decrypt_string(self, crypto_manager):
        """تست رمزنگاری و رمزگشایی رشته"""
        original_data = "این یک متن تست است"
        encrypted = crypto_manager.encrypt(original_data)
        
        # اطمینان از این که داده رمزنگاری شده با داده اصلی متفاوت است
        assert encrypted != original_data
        
        # رمزگشایی و مقایسه با داده اصلی
        decrypted = crypto_manager.decrypt(encrypted)
        assert decrypted == original_data

    def test_encrypt_decrypt_dict(self, crypto_manager):
        """تست رمزنگاری و رمزگشایی دیکشنری"""
        original_data = {
            "username": "test_user",
            "api_id": 12345,
            "settings": {"theme": "dark", "notifications": True}
        }
        encrypted = crypto_manager.encrypt(original_data)
        
        # اطمینان از این که داده رمزنگاری شده با داده اصلی متفاوت است
        assert encrypted != original_data
        assert isinstance(encrypted, str)
        
        # رمزگشایی و مقایسه با داده اصلی
        decrypted = crypto_manager.decrypt(encrypted)
        assert decrypted == original_data

    def test_decrypt_invalid_data(self, crypto_manager):
        """تست رمزگشایی داده نامعتبر"""
        invalid_data = "این داده رمزنگاری شده نیست"
        result = crypto_manager.decrypt(invalid_data)
        assert result is None

    def test_hash_password(self, crypto_manager):
        """تست هش کردن رمز عبور"""
        password = "رمز_عبور_پیچیده123!"
        hashed = crypto_manager.hash_password(password)
        
        # هش باید یک رشته باشد و با رمز اصلی متفاوت باشد
        assert isinstance(hashed, str)
        assert hashed != password
        
        # تست تأیید رمز عبور
        assert crypto_manager.verify_password(password, hashed)
        assert not crypto_manager.verify_password("رمز_اشتباه", hashed)

    def test_generate_token(self, crypto_manager):
        """تست تولید توکن"""
        token1 = crypto_manager.generate_token(32)
        token2 = crypto_manager.generate_token(32)
        
        # توکن‌ها باید رشته باشند با طول مشخص
        assert isinstance(token1, str)
        assert len(token1) == 64  # هر بایت به 2 کاراکتر hex تبدیل می‌شود
        
        # دو توکن تولید شده باید متفاوت باشند
        assert token1 != token2

    def test_api_key_generation(self, crypto_manager):
        """تست تولید کلید API"""
        api_key = crypto_manager.generate_api_key()
        
        # کلید API باید یک رشته با طول مناسب باشد
        assert isinstance(api_key, str)
        assert len(api_key) > 32
        
        # اطمینان از اینکه فرمت base64 معتبر است
        try:
            base64.b64decode(api_key)
        except Exception:
            pytest.fail("API key is not a valid base64 string")

    def test_encrypt_decrypt_config(self, crypto_manager):
        """تست رمزنگاری و رمزگشایی فایل تنظیمات"""
        config = {
            "api_id": 12345,
            "api_hash": "abcdef1234567890",
            "phone": "+989123456789",
            "session_name": "test_session",
            "plugins": ["plugin1", "plugin2"]
        }
        
        encrypted = crypto_manager.encrypt_config(config)
        assert isinstance(encrypted, str)
        
        decrypted = crypto_manager.decrypt_config(encrypted)
        assert decrypted == config

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    @patch('dotenv.load_dotenv')
    def test_update_env_file(self, mock_load_dotenv, mock_exists, mock_file, crypto_manager):
        """تست به‌روزرسانی فایل .env"""
        mock_exists.return_value = True
        
        # محتوای فرضی فایل .env
        mock_file.return_value.read.return_value = "SECRET_KEY=old_key\nAPI_KEY=old_api_key"
        
        # فراخوانی متد به‌روزرسانی
        crypto_manager._update_env_file("SECRET_KEY", "new_secret_key")
        
        # بررسی فراخوانی متد write با محتوای صحیح
        expected_content = "SECRET_KEY=new_secret_key\nAPI_KEY=old_api_key"
        mock_file.return_value.write.assert_called_once_with(expected_content)
