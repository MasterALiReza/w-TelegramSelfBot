"""
تنظیمات و فیکسچرهای مشترک برای تست‌های پروژه سلف بات تلگرام
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch

# اضافه کردن مسیر ریشه پروژه به sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_redis():
    """فیکسچر برای شبیه‌سازی اتصال به Redis"""
    with patch('redis.Redis') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_supabase():
    """فیکسچر برای شبیه‌سازی اتصال به Supabase"""
    with patch('supabase.create_client') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_telegram_client():
    """فیکسچر برای شبیه‌سازی کلاینت تلگرام"""
    with patch('telethon.TelegramClient') as mock:
        mock_client = Mock()
        # تنظیم رفتار پیش‌فرض برای متدهای کلاینت
        mock_client.is_connected.return_value = True
        mock_client.start.return_value = True
        mock_client.disconnect.return_value = None
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def env_setup():
    """فیکسچر برای تنظیم متغیرهای محیطی مورد نیاز برای تست"""
    original_env = os.environ.copy()
    
    # متغیرهای محیطی تست
    test_env = {
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key',
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'REDIS_DB': '0',
        'REDIS_PASSWORD': '',
        'TELEGRAM_API_ID': '12345',
        'TELEGRAM_API_HASH': 'test_hash',
        'SECRET_KEY': 'test_secret_key'
    }
    
    # تنظیم متغیرهای محیطی برای تست
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield
    
    # بازگرداندن متغیرهای محیطی به حالت اصلی
    os.environ.clear()
    os.environ.update(original_env)
