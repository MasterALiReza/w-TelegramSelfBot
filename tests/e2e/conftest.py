"""
فیکسچرهای مشترک برای تست‌های End-to-End
"""
import os
import pytest
import asyncio
import tempfile
import logging
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient
from fastapi import FastAPI

from core.config import Config
from core.database import Database, DatabaseManager
from core.redis_manager import RedisManager, initialize_redis
from core.database_cache import DatabaseCache
from core.crypto import CryptoManager
from core.plugin_manager import PluginManager
from api.main import app as api_app


# تنظیم لاگر برای تست‌ها
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("e2e_tests")


@pytest.fixture(scope="session")
def event_loop():
    """فیکسچر برای ایجاد حلقه رویداد asyncio با طول عمر session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_env():
    """فیکسچر برای تنظیم متغیرهای محیطی تست"""
    # ذخیره متغیرهای محیطی فعلی
    original_env = {}
    for key in os.environ:
        original_env[key] = os.environ[key]
    
    # تنظیم متغیرهای محیطی برای تست
    os.environ["APP_ENV"] = "test"
    os.environ["SECRET_KEY"] = "test_secret_key_for_e2e_tests"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_PASSWORD"] = ""  # معمولاً برای تست‌های محلی پسورد نداریم
    os.environ["SUPABASE_URL"] = "http://localhost:54321"  # آدرس محلی Supabase
    os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
    os.environ["CRYPTO_KEY"] = "test_encryption_key_for_e2e_tests"
    
    yield
    
    # بازگرداندن متغیرهای محیطی اصلی
    for key in original_env:
        os.environ[key] = original_env[key]


@pytest.fixture(scope="session")
async def redis_connection(test_env):
    """فیکسچر برای اتصال به Redis در تست‌های End-to-End"""
    redis = await initialize_redis()
    
    # پاکسازی دیتابیس Redis قبل از شروع تست‌ها
    await redis.flushdb()
    
    yield redis
    
    # پاکسازی و بستن اتصال پس از پایان تست‌ها
    await redis.flushdb()
    await redis.disconnect()


@pytest.fixture(scope="session")
async def database_connection(test_env):
    """فیکسچر برای اتصال به دیتابیس در تست‌های End-to-End"""
    # در محیط واقعی، باید به یک دیتابیس تست متصل شویم
    from core.database.sql import PostgreSQLDatabase
    
    db = PostgreSQLDatabase()
    await db.connect()
    
    # تنظیم DatabaseManager برای استفاده از این اتصال
    DatabaseManager.set_database(db)
    
    yield db
    
    # قطع اتصال پس از پایان تست‌ها
    await db.disconnect()


@pytest.fixture(scope="session")
async def db_cache(database_connection, redis_connection):
    """فیکسچر برای DatabaseCache در تست‌های End-to-End"""
    cache = DatabaseCache(database_connection, redis_connection)
    return cache


@pytest.fixture(scope="session")
def crypto_manager(test_env):
    """فیکسچر برای CryptoManager"""
    manager = CryptoManager()
    manager.set_key(os.environ["CRYPTO_KEY"])
    return manager


@pytest.fixture(scope="session")
def temp_dir():
    """فیکسچر برای ایجاد دایرکتوری موقت"""
    temp_directory = tempfile.mkdtemp()
    yield temp_directory
    # پاکسازی دایرکتوری موقت پس از پایان تست‌ها
    import shutil
    shutil.rmtree(temp_directory)


@pytest.fixture(scope="session")
def plugins_dir(temp_dir):
    """فیکسچر برای دایرکتوری پلاگین‌ها"""
    plugins_directory = os.path.join(temp_dir, "plugins")
    os.makedirs(plugins_directory, exist_ok=True)
    return plugins_directory


@pytest.fixture(scope="session")
async def plugin_manager(database_connection, redis_connection, db_cache, plugins_dir):
    """فیکسچر برای PluginManager"""
    manager = PluginManager(database_connection, redis_connection)
    # تنظیم مسیر پلاگین‌ها
    manager.plugins_dir = plugins_dir
    return manager


@pytest.fixture(scope="session")
def test_client(test_env):
    """فیکسچر برای کلاینت تست API در تست‌های End-to-End"""
    # راه‌اندازی اپلیکیشن API قبل از تست‌ها
    with TestClient(api_app) as client:
        yield client


@pytest.fixture
def auth_headers(test_env):
    """فیکسچر برای هدرهای احراز هویت"""
    # در تست‌های واقعی، باید احراز هویت انجام شود و توکن دریافت شود
    from api.main import create_access_token
    
    # ایجاد داده‌های کاربر تست
    token_data = {
        "sub": "test_admin",
        "name": "کاربر تست",
        "role": "admin",
        "permissions": ["manage_users", "manage_plugins", "view_dashboard"]
    }
    
    # ایجاد توکن
    token = create_access_token(token_data)
    
    # بازگشت هدرهای احراز هویت
    return {"Authorization": f"Bearer {token}"}
