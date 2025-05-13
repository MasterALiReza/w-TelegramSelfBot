"""
فیکسچرهای مشترک برای تست‌های یکپارچه‌سازی
"""
import os
import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from core.config import Config
from core.database import Database, DatabaseManager
from core.redis_manager import RedisManager
from core.database_cache import DatabaseCache
from core.plugin_manager import PluginManager
from core.crypto import CryptoManager


@pytest.fixture(scope="session")
def event_loop():
    """فیکسچر برای ایجاد حلقه رویداد asyncio با طول عمر session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """فیکسچر برای تنظیمات تست"""
    # تنظیم متغیرهای محیطی برای تست
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_PASSWORD"] = "test_password"
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_ANON_KEY"] = "test_key"
    os.environ["SECRET_KEY"] = "test_secret_key"
    os.environ["APP_ENV"] = "test"
    
    # بارگذاری تنظیمات
    config = Config()
    return config


@pytest.fixture
async def mock_redis():
    """فیکسچر برای mock ردیس"""
    redis = AsyncMock(spec=RedisManager)
    redis.connect = AsyncMock(return_value=True)
    redis.disconnect = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.exists = AsyncMock(return_value=False)
    redis.hset = AsyncMock()
    redis.hgetall = AsyncMock(return_value={})
    redis.hget = AsyncMock()
    redis.hdel = AsyncMock()
    redis.lpush = AsyncMock()
    redis.rpush = AsyncMock()
    redis.lpop = AsyncMock()
    redis.rpop = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])
    redis.is_connected = AsyncMock(return_value=True)
    
    return redis


@pytest.fixture
async def mock_db():
    """فیکسچر برای mock دیتابیس"""
    db = AsyncMock(spec=Database)
    db.connect = AsyncMock(return_value=True)
    db.disconnect = AsyncMock(return_value=True)
    db.execute = AsyncMock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock(return_value=[])
    db.insert = AsyncMock()
    db.update = AsyncMock()
    db.delete = AsyncMock()
    db.create_tables = AsyncMock(return_value=True)
    db.transaction = AsyncMock(return_value=True)
    db.is_connected = AsyncMock(return_value=True)
    
    # تنظیم DatabaseManager برای استفاده از mock
    DatabaseManager.set_database(db)
    
    return db


@pytest.fixture
async def db_cache(mock_db, mock_redis):
    """فیکسچر برای DatabaseCache"""
    cache = DatabaseCache(mock_db, mock_redis)
    return cache


@pytest.fixture
def crypto_manager():
    """فیکسچر برای CryptoManager"""
    manager = CryptoManager()
    # تنظیم کلید رمزنگاری
    manager.set_key("test_encryption_key")
    return manager


@pytest.fixture
async def plugin_manager(mock_db, mock_redis, db_cache):
    """فیکسچر برای PluginManager"""
    with patch('core.plugin_manager.DatabaseCache', return_value=db_cache):
        manager = PluginManager(mock_db, mock_redis)
        yield manager
