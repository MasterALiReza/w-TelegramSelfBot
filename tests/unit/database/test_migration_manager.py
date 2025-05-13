"""
تست‌های واحد برای ماژول migration_manager
"""
import os
import pytest
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from core.database import Database
from database.migration_manager import MigrationManager, run_migrations


@pytest.fixture
def mock_database():
    """فیکسچر برای شبیه‌سازی دیتابیس"""
    db = MagicMock(spec=Database)
    db.query = AsyncMock()
    db.execute = AsyncMock()
    db.transaction = AsyncMock()
    return db


@pytest.fixture
def temp_migration_dir():
    """فیکسچر برای ایجاد دایرکتوری موقت برای migration‌ها"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # پاکسازی دایرکتوری موقت
    shutil.rmtree(temp_dir)


@pytest.fixture
def migration_manager(mock_database, temp_migration_dir):
    """فیکسچر برای ایجاد نمونه MigrationManager"""
    manager = MigrationManager(mock_database)
    # جایگزینی مسیر migrations با دایرکتوری موقت
    manager.migrations_dir = temp_migration_dir
    return manager


class TestMigrationManager:
    """تست‌های مربوط به کلاس MigrationManager"""
    
    @pytest.mark.asyncio
    async def test_init_migration_table(self, migration_manager, mock_database):
        """تست تابع init_migration_table"""
        # فراخوانی متد
        await migration_manager.init_migration_table()
        
        # بررسی فراخوانی دیتابیس
        mock_database.execute.assert_called_once()
        # بررسی اینکه کوئری شامل CREATE TABLE باشد
        create_query = mock_database.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS" in create_query
        assert "migrations" in create_query
    
    @pytest.mark.asyncio
    async def test_get_applied_migrations_empty(self, migration_manager, mock_database):
        """تست تابع get_applied_migrations با دیتابیس خالی"""
        # تنظیم مقدار برگشتی از دیتابیس (هیچ migration اعمال نشده)
        mock_database.query.return_value = []
        
        # فراخوانی متد
        await migration_manager.get_applied_migrations()
        
        # بررسی فراخوانی دیتابیس
        mock_database.query.assert_called_once()
        query = mock_database.query.call_args[0][0]
        assert "SELECT" in query
        assert "migrations" in query
        
        # بررسی لیست migration‌های اعمال شده
        assert migration_manager.applied_migrations == []
    
    @pytest.mark.asyncio
    async def test_get_applied_migrations_with_data(self, migration_manager, mock_database):
        """تست تابع get_applied_migrations با دیتابیس دارای migration"""
        # تنظیم مقدار برگشتی از دیتابیس
        applied_migrations = [
            {"name": "001_initial_schema.sql", "applied_at": "2025-05-01T10:00:00"},
            {"name": "002_add_users_table.sql", "applied_at": "2025-05-02T11:30:00"}
        ]
        mock_database.query.return_value = applied_migrations
        
        # فراخوانی متد
        await migration_manager.get_applied_migrations()
        
        # بررسی فراخوانی دیتابیس
        mock_database.query.assert_called_once()
        
        # بررسی لیست migration‌های اعمال شده
        assert len(migration_manager.applied_migrations) == 2
        assert "001_initial_schema.sql" in migration_manager.applied_migrations
        assert "002_add_users_table.sql" in migration_manager.applied_migrations
    
    def test_get_migration_files(self, migration_manager, temp_migration_dir):
        """تست تابع get_migration_files"""
        # ایجاد چند فایل migration در دایرکتوری موقت
        migration_files = [
            "001_initial_schema.sql",
            "002_add_users_table.sql",
            "003_add_plugins_table.sql"
        ]
        
        for file_name in migration_files:
            file_path = os.path.join(temp_migration_dir, file_name)
            with open(file_path, 'w') as f:
                f.write("-- Test migration\nCREATE TABLE test (id INT);")
        
        # ایجاد یک فایل غیر-migration (باید نادیده گرفته شود)
        non_migration_file = os.path.join(temp_migration_dir, "README.md")
        with open(non_migration_file, 'w') as f:
            f.write("# Migrations\nThis directory contains database migrations.")
        
        # فراخوانی متد
        result = migration_manager.get_migration_files()
        
        # بررسی نتیجه
        assert len(result) == 3
        for file_name in migration_files:
            assert file_name in result
        
        # بررسی ترتیب فایل‌ها (باید مرتب شده باشند)
        assert result[0] == "001_initial_schema.sql"
        assert result[1] == "002_add_users_table.sql"
        assert result[2] == "003_add_plugins_table.sql"
    
    @pytest.mark.asyncio
    async def test_get_pending_migrations(self, migration_manager, temp_migration_dir):
        """تست تابع get_pending_migrations"""
        # ایجاد چند فایل migration در دایرکتوری موقت
        migration_files = [
            "001_initial_schema.sql",
            "002_add_users_table.sql",
            "003_add_plugins_table.sql"
        ]
        
        for file_name in migration_files:
            file_path = os.path.join(temp_migration_dir, file_name)
            with open(file_path, 'w') as f:
                f.write("-- Test migration\nCREATE TABLE test (id INT);")
        
        # تنظیم migration‌های اعمال شده (دو مورد اول)
        migration_manager.applied_migrations = [
            "001_initial_schema.sql",
            "002_add_users_table.sql"
        ]
        
        # فراخوانی متد
        result = await migration_manager.get_pending_migrations()
        
        # بررسی نتیجه
        assert len(result) == 1
        assert result[0] == "003_add_plugins_table.sql"
    
    @pytest.mark.asyncio
    async def test_apply_migration(self, migration_manager, mock_database, temp_migration_dir):
        """تست تابع apply_migration"""
        # ایجاد یک فایل migration در دایرکتوری موقت
        migration_name = "001_test_migration.sql"
        migration_content = """
        -- Test migration
        CREATE TABLE test_table (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL
        );
        """
        
        file_path = os.path.join(temp_migration_dir, migration_name)
        with open(file_path, 'w') as f:
            f.write(migration_content)
        
        # فراخوانی متد
        result = await migration_manager.apply_migration(migration_name)
        
        # بررسی نتیجه
        assert result is True
        
        # بررسی فراخوانی‌های دیتابیس
        # باید یک تراکنش ایجاد کرده باشد
        mock_database.transaction.assert_called_once()
        
        # بررسی ثبت migration در جدول migrations
        transaction_calls = mock_database.transaction.call_args[0][0]
        assert len(transaction_calls) == 2
        
        # بررسی محتوای تراکنش
        assert "INSERT INTO migrations" in transaction_calls[1][0]
        assert migration_name in transaction_calls[1][0]
    
    @pytest.mark.asyncio
    async def test_apply_all_migrations(self, migration_manager, temp_migration_dir):
        """تست تابع apply_all_migrations"""
        # ایجاد چند فایل migration در دایرکتوری موقت
        migration_files = [
            "001_initial_schema.sql",
            "002_add_users_table.sql",
            "003_add_plugins_table.sql"
        ]
        
        for file_name in migration_files:
            file_path = os.path.join(temp_migration_dir, file_name)
            with open(file_path, 'w') as f:
                f.write(f"-- Test migration {file_name}\nCREATE TABLE {file_name.split('_')[1]} (id INT);")
        
        # تنظیم migration‌های اعمال شده (یک مورد اول)
        migration_manager.applied_migrations = ["001_initial_schema.sql"]
        
        # اسپای روی تابع apply_migration
        with patch.object(migration_manager, 'apply_migration', AsyncMock(return_value=True)) as mock_apply:
            # فراخوانی متد
            result = await migration_manager.apply_all_migrations()
            
            # بررسی نتیجه
            assert result is True
            
            # بررسی فراخوانی apply_migration برای هر migration در انتظار
            assert mock_apply.call_count == 2
            mock_apply.assert_any_call("002_add_users_table.sql")
            mock_apply.assert_any_call("003_add_plugins_table.sql")
    
    @pytest.mark.asyncio
    async def test_run_migrations(self, mock_database):
        """تست تابع run_migrations"""
        # اسپای روی MigrationManager
        with patch('database.migration_manager.MigrationManager') as mock_manager_class:
            # تنظیم مقادیر برگشتی برای متدهای نمونه MigrationManager
            manager_instance = mock_manager_class.return_value
            manager_instance.init_migration_table = AsyncMock()
            manager_instance.get_applied_migrations = AsyncMock()
            manager_instance.apply_all_migrations = AsyncMock(return_value=True)
            
            # فراخوانی تابع
            result = await run_migrations(mock_database)
            
            # بررسی نتیجه
            assert result is True
            
            # بررسی فراخوانی‌های مورد انتظار
            mock_manager_class.assert_called_once_with(mock_database)
            manager_instance.init_migration_table.assert_called_once()
            manager_instance.get_applied_migrations.assert_called_once()
            manager_instance.apply_all_migrations.assert_called_once()
