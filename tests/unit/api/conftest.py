"""
فیکسچرهای مشترک برای تست‌های API
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.main import app as api_app
from core.database import Database
from core.redis_manager import RedisManager
from core.database_cache import DatabaseCache


@pytest.fixture
def app():
    """فیکسچر برای برنامه FastAPI"""
    return api_app


@pytest.fixture
def test_client(app):
    """فیکسچر برای کلاینت تست API"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """فیکسچر برای شبیه‌سازی دیتابیس"""
    db = MagicMock(spec=Database)
    db.connect = AsyncMock(return_value=True)
    db.disconnect = AsyncMock(return_value=True)
    db.query = AsyncMock()
    db.execute = AsyncMock()
    db.transaction = AsyncMock()
    db.get_user = AsyncMock()
    return db


@pytest.fixture
def mock_redis():
    """فیکسچر برای شبیه‌سازی ردیس"""
    redis = MagicMock(spec=RedisManager)
    redis.connect = AsyncMock(return_value=True)
    redis.disconnect = AsyncMock(return_value=True)
    redis.get = AsyncMock()
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.exists = AsyncMock()
    return redis


@pytest.fixture
def mock_db_cache(mock_db, mock_redis):
    """فیکسچر برای شبیه‌سازی کش دیتابیس"""
    db_cache = MagicMock(spec=DatabaseCache)
    db_cache.db = mock_db
    db_cache.redis = mock_redis
    db_cache.fetch_one = AsyncMock()
    db_cache.fetch_all = AsyncMock()
    db_cache.execute = AsyncMock()
    db_cache.count = AsyncMock()
    db_cache.invalidate_cache = AsyncMock()
    db_cache.get_user = AsyncMock()
    db_cache.get_users = AsyncMock()
    db_cache.count_users = AsyncMock()
    db_cache.get_user_by_username = AsyncMock()
    db_cache.get_user_by_email = AsyncMock()
    db_cache.create_user = AsyncMock()
    db_cache.update_user = AsyncMock()
    db_cache.delete_user = AsyncMock()
    db_cache.get_plugin = AsyncMock()
    db_cache.get_plugins = AsyncMock()
    db_cache.count_plugins = AsyncMock()
    db_cache.create_plugin = AsyncMock()
    db_cache.update_plugin = AsyncMock()
    db_cache.delete_plugin = AsyncMock()
    return db_cache
