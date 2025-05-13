"""
تست‌های یکپارچه‌سازی برای API
"""
import os
import jwt
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient
from fastapi import HTTPException, status

from api.main import app, create_access_token, get_current_user
from core.database_cache import DatabaseCache


@pytest.fixture
def test_client():
    """فیکسچر برای کلاینت تست API"""
    return TestClient(app)


@pytest.fixture
def auth_header():
    """فیکسچر برای هدر احراز هویت"""
    # تنظیم متغیر محیطی SECRET_KEY
    os.environ["SECRET_KEY"] = "test_secret_key"
    
    # ایجاد توکن
    token_data = {
        "sub": "admin",
        "name": "مدیر سیستم",
        "role": "admin",
        "permissions": ["manage_users", "manage_plugins", "view_dashboard"]
    }
    token = create_access_token(token_data)
    
    # بازگشت هدر Authorization
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_token_generation_and_validation():
    """تست یکپارچه تولید و اعتبارسنجی توکن"""
    # تنظیم متغیر محیطی SECRET_KEY
    os.environ["SECRET_KEY"] = "test_secret_key"
    
    # داده‌های کاربر
    user_data = {
        "sub": "test_user",
        "name": "کاربر تست",
        "role": "user",
        "permissions": ["view_dashboard"]
    }
    
    # تولید توکن
    token = create_access_token(user_data)
    
    # بررسی ساختار توکن
    assert isinstance(token, str)
    assert token.count('.') == 2  # format: header.payload.signature
    
    # اعتبارسنجی توکن
    user = get_current_user(token)
    
    # بررسی محتوای کاربر استخراج شده
    assert user["username"] == "test_user"
    assert user["name"] == "کاربر تست"
    assert user["role"] == "user"
    assert "view_dashboard" in user["permissions"]


@pytest.mark.asyncio
async def test_authentication_flow(test_client, mock_db, db_cache):
    """تست گردش کار احراز هویت"""
    # تنظیم داده‌های کاربر در دیتابیس
    user_credentials = {
        "username": "admin",
        "password": "admin_password"
    }
    
    hashed_password = "pbkdf2:sha256:150000$hash_test_password"
    user_in_db = {
        "id": 1,
        "username": "admin",
        "password": hashed_password,
        "email": "admin@example.com",
        "name": "مدیر سیستم",
        "role": "admin",
        "permissions": ["manage_users", "manage_plugins"]
    }
    
    # تنظیم mock ها
    with patch('api.main.db_cache', new=db_cache):
        with patch('api.main.verify_password', return_value=True):
            db_cache.fetch_one = AsyncMock(return_value=user_in_db)
            
            # فراخوانی API برای ورود
            response = test_client.post(
                "/token",
                data=user_credentials
            )
            
            # بررسی پاسخ
            assert response.status_code == 200
            
            # بررسی محتوای پاسخ
            data = response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert data["token_type"] == "bearer"
            
            # استفاده از توکن برای دریافت اطلاعات کاربر
            token = data["access_token"]
            user_response = test_client.get(
                "/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # بررسی پاسخ اطلاعات کاربر
            assert user_response.status_code == 200
            user_data = user_response.json()
            assert user_data["username"] == "admin"
            assert user_data["name"] == "مدیر سیستم"
            assert user_data["role"] == "admin"


@pytest.mark.asyncio
async def test_auth_permissions_integration(test_client, auth_header, mock_db, db_cache):
    """تست یکپارچه‌سازی سیستم مجوزها"""
    # تنظیم mock ها
    with patch('api.main.db_cache', new=db_cache):
        with patch('api.main.get_current_user') as mock_get_user:
            # تنظیم کاربر با مجوزهای مختلف
            admin_user = {
                "id": 1,
                "username": "admin",
                "name": "مدیر سیستم",
                "role": "admin",
                "permissions": ["manage_users", "manage_plugins"]
            }
            
            regular_user = {
                "id": 2,
                "username": "user",
                "name": "کاربر عادی",
                "role": "user",
                "permissions": ["view_dashboard"]
            }
            
            # ابتدا تست با کاربر ادمین
            mock_get_user.return_value = admin_user
            
            # دسترسی به API مدیریت کاربران
            admin_response = test_client.get(
                "/users/",
                headers=auth_header
            )
            
            # بررسی دسترسی موفق
            assert admin_response.status_code == 200
            
            # حالا تست با کاربر عادی
            mock_get_user.return_value = regular_user
            
            # تلاش برای دسترسی به API مدیریت کاربران
            user_response = test_client.get(
                "/users/",
                headers=auth_header
            )
            
            # بررسی عدم دسترسی
            assert user_response.status_code == 403
            assert "مجوز کافی ندارید" in user_response.json()["detail"]


@pytest.mark.asyncio
async def test_plugin_api_integration(test_client, auth_header, mock_db, db_cache):
    """تست یکپارچه‌سازی API پلاگین با لایه دیتابیس"""
    # تنظیم داده‌های پلاگین
    plugin_list = [
        {
            "id": 1,
            "name": "plugin1",
            "version": "1.0.0",
            "description": "توضیحات پلاگین 1",
            "is_enabled": True,
            "category": "utility"
        },
        {
            "id": 2,
            "name": "plugin2",
            "version": "2.0.0",
            "description": "توضیحات پلاگین 2",
            "is_enabled": False,
            "category": "security"
        }
    ]
    
    # تنظیم mock ها
    with patch('api.routers.plugins.db_cache', new=db_cache):
        with patch('api.main.get_current_user') as mock_get_user:
            # تنظیم کاربر ادمین
            admin_user = {
                "id": 1,
                "username": "admin",
                "name": "مدیر سیستم",
                "role": "admin",
                "permissions": ["manage_plugins"]
            }
            mock_get_user.return_value = admin_user
            
            # تنظیم پاسخ دیتابیس
            db_cache.get_plugins = AsyncMock(return_value=plugin_list)
            db_cache.count_plugins = AsyncMock(return_value=len(plugin_list))
            
            # فراخوانی API لیست پلاگین‌ها
            response = test_client.get(
                "/plugins/?page=1&limit=10",
                headers=auth_header
            )
            
            # بررسی پاسخ
            assert response.status_code == 200
            data = response.json()
            
            # بررسی محتوای پاسخ
            assert data["status"] == "success"
            assert data["count"] == 2
            assert data["page"] == 1
            assert len(data["plugins"]) == 2
            assert data["plugins"][0]["name"] == "plugin1"
            assert data["plugins"][1]["name"] == "plugin2"
