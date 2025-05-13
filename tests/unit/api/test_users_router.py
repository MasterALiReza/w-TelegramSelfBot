"""
تست‌های واحد برای روتر مدیریت کاربران
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.routers.users import router, get_user, list_users, create_user, update_user, delete_user
from api.models.user import UserCreate, UserUpdate


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
        "permissions": ["manage_users"]
    }


@pytest.fixture
def sample_user_data():
    """فیکسچر برای داده‌های نمونه کاربر"""
    return {
        "id": 1,
        "username": "test_user",
        "email": "test@example.com",
        "name": "کاربر تست",
        "role": "user",
        "permissions": ["view_dashboard", "use_selfbot"],
        "created_at": "2025-05-13T10:00:00",
        "updated_at": "2025-05-13T10:00:00"
    }


class TestUsersRouter:
    """تست‌های مربوط به روتر مدیریت کاربران"""
    
    @patch("api.routers.users.db_cache")
    async def test_list_users(self, mock_db_cache, mock_current_user):
        """تست تابع list_users"""
        # تنظیم mock برای دیتابیس
        sample_users = [
            {"id": 1, "username": "user1", "email": "user1@example.com", "role": "admin"},
            {"id": 2, "username": "user2", "email": "user2@example.com", "role": "user"}
        ]
        mock_db_cache.get_users = AsyncMock(return_value=sample_users)
        mock_db_cache.count_users = AsyncMock(return_value=len(sample_users))
        
        # فراخوانی تابع list_users
        result = await list_users(mock_current_user, 1, 10, None)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert result["count"] == 2
        assert result["page"] == 1
        assert result["total_pages"] == 1
        assert len(result["users"]) == 2
        assert result["users"][0]["id"] == 1
        assert result["users"][1]["id"] == 2
    
    @patch("api.routers.users.db_cache")
    async def test_get_user(self, mock_db_cache, mock_current_user, sample_user_data):
        """تست تابع get_user"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_user = AsyncMock(return_value=sample_user_data)
        
        # فراخوانی تابع get_user
        result = await get_user(1, mock_current_user)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert result["user"]["id"] == 1
        assert result["user"]["username"] == "test_user"
        assert result["user"]["email"] == "test@example.com"
    
    @patch("api.routers.users.db_cache")
    async def test_get_user_not_found(self, mock_db_cache, mock_current_user):
        """تست تابع get_user برای کاربر غیرموجود"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_user = AsyncMock(return_value=None)
        
        # بررسی اینکه فراخوانی با شناسه نامعتبر باعث HTTPException می‌شود
        with pytest.raises(HTTPException) as excinfo:
            await get_user(999, mock_current_user)
        
        # بررسی جزئیات خطا
        assert excinfo.value.status_code == 404
        assert "کاربر مورد نظر یافت نشد" in excinfo.value.detail
    
    @patch("api.routers.users.db_cache")
    async def test_create_user(self, mock_db_cache, mock_current_user, sample_user_data):
        """تست تابع create_user"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_user_by_username = AsyncMock(return_value=None)
        mock_db_cache.get_user_by_email = AsyncMock(return_value=None)
        mock_db_cache.create_user = AsyncMock(return_value=sample_user_data)
        
        # ایجاد داده‌های ورودی
        user_data = UserCreate(
            username="test_user",
            email="test@example.com",
            password="StrongPassword123",
            name="کاربر تست",
            role="user",
            permissions=["view_dashboard", "use_selfbot"]
        )
        
        # فراخوانی تابع create_user
        result = await create_user(user_data, mock_current_user)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert result["message"] == "کاربر با موفقیت ایجاد شد"
        assert result["user"]["id"] == 1
        assert result["user"]["username"] == "test_user"
        assert result["user"]["email"] == "test@example.com"
    
    @patch("api.routers.users.db_cache")
    async def test_create_user_duplicate_username(self, mock_db_cache, mock_current_user):
        """تست تابع create_user با نام کاربری تکراری"""
        # تنظیم mock برای دیتابیس - کاربر با نام کاربری مشابه وجود دارد
        existing_user = {"id": 2, "username": "test_user", "email": "existing@example.com"}
        mock_db_cache.get_user_by_username = AsyncMock(return_value=existing_user)
        
        # ایجاد داده‌های ورودی
        user_data = UserCreate(
            username="test_user",
            email="new@example.com",
            password="StrongPassword123",
            name="کاربر جدید",
            role="user"
        )
        
        # بررسی اینکه فراخوانی با نام کاربری تکراری باعث HTTPException می‌شود
        with pytest.raises(HTTPException) as excinfo:
            await create_user(user_data, mock_current_user)
        
        # بررسی جزئیات خطا
        assert excinfo.value.status_code == 400
        assert "نام کاربری قبلاً استفاده شده است" in excinfo.value.detail
    
    @patch("api.routers.users.db_cache")
    async def test_update_user(self, mock_db_cache, mock_current_user, sample_user_data):
        """تست تابع update_user"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_user = AsyncMock(return_value=sample_user_data)
        mock_db_cache.get_user_by_email = AsyncMock(return_value=None)
        
        updated_data = sample_user_data.copy()
        updated_data["name"] = "نام به‌روزرسانی شده"
        updated_data["email"] = "updated@example.com"
        
        mock_db_cache.update_user = AsyncMock(return_value=updated_data)
        
        # ایجاد داده‌های ورودی
        user_data = UserUpdate(
            email="updated@example.com",
            name="نام به‌روزرسانی شده"
        )
        
        # فراخوانی تابع update_user
        result = await update_user(user_data, 1, mock_current_user)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert result["message"] == "کاربر با موفقیت به‌روزرسانی شد"
        assert result["user"]["id"] == 1
        assert result["user"]["name"] == "نام به‌روزرسانی شده"
        assert result["user"]["email"] == "updated@example.com"
    
    @patch("api.routers.users.db_cache")
    async def test_update_self_no_role_change(self, mock_db_cache):
        """تست تابع update_user برای به‌روزرسانی خود کاربر بدون تغییر نقش"""
        # تنظیم کاربر جاری (کاربر خودش را به‌روزرسانی می‌کند)
        current_user = {
            "id": 1, 
            "username": "test_user", 
            "role": "user",
            "permissions": ["manage_profile"]
        }
        
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_user = AsyncMock(return_value=current_user)
        mock_db_cache.get_user_by_email = AsyncMock(return_value=None)
        
        updated_data = current_user.copy()
        updated_data["name"] = "نام جدید"
        
        mock_db_cache.update_user = AsyncMock(return_value=updated_data)
        
        # ایجاد داده‌های ورودی (بدون تغییر نقش)
        user_data = UserUpdate(name="نام جدید")
        
        # فراخوانی تابع update_user
        result = await update_user(user_data, 1, current_user)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert result["user"]["name"] == "نام جدید"
    
    @patch("api.routers.users.db_cache")
    async def test_update_self_with_role_change(self, mock_db_cache):
        """تست تابع update_user برای تغییر نقش خود کاربر (که باید با خطا مواجه شود)"""
        # تنظیم کاربر جاری (کاربر خودش را به‌روزرسانی می‌کند)
        current_user = {
            "id": 1, 
            "username": "test_user", 
            "role": "user",
            "permissions": ["manage_profile"]
        }
        
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_user = AsyncMock(return_value=current_user)
        
        # ایجاد داده‌های ورودی (با تغییر نقش)
        user_data = UserUpdate(role="admin")
        
        # بررسی اینکه تغییر نقش خود باعث HTTPException می‌شود
        with pytest.raises(HTTPException) as excinfo:
            await update_user(user_data, 1, current_user)
        
        # بررسی جزئیات خطا
        assert excinfo.value.status_code == 403
        assert "شما نمی‌توانید نقش خود را تغییر دهید" in excinfo.value.detail
    
    @patch("api.routers.users.db_cache")
    async def test_delete_user(self, mock_db_cache, mock_current_user, sample_user_data):
        """تست تابع delete_user"""
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_user = AsyncMock(return_value=sample_user_data)
        mock_db_cache.delete_user = AsyncMock(return_value=True)
        
        # فراخوانی تابع delete_user
        result = await delete_user(1, mock_current_user)
        
        # بررسی نتیجه
        assert result["status"] == "success"
        assert "با موفقیت حذف شد" in result["message"]
    
    @patch("api.routers.users.db_cache")
    async def test_delete_self(self, mock_db_cache):
        """تست تابع delete_user برای حذف خود کاربر (که باید با خطا مواجه شود)"""
        # تنظیم کاربر جاری
        current_user = {
            "id": 1, 
            "username": "admin", 
            "role": "admin",
            "permissions": ["manage_users"]
        }
        
        # تنظیم mock برای دیتابیس
        mock_db_cache.get_user = AsyncMock(return_value=current_user)
        
        # بررسی اینکه حذف خود باعث HTTPException می‌شود
        with pytest.raises(HTTPException) as excinfo:
            await delete_user(1, current_user)
        
        # بررسی جزئیات خطا
        assert excinfo.value.status_code == 403
        assert "شما نمی‌توانید حساب کاربری خود را حذف کنید" in excinfo.value.detail
