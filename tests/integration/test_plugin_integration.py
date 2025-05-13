"""
تست‌های یکپارچه‌سازی برای مدیریت پلاگین‌ها
"""
import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, AsyncMock, MagicMock

from core.plugin_manager import PluginManager
from core.database_cache import DatabaseCache


@pytest.fixture
def temp_plugins_dir():
    """فیکسچر برای ایجاد دایرکتوری موقت برای پلاگین‌ها"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # پاکسازی دایرکتوری موقت
    shutil.rmtree(temp_dir)


@pytest.fixture
async def sample_plugin_data():
    """فیکسچر برای داده‌های نمونه پلاگین"""
    return {
        "id": 1,
        "name": "test_plugin",
        "version": "1.0.0",
        "description": "Test plugin for integration tests",
        "author": "Test Author",
        "category": "utility",
        "is_enabled": True,
        "is_system": False,
        "source_code": "async def start(message):\n    return 'This is a test plugin'",
        "created_at": "2025-05-13T14:30:00",
        "updated_at": "2025-05-13T14:30:00"
    }


@pytest.mark.asyncio
async def test_plugin_manager_load_plugin_from_db(mock_db, mock_redis, db_cache, plugin_manager, sample_plugin_data, temp_plugins_dir):
    """تست بارگذاری پلاگین از دیتابیس"""
    # تنظیم مسیر پلاگین‌ها
    plugin_manager.plugins_dir = temp_plugins_dir
    
    # تنظیم داده‌های مورد نیاز برای تست
    plugin_name = sample_plugin_data["name"]
    
    # تنظیم mock برای دیتابیس
    db_cache.fetch_one = AsyncMock(return_value=sample_plugin_data)
    
    # فراخوانی متد مورد آزمایش
    result = await plugin_manager.load_plugin_from_db(plugin_name)
    
    # بررسی نتیجه
    assert result is True
    
    # بررسی ایجاد فایل پلاگین
    plugin_path = os.path.join(temp_plugins_dir, f"{plugin_name}.py")
    assert os.path.exists(plugin_path)
    
    # بررسی محتوای فایل پلاگین
    with open(plugin_path, 'r') as f:
        content = f.read()
        assert "async def start(message):" in content
        assert "This is a test plugin" in content


@pytest.mark.asyncio
async def test_plugin_manager_enable_disable_plugin(mock_db, mock_redis, db_cache, plugin_manager, sample_plugin_data, temp_plugins_dir):
    """تست فعال/غیرفعال کردن پلاگین"""
    # تنظیم مسیر پلاگین‌ها
    plugin_manager.plugins_dir = temp_plugins_dir
    
    # تنظیم داده‌های مورد نیاز برای تست
    plugin_name = sample_plugin_data["name"]
    
    # ایجاد فایل پلاگین در دایرکتوری موقت
    plugin_path = os.path.join(temp_plugins_dir, f"{plugin_name}.py")
    with open(plugin_path, 'w') as f:
        f.write(sample_plugin_data["source_code"])
    
    # تنظیم mock برای دیتابیس
    db_cache.fetch_one = AsyncMock(return_value=sample_plugin_data)
    db_cache.execute = AsyncMock()
    
    # اضافه کردن پلاگین به فهرست پلاگین‌های مدیر
    plugin_manager.plugins[plugin_name] = {"enabled": True, "instance": None}
    
    # 1. تست غیرفعال کردن پلاگین
    result = await plugin_manager.disable_plugin(plugin_name)
    
    # بررسی نتیجه
    assert result is True
    assert plugin_manager.plugins[plugin_name]["enabled"] is False
    
    # بررسی فراخوانی دیتابیس برای به‌روزرسانی وضعیت
    db_cache.execute.assert_called_once()
    
    # تنظیم مجدد mock برای enable
    db_cache.execute.reset_mock()
    
    # 2. تست فعال کردن پلاگین
    result = await plugin_manager.enable_plugin(plugin_name)
    
    # بررسی نتیجه
    assert result is True
    assert plugin_manager.plugins[plugin_name]["enabled"] is True
    
    # بررسی فراخوانی دیتابیس برای به‌روزرسانی وضعیت
    db_cache.execute.assert_called_once()


@pytest.mark.asyncio
async def test_plugin_manager_discover_plugins(plugin_manager, temp_plugins_dir):
    """تست کشف پلاگین‌ها از دایرکتوری"""
    # تنظیم مسیر پلاگین‌ها
    plugin_manager.plugins_dir = temp_plugins_dir
    
    # ایجاد چند فایل پلاگین در دایرکتوری موقت
    plugins = {
        "test_plugin1": "async def start(message):\n    return 'Test Plugin 1'",
        "test_plugin2": "async def start(message):\n    return 'Test Plugin 2'",
        "not_a_plugin": "def regular_function():\n    return 'Not a plugin'"
    }
    
    for name, content in plugins.items():
        with open(os.path.join(temp_plugins_dir, f"{name}.py"), 'w') as f:
            f.write(content)
    
    # فراخوانی متد مورد آزمایش
    discovered = await plugin_manager.discover_plugins()
    
    # بررسی نتیجه کشف پلاگین‌ها
    assert "test_plugin1" in discovered
    assert "test_plugin2" in discovered
    assert "not_a_plugin" not in discovered  # فایل‌های بدون تابع start باید رد شوند


@pytest.mark.asyncio
async def test_plugin_manager_update_plugin(mock_db, mock_redis, db_cache, plugin_manager, sample_plugin_data, temp_plugins_dir):
    """تست به‌روزرسانی پلاگین"""
    # تنظیم مسیر پلاگین‌ها
    plugin_manager.plugins_dir = temp_plugins_dir
    
    # تنظیم داده‌های مورد نیاز برای تست
    plugin_name = sample_plugin_data["name"]
    
    # ایجاد فایل پلاگین اولیه در دایرکتوری موقت
    plugin_path = os.path.join(temp_plugins_dir, f"{plugin_name}.py")
    with open(plugin_path, 'w') as f:
        f.write("async def start(message):\n    return 'Old version'")
    
    # تنظیم داده‌های به‌روزرسانی
    updated_data = sample_plugin_data.copy()
    updated_data["source_code"] = "async def start(message):\n    return 'Updated version'"
    
    # تنظیم mock برای دیتابیس
    db_cache.fetch_one = AsyncMock(return_value=updated_data)
    db_cache.execute = AsyncMock()
    
    # اضافه کردن پلاگین به فهرست پلاگین‌های مدیر
    plugin_manager.plugins[plugin_name] = {"enabled": True, "instance": None}
    
    # فراخوانی متد مورد آزمایش
    result = await plugin_manager.update_plugin(plugin_name)
    
    # بررسی نتیجه
    assert result is True
    
    # بررسی محتوای فایل به‌روزرسانی شده
    with open(plugin_path, 'r') as f:
        content = f.read()
        assert "Updated version" in content
