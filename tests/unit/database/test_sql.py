"""
تست‌های واحد برای ماژول database/sql.py
"""
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from core.database.sql import PostgreSQLDatabase


class TestPostgreSQLDatabase:
    """تست‌های مربوط به کلاس PostgreSQLDatabase"""
    
    @pytest.fixture
    def mock_supabase(self):
        """فیکسچر برای شبیه‌سازی Supabase"""
        mock_client = MagicMock()
        
        # تنظیم مقادیر بازگشتی برای متدهای table و rpc
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        mock_rpc = MagicMock()
        mock_client.rpc.return_value = mock_rpc
        
        return mock_client
    
    @pytest.fixture
    def postgres_db(self):
        """فیکسچر برای ایجاد نمونه PostgreSQLDatabase"""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test_key"
        }):
            return PostgreSQLDatabase()
    
    @pytest.mark.asyncio
    @patch('supabase.create_client')
    async def test_connect(self, mock_create_client, postgres_db, mock_supabase):
        """تست متد connect"""
        # تنظیم شیء برگشتی برای create_client
        mock_create_client.return_value = mock_supabase
        
        # فراخوانی متد connect
        result = await postgres_db.connect()
        
        # بررسی‌ها
        assert result is True
        assert postgres_db.client is mock_supabase
        mock_create_client.assert_called_once_with(
            "https://test.supabase.co",
            "test_key"
        )
    
    @pytest.mark.asyncio
    async def test_disconnect(self, postgres_db):
        """تست متد disconnect"""
        # تنظیم وضعیت اتصال
        postgres_db.client = MagicMock()
        
        # فراخوانی متد disconnect
        result = await postgres_db.disconnect()
        
        # بررسی‌ها
        assert result is True
        assert postgres_db.client is None
    
    @pytest.mark.asyncio
    async def test_execute(self, postgres_db, mock_supabase):
        """تست متد execute"""
        # تنظیم وضعیت اتصال و پاسخ rpc
        postgres_db.client = mock_supabase
        mock_rpc_response = MagicMock()
        mock_rpc_response.execute = AsyncMock(return_value={"result": True})
        mock_supabase.rpc.return_value = mock_rpc_response
        
        # فراخوانی متد execute
        query = "SELECT * FROM test"
        params = {"param1": "value1"}
        result = await postgres_db.execute(query, params)
        
        # بررسی‌ها
        assert result is True
        mock_supabase.rpc.assert_called_once_with("execute_query", {
            "query_text": query,
            "params": params
        })
    
    @pytest.mark.asyncio
    async def test_query(self, postgres_db, mock_supabase):
        """تست متد query"""
        # تنظیم وضعیت اتصال و پاسخ rpc
        postgres_db.client = mock_supabase
        mock_rpc_response = MagicMock()
        expected_data = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
        mock_rpc_response.execute = AsyncMock(return_value={"data": expected_data})
        mock_supabase.rpc.return_value = mock_rpc_response
        
        # فراخوانی متد query
        query = "SELECT * FROM test"
        params = {"param1": "value1"}
        result = await postgres_db.query(query, params)
        
        # بررسی‌ها
        assert result == expected_data
        mock_supabase.rpc.assert_called_once_with("execute_query", {
            "query_text": query,
            "params": params
        })
    
    @pytest.mark.asyncio
    async def test_insert(self, postgres_db, mock_supabase):
        """تست متد insert"""
        # تنظیم وضعیت اتصال و پاسخ table
        postgres_db.client = mock_supabase
        mock_table_response = MagicMock()
        mock_table_response.insert = MagicMock()
        mock_table_response.insert().execute = AsyncMock(return_value=MagicMock(data=[{"id": 1}]))
        mock_supabase.table.return_value = mock_table_response
        
        # فراخوانی متد insert
        table = "test_table"
        data = {"name": "test", "value": 123}
        result = await postgres_db.insert(table, data)
        
        # بررسی‌ها
        assert result == 1
        mock_supabase.table.assert_called_once_with(table)
        mock_table_response.insert.assert_called_once_with(data)
    
    @pytest.mark.asyncio
    async def test_update(self, postgres_db, mock_supabase):
        """تست متد update"""
        # تنظیم وضعیت اتصال و پاسخ table
        postgres_db.client = mock_supabase
        mock_table_response = MagicMock()
        mock_table_response.update = MagicMock()
        mock_table_response.update().eq = MagicMock()
        mock_table_response.update().eq().execute = AsyncMock(return_value=MagicMock(data=[{}, {}]))
        mock_supabase.table.return_value = mock_table_response
        
        # فراخوانی متد update
        table = "test_table"
        data = {"name": "updated"}
        condition = {"id": 1}
        result = await postgres_db.update(table, data, condition)
        
        # بررسی‌ها
        assert result == 2
        mock_supabase.table.assert_called_once_with(table)
        mock_table_response.update.assert_called_once_with(data)
        mock_table_response.update().eq.assert_called_once_with("id", 1)
    
    @pytest.mark.asyncio
    async def test_delete(self, postgres_db, mock_supabase):
        """تست متد delete"""
        # تنظیم وضعیت اتصال و پاسخ table
        postgres_db.client = mock_supabase
        mock_table_response = MagicMock()
        mock_table_response.delete = MagicMock()
        mock_table_response.delete().eq = MagicMock()
        mock_table_response.delete().eq().execute = AsyncMock(return_value=MagicMock(data=[{}, {}, {}]))
        mock_supabase.table.return_value = mock_table_response
        
        # فراخوانی متد delete
        table = "test_table"
        condition = {"status": "inactive"}
        result = await postgres_db.delete(table, condition)
        
        # بررسی‌ها
        assert result == 3
        mock_supabase.table.assert_called_once_with(table)
        mock_table_response.delete.assert_called_once()
        mock_table_response.delete().eq.assert_called_once_with("status", "inactive")
    
    @pytest.mark.asyncio
    async def test_get(self, postgres_db, mock_supabase):
        """تست متد get"""
        # تنظیم وضعیت اتصال و پاسخ table
        postgres_db.client = mock_supabase
        mock_table_response = MagicMock()
        mock_table_response.select = MagicMock()
        mock_table_response.select().eq = MagicMock()
        
        expected_data = [{"id": 1, "name": "test", "value": 123}]
        mock_table_response.select().eq().execute = AsyncMock(return_value=MagicMock(data=expected_data))
        mock_supabase.table.return_value = mock_table_response
        
        # فراخوانی متد get
        table = "test_table"
        condition = {"id": 1}
        fields = ["id", "name"]
        result = await postgres_db.get(table, condition, fields)
        
        # بررسی‌ها
        assert result == expected_data
        mock_supabase.table.assert_called_once_with(table)
        mock_table_response.select.assert_called_once_with(",".join(fields))
        mock_table_response.select().eq.assert_called_once_with("id", 1)
