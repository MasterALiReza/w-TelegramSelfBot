"""
تست‌های یکپارچه‌سازی برای تعامل بین ماژول‌های دیتابیس
"""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

from core.database import Database, DatabaseManager
from core.redis_manager import RedisManager
from core.database_cache import DatabaseCache


@pytest.mark.asyncio
async def test_database_cache_fetch_one_cache_miss(mock_db, mock_redis, db_cache):
    """تست fetch_one در DatabaseCache با سناریوی cache miss"""
    # تنظیم داده‌های تست
    table = "users"
    query = "SELECT * FROM users WHERE id = %s"
    params = (1,)
    expected_data = {"id": 1, "username": "test_user", "email": "test@example.com"}
    
    # تنظیم mock برای سناریوی cache miss
    mock_redis.exists.return_value = False
    mock_db.fetch_one.return_value = expected_data
    
    # فراخوانی متد مورد آزمایش
    result = await db_cache.fetch_one(table, query, params)
    
    # بررسی نتیجه
    assert result == expected_data
    
    # بررسی فراخوانی دیتابیس
    mock_db.fetch_one.assert_called_once_with(query, params)
    
    # بررسی ذخیره داده در کش
    mock_redis.set.assert_called_once()
    # بررسی افزودن به تگ
    mock_redis.hset.assert_called_once()


@pytest.mark.asyncio
async def test_database_cache_fetch_one_cache_hit(mock_db, mock_redis, db_cache):
    """تست fetch_one در DatabaseCache با سناریوی cache hit"""
    # تنظیم داده‌های تست
    table = "users"
    query = "SELECT * FROM users WHERE id = %s"
    params = (1,)
    expected_data = {"id": 1, "username": "test_user", "email": "test@example.com"}
    
    # تنظیم mock برای سناریوی cache hit
    mock_redis.exists.return_value = True
    mock_redis.get.return_value = json.dumps(expected_data)
    
    # فراخوانی متد مورد آزمایش
    result = await db_cache.fetch_one(table, query, params)
    
    # بررسی نتیجه
    assert result == expected_data
    
    # بررسی عدم فراخوانی دیتابیس
    mock_db.fetch_one.assert_not_called()


@pytest.mark.asyncio
async def test_database_cache_execute_and_invalidate(mock_db, mock_redis, db_cache):
    """تست execute و نامعتبرسازی کش در DatabaseCache"""
    # تنظیم داده‌های تست
    tables = ["users", "user_settings"]
    query = "UPDATE users SET last_login = %s WHERE id = %s"
    params = ("2025-05-13", 1)
    
    # ساخت tag keys که انتظار داریم حذف شوند
    tag_keys = [db_cache._get_tag_key(table) for table in tables]
    
    # تنظیم mock برای redis
    mock_redis.hgetall.return_value = {
        "db:users:select:abc123": "1",
        "db:users:count:def456": "1"
    }
    
    # فراخوانی متد مورد آزمایش
    await db_cache.execute(tables, query, params)
    
    # بررسی فراخوانی دیتابیس
    mock_db.execute.assert_called_once_with(query, params)
    
    # بررسی فراخوانی‌های redis برای نامعتبرسازی کش
    assert mock_redis.hgetall.call_count == 2
    assert mock_redis.delete.call_count >= 3  # حداقل 2 tag key + 2 cache key
    
    # بررسی حذف tag keys
    for tag_key in tag_keys:
        mock_redis.delete.assert_any_call(tag_key)


@pytest.mark.asyncio
async def test_database_cache_transaction(mock_db, mock_redis, db_cache):
    """تست تراکنش در DatabaseCache"""
    # تنظیم داده‌های تست
    tables = ["users", "user_settings"]
    queries = [
        ("INSERT INTO users (username, email) VALUES (%s, %s)", ("newuser", "new@example.com")),
        ("INSERT INTO user_settings (user_id, theme) VALUES (%s, %s)", (1, "dark"))
    ]
    
    # فراخوانی متد مورد آزمایش
    result = await db_cache.transaction(tables, queries)
    
    # بررسی نتیجه
    assert result is True
    
    # بررسی فراخوانی تراکنش دیتابیس
    mock_db.transaction.assert_called_once_with(queries)
    
    # بررسی نامعتبرسازی کش برای جداول مرتبط
    assert mock_redis.hgetall.call_count == 2


@pytest.mark.asyncio
async def test_database_manager_singleton(mock_db):
    """تست الگوی Singleton در DatabaseManager"""
    # دریافت نمونه‌های مختلف
    manager1 = DatabaseManager()
    manager2 = DatabaseManager()
    
    # بررسی یکسان بودن نمونه‌ها
    assert manager1 is manager2
    
    # بررسی دیتابیس تنظیم شده
    db = DatabaseManager.get_database()
    assert db is mock_db
