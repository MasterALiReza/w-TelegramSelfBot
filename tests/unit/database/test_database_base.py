"""
تست‌های واحد برای ماژول database/base.py
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from core.database.base import DatabaseInterface, DatabaseManager


class MockDatabase(DatabaseInterface):
    """پیاده‌سازی mock از رابط دیتابیس برای تست"""
    
    def __init__(self):
        self.connect_called = False
        self.disconnect_called = False
        self.execute_called = False
        self.fetch_one_called = False
        self.fetch_all_called = False
        self.insert_called = False
        self.update_called = False
        self.delete_called = False
        self.create_tables_called = False
    
    async def connect(self):
        self.connect_called = True
        return True
    
    async def disconnect(self):
        self.disconnect_called = True
        return True
    
    async def execute(self, query, values=None):
        self.execute_called = True
        return True
    
    async def fetch_one(self, query, values=None):
        self.fetch_one_called = True
        return {"id": 1, "name": "test"}
    
    async def fetch_all(self, query, values=None):
        self.fetch_all_called = True
        return [{"id": 1, "name": "test"}]
    
    async def insert(self, table, data):
        self.insert_called = True
        return {"id": 1, **data}
    
    async def update(self, table, data, condition, values):
        self.update_called = True
        return 1
    
    async def delete(self, table, condition, values):
        self.delete_called = True
        return 1
    
    async def create_tables(self):
        self.create_tables_called = True
        return True


class TestDatabaseInterface:
    """تست‌های مربوط به رابط DatabaseInterface"""
    
    @pytest.fixture
    def mock_db(self):
        """فیکسچر برای ایجاد نمونه mock از دیتابیس"""
        return MockDatabase()
    
    @pytest.mark.asyncio
    async def test_connect(self, mock_db):
        """تست متد connect"""
        result = await mock_db.connect()
        assert result is True
        assert mock_db.connect_called is True
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mock_db):
        """تست متد disconnect"""
        result = await mock_db.disconnect()
        assert result is True
        assert mock_db.disconnect_called is True
    
    @pytest.mark.asyncio
    async def test_execute(self, mock_db):
        """تست متد execute"""
        result = await mock_db.execute("SELECT * FROM test")
        assert result is True
        assert mock_db.execute_called is True
    
    @pytest.mark.asyncio
    async def test_fetch_one(self, mock_db):
        """تست متد fetch_one"""
        result = await mock_db.fetch_one("SELECT * FROM test WHERE id = 1")
        assert isinstance(result, dict)
        assert mock_db.fetch_one_called is True
    
    @pytest.mark.asyncio
    async def test_fetch_all(self, mock_db):
        """تست متد fetch_all"""
        result = await mock_db.fetch_all("SELECT * FROM test")
        assert isinstance(result, list)
        assert mock_db.fetch_all_called is True
    
    @pytest.mark.asyncio
    async def test_insert(self, mock_db):
        """تست متد insert"""
        result = await mock_db.insert("test", {"name": "test"})
        assert isinstance(result, dict)
        assert "id" in result
        assert result["name"] == "test"
        assert mock_db.insert_called is True
    
    @pytest.mark.asyncio
    async def test_update(self, mock_db):
        """تست متد update"""
        result = await mock_db.update("test", {"name": "updated"}, "id = %s", (1,))
        assert result == 1
        assert mock_db.update_called is True
    
    @pytest.mark.asyncio
    async def test_delete(self, mock_db):
        """تست متد delete"""
        result = await mock_db.delete("test", "id = %s", (1,))
        assert result == 1
        assert mock_db.delete_called is True
    
    @pytest.mark.asyncio
    async def test_create_tables(self, mock_db):
        """تست متد create_tables"""
        result = await mock_db.create_tables()
        assert result is True
        assert mock_db.create_tables_called is True


class TestDatabaseManager:
    """تست‌های مربوط به کلاس DatabaseManager"""
    
    def setup_method(self):
        """راه‌اندازی قبل از هر تست"""
        # پاک کردن نمونه قبلی برای اطمینان از تست مستقل
        DatabaseManager._instance = None
        DatabaseManager._db = None
    
    def test_singleton_pattern(self):
        """تست الگوی Singleton در DatabaseManager"""
        manager1 = DatabaseManager()
        manager2 = DatabaseManager()
        assert manager1 is manager2
        assert id(manager1) == id(manager2)
    
    def test_set_get_database(self):
        """تست متدهای set_database و get_database"""
        mock_db = MockDatabase()
        
        # تنظیم دیتابیس
        DatabaseManager.set_database(mock_db)
        
        # بررسی برابری شیء دیتابیس
        db = DatabaseManager.get_database()
        assert db is mock_db
        
        # بررسی مجدد با نمونه دیگر از DatabaseManager
        manager = DatabaseManager()
        assert manager.get_database() is mock_db
