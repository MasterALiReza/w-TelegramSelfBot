"""
تست‌های واحد برای ماژول redis_manager.py
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from core.redis_manager import RedisManager, initialize_redis


class TestRedisManager:
    """تست‌های کلاس RedisManager"""

    @pytest.fixture
    def mock_redis_client(self):
        """فیکسچر برای شبیه‌سازی کلاینت Redis"""
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_instance = AsyncMock()
            mock_redis.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def redis_manager(self, mock_redis_client):
        """فیکسچر برای ایجاد نمونه RedisManager"""
        return RedisManager(
            host='test_host',
            port=6379,
            db=0,
            password='test_password',
            prefix='test:'
        )

    @pytest.mark.asyncio
    async def test_get_set_operations(self, redis_manager, mock_redis_client):
        """تست عملیات‌های پایه get و set"""
        # تنظیم mock برای متد set
        mock_redis_client.set.return_value = AsyncMock(return_value=True)
        
        # فراخوانی متد set
        result = await redis_manager.set('test_key', 'test_value', 60)
        
        # بررسی فراخوانی صحیح متد set از redis
        mock_redis_client.set.assert_called_once_with(
            'test:test_key', 
            json.dumps('test_value'), 
            ex=60
        )
        assert result is True
        
        # تنظیم mock برای متد get
        mock_redis_client.get.return_value = AsyncMock(return_value=json.dumps('test_value'))
        
        # فراخوانی متد get
        value = await redis_manager.get('test_key')
        
        # بررسی فراخوانی صحیح متد get از redis
        mock_redis_client.get.assert_called_once_with('test:test_key')
        assert value == 'test_value'

    @pytest.mark.asyncio
    async def test_delete_operation(self, redis_manager, mock_redis_client):
        """تست عملیات حذف"""
        # تنظیم mock برای متد delete
        mock_redis_client.delete.return_value = AsyncMock(return_value=1)
        
        # فراخوانی متد delete
        result = await redis_manager.delete('test_key')
        
        # بررسی فراخوانی صحیح متد delete از redis
        mock_redis_client.delete.assert_called_once_with('test:test_key')
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_exists_operation(self, redis_manager, mock_redis_client):
        """تست عملیات exists"""
        # تنظیم mock برای متد exists
        mock_redis_client.exists.return_value = AsyncMock(return_value=1)
        
        # فراخوانی متد exists
        result = await redis_manager.exists('test_key')
        
        # بررسی فراخوانی صحیح متد exists از redis
        mock_redis_client.exists.assert_called_once_with('test:test_key')
        assert result is True
    
    @pytest.mark.asyncio
    async def test_list_operations(self, redis_manager, mock_redis_client):
        """تست عملیات‌های لیست"""
        # تنظیم mock برای متد lpush
        mock_redis_client.lpush.return_value = AsyncMock(return_value=3)
        
        # فراخوانی متد list_push
        await redis_manager.list_push('test_list', 'item1')
        
        # بررسی فراخوانی صحیح متد lpush از redis
        mock_redis_client.lpush.assert_called_once_with(
            'test:test_list', 
            json.dumps('item1')
        )
        
        # تنظیم mock برای متد lrange
        mock_redis_client.lrange.return_value = [
            json.dumps('item1'), 
            json.dumps('item2'), 
            json.dumps('item3')
        ]
        
        # فراخوانی متد list_get
        items = await redis_manager.list_get('test_list')
        
        # بررسی فراخوانی صحیح متد lrange از redis
        mock_redis_client.lrange.assert_called_once_with('test:test_list', 0, -1)
        assert items == ['item1', 'item2', 'item3']
    
    @pytest.mark.asyncio
    async def test_hash_operations(self, redis_manager, mock_redis_client):
        """تست عملیات‌های هش"""
        # تنظیم mock برای متد hset
        mock_redis_client.hset.return_value = AsyncMock(return_value=1)
        
        # فراخوانی متد hash_set
        await redis_manager.hash_set('test_hash', 'field1', 'value1')
        
        # بررسی فراخوانی صحیح متد hset از redis
        mock_redis_client.hset.assert_called_once_with(
            'test:test_hash', 
            'field1', 
            json.dumps('value1')
        )
        
        # تنظیم mock برای متد hget
        mock_redis_client.hget.return_value = json.dumps('value1')
        
        # فراخوانی متد hash_get
        value = await redis_manager.hash_get('test_hash', 'field1')
        
        # بررسی فراخوانی صحیح متد hget از redis
        mock_redis_client.hget.assert_called_once_with('test:test_hash', 'field1')
        assert value == 'value1'
        
        # تنظیم mock برای متد hgetall
        mock_redis_client.hgetall.return_value = {
            'field1': json.dumps('value1'),
            'field2': json.dumps('value2')
        }
        
        # فراخوانی متد hash_get_all
        hash_data = await redis_manager.hash_get_all('test_hash')
        
        # بررسی فراخوانی صحیح متد hgetall از redis
        mock_redis_client.hgetall.assert_called_once_with('test:test_hash')
        assert hash_data == {'field1': 'value1', 'field2': 'value2'}

    @pytest.mark.asyncio
    async def test_increment_operation(self, redis_manager, mock_redis_client):
        """تست عملیات افزایش مقدار"""
        # تنظیم mock برای متد incr
        mock_redis_client.incr.return_value = AsyncMock(return_value=6)
        
        # فراخوانی متد increment
        new_value = await redis_manager.increment('test_counter')
        
        # بررسی فراخوانی صحیح متد incr از redis
        mock_redis_client.incr.assert_called_once_with('test:test_counter')
        assert new_value == 6
    
    @pytest.mark.asyncio
    async def test_expiry_operations(self, redis_manager, mock_redis_client):
        """تست عملیات‌های مرتبط با انقضا"""
        # تنظیم mock برای متد expire
        mock_redis_client.expire.return_value = AsyncMock(return_value=True)
        
        # فراخوانی متد set_expiry
        result = await redis_manager.set_expiry('test_key', 120)
        
        # بررسی فراخوانی صحیح متد expire از redis
        mock_redis_client.expire.assert_called_once_with('test:test_key', 120)
        assert result is True
        
        # تنظیم mock برای متد ttl
        mock_redis_client.ttl.return_value = AsyncMock(return_value=118)
        
        # فراخوانی متد get_ttl
        ttl = await redis_manager.get_ttl('test_key')
        
        # بررسی فراخوانی صحیح متد ttl از redis
        mock_redis_client.ttl.assert_called_once_with('test:test_key')
        assert ttl == 118

    @pytest.mark.asyncio
    async def test_clear_all(self, redis_manager, mock_redis_client):
        """تست پاک کردن تمام کلیدها با یک پیشوند"""
        # متدهای موک برای scan و delete
        mock_redis_client.scan.return_value = (0, ['test:key1', 'test:key2', 'other:key3'])
        mock_redis_client.delete.return_value = AsyncMock(return_value=2)
        
        # فراخوانی متد clear_all
        await redis_manager.clear_all()
        
        # بررسی فراخوانی صحیح متدهای scan و delete از redis
        mock_redis_client.scan.assert_called_once()
        mock_redis_client.delete.assert_called_once_with('test:key1', 'test:key2')

    @patch('redis.asyncio.Redis')
    def test_initialize_redis(self, mock_redis_class):
        """تست تابع initialize_redis"""
        # فراخوانی تابع initialize_redis
        manager = initialize_redis(
            host='custom_host',
            port=1234,
            db=2,
            password='custom_password',
            prefix='custom:'
        )
        
        # بررسی ایجاد صحیح RedisManager
        mock_redis_class.assert_called_once_with(
            host='custom_host',
            port=1234,
            db=2,
            password='custom_password',
            decode_responses=True
        )
        
        assert isinstance(manager, RedisManager)
        assert manager.prefix == 'custom:'
