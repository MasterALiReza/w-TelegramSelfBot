"""
تست‌های واحد برای روتر مدیریت پلاگین‌ها
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.routers.plugins import router, get_plugin, list_plugins, create_plugin, update_plugin, toggle_plugin, delete_plugin
from api.models.plugin import PluginToggleRequest, PluginCreate, PluginUpdate


@pytest.fixture
def test_client():
    """فیکسچر برای ایجاد کلاینت تست"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_current_user():
    """فیکسچر برای شبیه‌سازی کاربر جاری"""
    return {
        "username": "admin",
        "name": "ادمین سیستم",
        "role": "admin",
        "permissions": ["manage_plugins"]
    }


@pytest.fixture
def sample_plugin_data():
    """فیکسچر برای داده‌های نمونه پلاگین"""
    return {
        "id": 1,
        "name": "تست پلاگین",
        "version": "1.0.0",
        "description": "این یک پلاگین تست است",
        "author": "نویسنده تست",
        "category": "utility",
        "is_enabled": True,
        "is_system": False,
        "created_at": "2025-05-13T10:00:00",
        "updated_at": "2025-05-13T10:00:00"
    }


class TestPluginsRouter:
    """تست‌های مربوط به روتر مدیریت پلاگین‌ها"""
    
    @patch("api.routers.plugins.db_cache")
    async def test_list_plugins(self, mock_db_cache, mock_current_user):
        """تست تابع list_plugins"""
        # تنظیم mock برای دیتابیس
        sample_plugins = [
            {"id": 1, "name": "پلاگین 1", "is_enabled": True, "category": "utility"},
            {"id": 2, "name": "پلاگین 2", "is_enabled": False, "category": "security"}
        ]
        mock_db_cache.get_plugins = AsyncMock(return_value=sample_plugins)
        mock_db_cache.count_plugins = AsyncMock(return_value=len(sample_plugins))
        
        # فراخوانی تابع list_plugins
        result = await list_plugins(mock_current_user, 1, 10, None, None, None)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert result["count"] == 2
        assert result["page"] == 1
        assert result["total_pages"] == 1
        assert len(result["plugins"]) == 2
        assert result["plugins"][0]["id"] == 1
        assert result["plugins"][1]["id"] == 2
    
    @patch("api.routers.plugins.db_cache")
    async def test_get_plugin(self, mock_db_cache, mock_current_user, sample_plugin_data):
        """تست تابع get_plugin"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_plugin = AsyncMock(return_value=sample_plugin_data)
        
        # فراخوانی تابع get_plugin
        result = await get_plugin(1, mock_current_user)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert result["plugin"]["id"] == 1
        assert result["plugin"]["name"] == "تست پلاگین"
        assert result["plugin"]["is_enabled"] is True
    
    @patch("api.routers.plugins.db_cache")
    async def test_get_plugin_not_found(self, mock_db_cache, mock_current_user):
        """تست تابع get_plugin برای پلاگین غیرموجود"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_plugin = AsyncMock(return_value=None)
        
        # بررسی اینکه فراخوانی با شناسه نامعتبر باعث HTTPException می‌شود
        with pytest.raises(HTTPException) as excinfo:
            await get_plugin(999, mock_current_user)
        
        # بررسی جزئیات خطا
        assert excinfo.value.status_code == 404
        assert "پلاگین مورد نظر یافت نشد" in excinfo.value.detail
    
    @patch("api.routers.plugins.db_cache")
    async def test_create_plugin(self, mock_db_cache, mock_current_user, sample_plugin_data):
        """تست تابع create_plugin"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.create_plugin = AsyncMock(return_value=sample_plugin_data)
        
        # ایجاد داده‌های ورودی
        plugin_data = PluginCreate(
            name="تست پلاگین",
            version="1.0.0",
            description="این یک پلاگین تست است",
            author="نویسنده تست",
            category="utility",
            source_code=""
        )
        
        # فراخوانی تابع create_plugin
        result = await create_plugin(plugin_data, mock_current_user)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert result["message"] == "پلاگین با موفقیت ایجاد شد"
        assert result["plugin"]["id"] == 1
        assert result["plugin"]["name"] == "تست پلاگین"
    
    @patch("api.routers.plugins.db_cache")
    async def test_update_plugin(self, mock_db_cache, mock_current_user, sample_plugin_data):
        """تست تابع update_plugin"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_plugin = AsyncMock(return_value=sample_plugin_data)
        
        updated_data = sample_plugin_data.copy()
        updated_data["name"] = "نام به‌روزرسانی شده"
        updated_data["description"] = "توضیحات جدید"
        
        mock_db_cache.update_plugin = AsyncMock(return_value=updated_data)
        
        # ایجاد داده‌های ورودی
        plugin_data = PluginUpdate(
            name="نام به‌روزرسانی شده",
            description="توضیحات جدید"
        )
        
        # فراخوانی تابع update_plugin
        result = await update_plugin(plugin_data, 1, mock_current_user)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert result["message"] == "پلاگین با موفقیت به‌روزرسانی شد"
        assert result["plugin"]["id"] == 1
        assert result["plugin"]["name"] == "نام به‌روزرسانی شده"
        assert result["plugin"]["description"] == "توضیحات جدید"
    
    @patch("api.routers.plugins.db_cache")
    async def test_toggle_plugin(self, mock_db_cache, mock_current_user, sample_plugin_data):
        """تست تابع toggle_plugin"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_plugin = AsyncMock(return_value=sample_plugin_data)
        
        toggled_data = sample_plugin_data.copy()
        toggled_data["is_enabled"] = False
        
        mock_db_cache.update_plugin = AsyncMock(return_value=toggled_data)
        
        # ایجاد داده‌های ورودی
        toggle_data = PluginToggleRequest(is_enabled=False)
        
        # فراخوانی تابع toggle_plugin
        result = await toggle_plugin(toggle_data, 1, mock_current_user)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert "غیرفعال" in result["message"]
        assert result["plugin"]["id"] == 1
        assert result["plugin"]["is_enabled"] is False
    
    @patch("api.routers.plugins.db_cache")
    async def test_delete_plugin(self, mock_db_cache, mock_current_user, sample_plugin_data):
        """تست تابع delete_plugin"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_plugin = AsyncMock(return_value=sample_plugin_data)
        mock_db_cache.delete_plugin = AsyncMock(return_value=True)
        
        # فراخوانی تابع delete_plugin
        result = await delete_plugin(1, mock_current_user)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert "با موفقیت حذف شد" in result["message"]
    
    @patch("api.routers.plugins.db_cache")
    async def test_delete_system_plugin(self, mock_db_cache, mock_current_user):
        """تست تابع delete_plugin برای پلاگین سیستمی"""
        # تنظیم mock برای دیتابیس
        system_plugin = {
            "id": 2,
            "name": "پلاگین سیستمی",
            "is_system": True
        }
        mock_db_cache.get_plugin = AsyncMock(return_value=system_plugin)
        
        # بررسی اینکه فراخوانی با پلاگین سیستمی باعث HTTPException می‌شود
        with pytest.raises(HTTPException) as excinfo:
            await delete_plugin(2, mock_current_user)
        
        # بررسی جزئیات خطا
        assert excinfo.value.status_code == 403
        assert "پلاگین‌های سیستمی قابل حذف نیستند" in excinfo.value.detail
