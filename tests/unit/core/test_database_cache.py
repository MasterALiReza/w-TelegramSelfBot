"""
تست‌های واحد برای ماژول database_cache
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from core.database_cache import DatabaseCache
from core.database import Database
from core.redis_manager import RedisManager


@pytest.fixture
def mock_database():
    """فیکسچر برای شبیه‌سازی دیتابیس"""
    db = MagicMock(spec=Database)
    db.query = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_redis():
    """فیکسچر برای شبیه‌سازی ردیس"""
    redis = MagicMock(spec=RedisManager)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.hset = AsyncMock()
    redis.hgetall = AsyncMock(return_value={})
    redis.exists = AsyncMock(return_value=False)
    return redis


@pytest.fixture
def database_cache(mock_database, mock_redis):
    """فیکسچر برای ایجاد نمونه DatabaseCache"""
    return DatabaseCache(mock_database, mock_redis, default_ttl=300)


class TestDatabaseCache:
    """تست‌های مربوط به کلاس DatabaseCache"""
    
    def test_get_cache_key(self, database_cache):
        """تست تابع _get_cache_key"""
        # تست ساخت کلید کش با پارامترهای مختلف
        key1 = database_cache._get_cache_key("select", "users", "abcdef")
        key2 = database_cache._get_cache_key("count", "plugins", "123456")
        
        # بررسی صحت کلیدهای ساخته شده
        assert key1 == "db:users:select:abcdef"
        assert key2 == "db:plugins:count:123456"
        
        # بررسی یکتا بودن کلیدها با پارامترهای متفاوت
        assert key1 != key2
    
    def test_get_tag_key(self, database_cache):
        """تست تابع _get_tag_key"""
        # تست ساخت کلید تگ برای جداول مختلف
        tag1 = database_cache._get_tag_key("users")
        tag2 = database_cache._get_tag_key("plugins")
        
        # بررسی صحت تگ‌های ساخته شده
        assert tag1 == "tag:users"
        assert tag2 == "tag:plugins"
        
        # بررسی یکتا بودن تگ‌ها با پارامترهای متفاوت
        assert tag1 != tag2
    
    @pytest.mark.asyncio
    async def test_add_to_tag(self, database_cache, mock_redis):
        """تست تابع _add_to_tag"""
        # تنظیم پارامترها
        table = "users"
        cache_key = "db:users:select:abcdef"
        
        # فراخوانی متد
        await database_cache._add_to_tag(table, cache_key)
        
        # بررسی اضافه شدن به نگاشت داخلی
        tag_key = database_cache._get_tag_key(table)
        assert tag_key in database_cache._cache_tags
        assert cache_key in database_cache._cache_tags[tag_key]
        
        # بررسی فراخوانی redis
        mock_redis.hset.assert_called_once_with(tag_key, cache_key, "1")
    
    @pytest.mark.asyncio
    async def test_invalidate_tag(self, database_cache, mock_redis):
        """تست تابع _invalidate_tag"""
        # تنظیم داده‌های نگاشت داخلی
        table = "users"
        tag_key = database_cache._get_tag_key(table)
        cache_key1 = "db:users:select:abcdef"
        cache_key2 = "db:users:count:123456"
        
        database_cache._cache_tags[tag_key] = {cache_key1, cache_key2}
        
        # تنظیم مقدار برگشتی از redis
        mock_redis.hgetall.return_value = {
            cache_key1: "1",
            cache_key2: "1",
            "db:users:select:xyz": "1"
        }
        
        # فراخوانی متد
        await database_cache._invalidate_tag(table)
        
        # بررسی حذف تگ از نگاشت داخلی
        assert tag_key not in database_cache._cache_tags
        
        # بررسی فراخوانی‌های redis
        mock_redis.hgetall.assert_called_once_with(tag_key)
        
        # بررسی حذف کلیدها
        assert mock_redis.delete.call_count == 4  # 3 کلید + 1 تگ
        mock_redis.delete.assert_any_call(tag_key)
        mock_redis.delete.assert_any_call(cache_key1)
        mock_redis.delete.assert_any_call(cache_key2)
        mock_redis.delete.assert_any_call("db:users:select:xyz")
    
    @pytest.mark.asyncio
    async def test_fetch_one_cache_hit(self, database_cache, mock_redis):
        """تست تابع fetch_one با کش موجود"""
        # تنظیم داده‌های تست
        table = "users"
        query = "SELECT * FROM users WHERE id = %s"
        params = (1,)
        expected_data = {"id": 1, "username": "test_user"}
        
        # تنظیم مقدار برگشتی از redis
        mock_redis.exists.return_value = True
        mock_redis.get.return_value = json.dumps(expected_data)
        
        # فراخوانی متد
        result = await database_cache.fetch_one(table, query, params)
        
        # بررسی نتیجه
        assert result == expected_data
        
        # تایید عدم فراخوانی دیتابیس
        database_cache.db.query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fetch_one_cache_miss(self, database_cache, mock_redis, mock_database):
        """تست تابع fetch_one با کش ناموجود"""
        # تنظیم داده‌های تست
        table = "users"
        query = "SELECT * FROM users WHERE id = %s"
        params = (1,)
        expected_data = {"id": 1, "username": "test_user"}
        
        # تنظیم مقدار برگشتی از redis و دیتابیس
        mock_redis.exists.return_value = False
        mock_database.query.return_value = [expected_data]
        
        # فراخوانی متد
        result = await database_cache.fetch_one(table, query, params)
        
        # بررسی نتیجه
        assert result == expected_data
        
        # تایید فراخوانی دیتابیس
        mock_database.query.assert_called_once_with(query, params)
        
        # تایید ذخیره در کش
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_all_cache_hit(self, database_cache, mock_redis):
        """تست تابع fetch_all با کش موجود"""
        # تنظیم داده‌های تست
        table = "users"
        query = "SELECT * FROM users WHERE role = %s"
        params = ("admin",)
        expected_data = [
            {"id": 1, "username": "admin1", "role": "admin"},
            {"id": 2, "username": "admin2", "role": "admin"}
        ]
        
        # تنظیم مقدار برگشتی از redis
        mock_redis.exists.return_value = True
        mock_redis.get.return_value = json.dumps(expected_data)
        
        # فراخوانی متد
        result = await database_cache.fetch_all(table, query, params)
        
        # بررسی نتیجه
        assert result == expected_data
        
        # تایید عدم فراخوانی دیتابیس
        database_cache.db.query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_fetch_all_cache_miss(self, database_cache, mock_redis, mock_database):
        """تست تابع fetch_all با کش ناموجود"""
        # تنظیم داده‌های تست
        table = "users"
        query = "SELECT * FROM users WHERE role = %s"
        params = ("admin",)
        expected_data = [
            {"id": 1, "username": "admin1", "role": "admin"},
            {"id": 2, "username": "admin2", "role": "admin"}
        ]
        
        # تنظیم مقدار برگشتی از redis و دیتابیس
        mock_redis.exists.return_value = False
        mock_database.query.return_value = expected_data
        
        # فراخوانی متد
        result = await database_cache.fetch_all(table, query, params)
        
        # بررسی نتیجه
        assert result == expected_data
        
        # تایید فراخوانی دیتابیس
        mock_database.query.assert_called_once_with(query, params)
        
        # تایید ذخیره در کش
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count_cache_hit(self, database_cache, mock_redis):
        """تست تابع count با کش موجود"""
        # تنظیم داده‌های تست
        table = "plugins"
        query = "SELECT COUNT(*) FROM plugins WHERE is_enabled = %s"
        params = (True,)
        expected_count = 5
        
        # تنظیم مقدار برگشتی از redis
        mock_redis.exists.return_value = True
        mock_redis.get.return_value = json.dumps(expected_count)
        
        # فراخوانی متد
        result = await database_cache.count(table, query, params)
        
        # بررسی نتیجه
        assert result == expected_count
        
        # تایید عدم فراخوانی دیتابیس
        database_cache.db.query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_count_cache_miss(self, database_cache, mock_redis, mock_database):
        """تست تابع count با کش ناموجود"""
        # تنظیم داده‌های تست
        table = "plugins"
        query = "SELECT COUNT(*) FROM plugins WHERE is_enabled = %s"
        params = (True,)
        expected_count = 5
        
        # تنظیم مقدار برگشتی از redis و دیتابیس
        mock_redis.exists.return_value = False
        mock_database.query.return_value = [{"count": expected_count}]
        
        # فراخوانی متد
        result = await database_cache.count(table, query, params)
        
        # بررسی نتیجه
        assert result == expected_count
        
        # تایید فراخوانی دیتابیس
        mock_database.query.assert_called_once_with(query, params)
        
        # تایید ذخیره در کش
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute(self, database_cache, mock_database):
        """تست تابع execute"""
        # تنظیم داده‌های تست
        tables = ["users", "user_settings"]
        query = "UPDATE users SET last_login = %s WHERE id = %s"
        params = ("2025-05-13", 1)
        
        # فراخوانی متد با اسپای روی _invalidate_tag
        with patch.object(database_cache, '_invalidate_tag', AsyncMock()) as mock_invalidate:
            await database_cache.execute(tables, query, params)
            
            # بررسی فراخوانی دیتابیس
            mock_database.execute.assert_called_once_with(query, params)
            
            # بررسی نامعتبرسازی کش برای هر جدول
            assert mock_invalidate.call_count == 2
            mock_invalidate.assert_any_call("users")
            mock_invalidate.assert_any_call("user_settings")
    
    @pytest.mark.asyncio
    async def test_invalidate_cache(self, database_cache):
        """تست تابع invalidate_cache"""
        # تنظیم داده‌های تست
        tables = ["users", "plugins"]
        
        # فراخوانی متد با اسپای روی _invalidate_tag
        with patch.object(database_cache, '_invalidate_tag', AsyncMock()) as mock_invalidate:
            await database_cache.invalidate_cache(tables)
            
            # بررسی نامعتبرسازی کش برای هر جدول
            assert mock_invalidate.call_count == 2
            mock_invalidate.assert_any_call("users")
            mock_invalidate.assert_any_call("plugins")
    
    @pytest.mark.asyncio
    async def test_transaction(self, database_cache, mock_database):
        """تست تابع transaction"""
        # تنظیم داده‌های تست
        tables = ["users", "user_settings"]
        queries = [
            ("INSERT INTO users (username, email) VALUES (%s, %s)", ("newuser", "new@example.com")),
            ("INSERT INTO user_settings (user_id, theme) VALUES (%s, %s)", (10, "dark"))
        ]
        
        # تنظیم مقدار برگشتی دیتابیس
        mock_database.transaction.return_value = True
        
        # فراخوانی متد با اسپای روی _invalidate_tag
        with patch.object(database_cache, '_invalidate_tag', AsyncMock()) as mock_invalidate:
            result = await database_cache.transaction(tables, queries)
            
            # بررسی نتیجه
            assert result is True
            
            # بررسی فراخوانی تراکنش
            mock_database.transaction.assert_called_once_with(queries)
            
            # بررسی نامعتبرسازی کش برای هر جدول
            assert mock_invalidate.call_count == 2
            mock_invalidate.assert_any_call("users")
            mock_invalidate.assert_any_call("user_settings")
