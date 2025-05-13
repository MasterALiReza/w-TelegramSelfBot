"""
تست‌های End-to-End برای رمزنگاری و دیتابیس
"""
import os
import json
import pytest
import asyncio
import tempfile

from core.crypto import CryptoManager
from core.database_cache import DatabaseCache


@pytest.mark.e2e
@pytest.mark.crypto
def test_crypto_key_management(test_env):
    """تست مدیریت کلید رمزنگاری"""
    # ایجاد نمونه CryptoManager
    crypto = CryptoManager()
    
    # تنظیم کلید رمزنگاری
    crypto.set_key(os.environ["CRYPTO_KEY"])
    
    # بررسی تنظیم کلید
    assert crypto.key is not None
    assert len(crypto.key) > 0


@pytest.mark.e2e
@pytest.mark.crypto
def test_data_encryption_decryption(crypto_manager):
    """تست رمزنگاری و رمزگشایی داده‌ها"""
    # داده‌های حساس
    sensitive_data = {
        "api_id": 123456,
        "api_hash": "abcdef1234567890abcdef",
        "phone": "+98123456789",
        "auth_key": "supersecretauthkey123456789"
    }
    
    # رمزگذاری داده‌ها
    encrypted_data = crypto_manager.encrypt(sensitive_data)
    
    # بررسی داده‌های رمزگذاری شده
    assert encrypted_data != json.dumps(sensitive_data)
    assert isinstance(encrypted_data, str)
    
    # رمزگشایی داده‌ها
    decrypted_data = crypto_manager.decrypt(encrypted_data)
    
    # بررسی صحت داده‌های رمزگشایی شده
    assert decrypted_data == sensitive_data
    assert decrypted_data["api_id"] == 123456
    assert decrypted_data["api_hash"] == "abcdef1234567890abcdef"


@pytest.mark.e2e
@pytest.mark.crypto
def test_password_hashing_verification(crypto_manager):
    """تست هش‌سازی و تأیید رمز عبور"""
    # رمز عبور اصلی
    original_password = "StrongPassword123!"
    
    # هش‌سازی رمز عبور
    hashed_password = crypto_manager.hash_password(original_password)
    
    # بررسی هش تولید شده
    assert hashed_password != original_password
    assert hashed_password.startswith("pbkdf2:")
    
    # تأیید رمز عبور صحیح
    assert crypto_manager.verify_password(original_password, hashed_password) is True
    
    # تأیید رمز عبور نادرست
    assert crypto_manager.verify_password("WrongPassword", hashed_password) is False


@pytest.mark.e2e
@pytest.mark.crypto
def test_session_file_encryption(crypto_manager, temp_dir):
    """تست رمزنگاری فایل جلسه تلگرام"""
    # ایجاد مسیر فایل جلسه
    session_path = os.path.join(temp_dir, "test_session.session")
    
    # داده‌های جلسه
    session_data = {
        "api_id": 123456,
        "api_hash": "abcdef1234567890abcdef",
        "phone": "+98123456789",
        "auth_key": "supersecretauthkey123456789",
        "dc_id": 2,
        "server_address": "149.154.167.91",
        "port": 443
    }
    
    # رمزگذاری و ذخیره در فایل
    encrypted_data = crypto_manager.encrypt(session_data)
    with open(session_path, 'w') as f:
        f.write(encrypted_data)
    
    # بررسی وجود فایل
    assert os.path.exists(session_path)
    
    # خواندن از فایل و رمزگشایی
    with open(session_path, 'r') as f:
        file_content = f.read()
    
    decrypted_data = crypto_manager.decrypt(file_content)
    
    # بررسی صحت داده‌ها
    assert decrypted_data == session_data
    assert decrypted_data["api_id"] == 123456
    assert decrypted_data["auth_key"] == "supersecretauthkey123456789"


@pytest.mark.e2e
@pytest.mark.database
@pytest.mark.asyncio
async def test_database_connection(database_connection):
    """تست اتصال به دیتابیس"""
    # بررسی اتصال موفق
    is_connected = await database_connection.is_connected()
    
    # اگر دیتابیس در دسترس نباشد، تست را رد می‌کنیم
    if not is_connected:
        pytest.skip("دیتابیس در دسترس نیست")
    
    assert is_connected is True


@pytest.mark.e2e
@pytest.mark.database
@pytest.mark.asyncio
async def test_database_basic_crud(database_connection):
    """تست عملیات پایه دیتابیس (CRUD)"""
    # بررسی اتصال
    is_connected = await database_connection.is_connected()
    if not is_connected:
        pytest.skip("دیتابیس در دسترس نیست")
    
    # نام جدول تست
    test_table = "test_e2e_table"
    
    try:
        # ایجاد جدول تست
        create_query = f"""
        CREATE TABLE IF NOT EXISTS {test_table} (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            value INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        await database_connection.execute(create_query)
        
        # درج داده
        insert_data = {
            "name": "test_item",
            "value": 42
        }
        
        inserted = await database_connection.insert(test_table, insert_data)
        assert inserted is not None
        assert "id" in inserted
        
        # خواندن داده
        read_query = f"SELECT * FROM {test_table} WHERE name = %s"
        result = await database_connection.fetch_one(read_query, ("test_item",))
        
        assert result is not None
        assert result["name"] == "test_item"
        assert result["value"] == 42
        
        # به‌روزرسانی داده
        update_result = await database_connection.update(
            test_table,
            {"value": 99},
            "id = %s",
            (result["id"],)
        )
        
        assert update_result > 0
        
        # بررسی به‌روزرسانی
        updated = await database_connection.fetch_one(
            f"SELECT * FROM {test_table} WHERE id = %s",
            (result["id"],)
        )
        
        assert updated["value"] == 99
        
        # حذف داده
        delete_result = await database_connection.delete(
            test_table,
            "id = %s",
            (result["id"],)
        )
        
        assert delete_result > 0
        
        # بررسی حذف
        deleted_check = await database_connection.fetch_one(
            f"SELECT * FROM {test_table} WHERE id = %s",
            (result["id"],)
        )
        
        assert deleted_check is None
        
    finally:
        # پاکسازی - حذف جدول تست
        await database_connection.execute(f"DROP TABLE IF EXISTS {test_table}")


@pytest.mark.e2e
@pytest.mark.database
@pytest.mark.redis
@pytest.mark.asyncio
async def test_database_cache_integration(redis_connection, database_connection, db_cache):
    """تست یکپارچه‌سازی کش دیتابیس"""
    # بررسی اتصال‌ها
    db_connected = await database_connection.is_connected()
    redis_connected = await redis_connection.is_connected()
    
    if not (db_connected and redis_connected):
        pytest.skip("دیتابیس یا Redis در دسترس نیست")
    
    # نام جدول تست
    test_table = "test_cache_table"
    
    try:
        # ایجاد جدول تست
        create_query = f"""
        CREATE TABLE IF NOT EXISTS {test_table} (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            value INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        await database_connection.execute(create_query)
        
        # درج داده‌های نمونه
        for i in range(1, 6):
            await database_connection.insert(test_table, {
                "name": f"item_{i}",
                "value": i * 10
            })
        
        # تست fetch_one با کش
        query = f"SELECT * FROM {test_table} WHERE id = %s"
        
        # اولین فراخوانی - کش miss
        result1 = await db_cache.fetch_one(test_table, query, (1,))
        assert result1 is not None
        assert result1["name"] == "item_1"
        
        # دومین فراخوانی - باید از کش بخواند
        result2 = await db_cache.fetch_one(test_table, query, (1,))
        assert result2 is not None
        assert result2["name"] == "item_1"
        assert result2 == result1  # باید داده‌های یکسان باشند
        
        # تست fetch_all با کش
        list_query = f"SELECT * FROM {test_table} ORDER BY id"
        
        # اولین فراخوانی - کش miss
        list_result1 = await db_cache.fetch_all(test_table, list_query)
        assert len(list_result1) == 5
        
        # دومین فراخوانی - باید از کش بخواند
        list_result2 = await db_cache.fetch_all(test_table, list_query)
        assert len(list_result2) == 5
        assert list_result2 == list_result1  # باید داده‌های یکسان باشند
        
        # تست نامعتبرسازی کش با execute
        update_query = f"UPDATE {test_table} SET value = 999 WHERE id = %s"
        await db_cache.execute([test_table], update_query, (1,))
        
        # بررسی اینکه داده از کش نیاید
        result3 = await db_cache.fetch_one(test_table, query, (1,))
        assert result3 is not None
        assert result3["value"] == 999  # باید مقدار جدید را بخواند
        assert result3 != result1  # نباید داده‌های کش شده قبلی باشد
        
    finally:
        # پاکسازی - حذف جدول تست
        await database_connection.execute(f"DROP TABLE IF EXISTS {test_table}")
        
        # پاکسازی کش Redis
        cache_keys = await redis_connection.keys(f"db:{test_table}:*")
        if cache_keys:
            await redis_connection.delete(*cache_keys)
