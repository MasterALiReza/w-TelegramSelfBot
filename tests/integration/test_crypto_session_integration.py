"""
تست‌های یکپارچه‌سازی برای رمزنگاری و مدیریت جلسات
"""
import os
import json
import tempfile
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from core.crypto import CryptoManager
from core.redis_manager import RedisManager
from core.database_cache import DatabaseCache


@pytest.fixture
def temp_session_dir():
    """فیکسچر برای ایجاد دایرکتوری موقت برای فایل‌های جلسه"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # پاکسازی دایرکتوری موقت بعد از تست
    import shutil
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_encrypt_decrypt_session_data(crypto_manager, temp_session_dir):
    """تست یکپارچه رمزنگاری و رمزگشایی داده‌های جلسه"""
    # تنظیم مسیر فایل جلسه
    session_path = os.path.join(temp_session_dir, "test_session.session")
    
    # داده‌های حساس جلسه
    session_data = {
        "api_id": 123456,
        "api_hash": "abcdef1234567890abcdef",
        "phone": "+98123456789",
        "auth_key": "supersecretauthkey123456789",
        "dc_id": 2,
        "server_address": "149.154.167.91",
        "port": 443
    }
    
    # رمزگذاری داده‌ها
    encrypted_data = crypto_manager.encrypt(session_data)
    
    # ذخیره در فایل
    with open(session_path, 'w') as f:
        f.write(encrypted_data)
    
    # خواندن از فایل
    with open(session_path, 'r') as f:
        read_encrypted_data = f.read()
    
    # رمزگشایی داده‌ها
    decrypted_data = crypto_manager.decrypt(read_encrypted_data)
    
    # بررسی صحت داده‌های رمزگشایی شده
    assert decrypted_data == session_data
    assert decrypted_data["api_id"] == 123456
    assert decrypted_data["api_hash"] == "abcdef1234567890abcdef"
    assert decrypted_data["auth_key"] == "supersecretauthkey123456789"


@pytest.mark.asyncio
async def test_password_hashing_and_verification(crypto_manager):
    """تست یکپارچه هش‌سازی و تأیید رمز عبور"""
    # رمز عبور اصلی
    password = "StrongPassword123!"
    
    # هش‌سازی رمز عبور
    hashed_password = crypto_manager.hash_password(password)
    
    # بررسی هش تولید شده
    assert hashed_password != password
    assert hashed_password.startswith("pbkdf2:")
    
    # تأیید رمز عبور با هش
    assert crypto_manager.verify_password(password, hashed_password) is True
    
    # تأیید رمز عبور نادرست
    assert crypto_manager.verify_password("WrongPassword", hashed_password) is False


@pytest.mark.asyncio
async def test_token_generation_and_verification(crypto_manager):
    """تست یکپارچه تولید و تأیید توکن امنیتی"""
    # اطلاعات توکن
    token_data = {
        "user_id": 123,
        "action": "reset_password",
        "expiry": 3600  # یک ساعت
    }
    
    # تولید توکن
    token = crypto_manager.generate_token(token_data)
    
    # بررسی ساختار توکن
    assert isinstance(token, str)
    assert len(token) > 20
    
    # تأیید توکن
    verified_data = crypto_manager.verify_token(token)
    
    # بررسی داده‌های استخراج شده
    assert verified_data["user_id"] == 123
    assert verified_data["action"] == "reset_password"


@pytest.mark.asyncio
async def test_crypto_redis_integration(crypto_manager, mock_redis):
    """تست یکپارچه رمزنگاری با ذخیره‌سازی در Redis"""
    # تنظیم داده‌ها
    key = "sensitive_data:user:123"
    sensitive_data = {
        "api_id": 123456,
        "api_hash": "abcdef1234567890abcdef",
        "auth_key": "supersecretauthkey123456789"
    }
    
    # رمزگذاری داده‌ها
    encrypted_data = crypto_manager.encrypt(sensitive_data)
    
    # ذخیره در Redis
    await mock_redis.set(key, encrypted_data)
    
    # بررسی فراخوانی Redis
    mock_redis.set.assert_called_once_with(key, encrypted_data)
    
    # تنظیم داده بازگشتی از Redis
    mock_redis.get.return_value = encrypted_data
    
    # بازیابی از Redis
    retrieved_data = await mock_redis.get(key)
    
    # رمزگشایی داده‌ها
    decrypted_data = crypto_manager.decrypt(retrieved_data)
    
    # بررسی صحت داده‌های رمزگشایی شده
    assert decrypted_data == sensitive_data
    assert decrypted_data["api_id"] == 123456
    assert decrypted_data["api_hash"] == "abcdef1234567890abcdef"


@pytest.mark.asyncio
async def test_database_crypto_integration(crypto_manager, mock_db, db_cache):
    """تست یکپارچه رمزنگاری با ذخیره‌سازی در دیتابیس"""
    # تنظیم داده‌ها
    user_id = 123
    sensitive_data = {
        "api_id": 123456,
        "api_hash": "abcdef1234567890abcdef",
        "auth_key": "supersecretauthkey123456789"
    }
    
    # رمزگذاری داده‌ها
    encrypted_data = crypto_manager.encrypt(sensitive_data)
    
    # تنظیم پاسخ‌های mock
    mock_db.fetch_one.return_value = {"id": user_id, "encrypted_data": encrypted_data}
    
    # ذخیره در دیتابیس
    query = "UPDATE users SET encrypted_data = %s WHERE id = %s"
    await mock_db.execute(query, (encrypted_data, user_id))
    
    # بررسی فراخوانی دیتابیس
    mock_db.execute.assert_called_once_with(query, (encrypted_data, user_id))
    
    # بازیابی از دیتابیس
    query = "SELECT encrypted_data FROM users WHERE id = %s"
    db_result = await mock_db.fetch_one(query, (user_id,))
    
    # رمزگشایی داده‌ها
    decrypted_data = crypto_manager.decrypt(db_result["encrypted_data"])
    
    # بررسی صحت داده‌های رمزگشایی شده
    assert decrypted_data == sensitive_data
    assert decrypted_data["api_id"] == 123456
    assert decrypted_data["api_hash"] == "abcdef1234567890abcdef"
