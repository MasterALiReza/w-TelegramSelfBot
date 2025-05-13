"""
تست‌های واحد برای ماژول اصلی API
"""
import os
import jwt
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.main import app, create_access_token, get_current_user, oauth2_scheme


@pytest.fixture
def test_client():
    """فیکسچر برای ایجاد کلاینت تست"""
    return TestClient(app)


@pytest.fixture
def user_token_data():
    """فیکسچر برای داده‌های توکن کاربر"""
    return {
        "sub": "admin",
        "name": "ادمین سیستم",
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }


class TestAPIAuthentication:
    """تست‌های مربوط به احراز هویت API"""
    
    def test_create_access_token(self, user_token_data):
        """تست تابع ایجاد توکن دسترسی"""
        # حذف فیلد exp از داده‌ها چون به صورت خودکار در تابع اضافه می‌شود
        data_copy = user_token_data.copy()
        data_copy.pop("exp", None)
        
        # تنظیم کلید رمزنگاری برای JWT
        with patch.dict(os.environ, {"SECRET_KEY": "test_secret_key"}):
            token = create_access_token(data_copy)
            
            # بررسی اینکه توکن یک رشته باشد
            assert isinstance(token, str)
            
            # رمزگشایی توکن و بررسی محتوا
            decoded = jwt.decode(token, "test_secret_key", algorithms=["HS256"])
            assert decoded["sub"] == "admin"
            assert decoded["name"] == "ادمین سیستم"
            assert decoded["role"] == "admin"
            assert "exp" in decoded  # زمان انقضا باید وجود داشته باشد
    
    @patch("jwt.decode")
    @patch.dict(os.environ, {"SECRET_KEY": "test_secret_key"})
    def test_get_current_user_valid(self, mock_decode):
        """تست تابع دریافت کاربر جاری با توکن معتبر"""
        # تنظیم مقدار برگشتی برای jwt.decode
        mock_decode.return_value = {
            "sub": "test_user",
            "name": "کاربر تست",
            "role": "user"
        }
        
        # فراخوانی تابع get_current_user
        user = get_current_user("valid_token")
        
        # بررسی‌ها
        assert user["username"] == "test_user"
        assert user["name"] == "کاربر تست"
        assert user["role"] == "user"
        mock_decode.assert_called_once_with(
            "valid_token", "test_secret_key", algorithms=["HS256"]
        )
    
    @patch("jwt.decode")
    @patch.dict(os.environ, {"SECRET_KEY": "test_secret_key"})
    def test_get_current_user_invalid_token(self, mock_decode):
        """تست تابع دریافت کاربر جاری با توکن نامعتبر"""
        # تنظیم خطا برای jwt.decode
        mock_decode.side_effect = jwt.PyJWTError("Invalid token")
        
        # بررسی اینکه فراخوانی با توکن نامعتبر باعث HTTPException می‌شود
        with pytest.raises(HTTPException) as excinfo:
            get_current_user("invalid_token")
        
        # بررسی جزئیات خطا
        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "توکن نامعتبر" in excinfo.value.detail


class TestAPIEndpoints:
    """تست‌های مربوط به نقاط پایانی API"""
    
    def test_root_endpoint(self, test_client):
        """تست مسیر اصلی"""
        response = test_client.get("/")
        
        # بررسی پاسخ
        assert response.status_code == 200
        assert response.json()["message"] == "به API سلف بات تلگرام خوش آمدید"
    
    @patch("api.main.Database")
    @patch("api.main.RedisManager")
    def test_status_endpoint(self, mock_redis, mock_db, test_client):
        """تست مسیر وضعیت"""
        # تنظیم mockها
        mock_db.is_connected.return_value = True
        mock_redis.is_connected.return_value = True
        
        # فراخوانی API
        response = test_client.get("/status")
        
        # بررسی پاسخ
        assert response.status_code == 200
        assert response.json()["status"] == "active"
        assert "timestamp" in response.json()
        assert "version" in response.json()
        assert response.json()["database"] == "connected"
    
    @patch("api.main.get_current_user")
    def test_read_users_me_endpoint(self, mock_get_current_user, test_client):
        """تست مسیر اطلاعات کاربر جاری"""
        # تنظیم mock برای تابع get_current_user
        user_data = {
            "username": "test_user",
            "name": "کاربر تست",
            "role": "user",
            "permissions": ["read", "write"]
        }
        mock_get_current_user.return_value = user_data
        
        # فراخوانی API با هدر Authorization
        response = test_client.get(
            "/users/me",
            headers={"Authorization": "Bearer dummy_token"}
        )
        
        # بررسی پاسخ
        assert response.status_code == 200
        assert response.json() == user_data
    
    def test_login_endpoint_missing_credentials(self, test_client):
        """تست مسیر ورود با اعتبارنامه ناقص"""
        # فراخوانی API بدون ارسال داده‌ها
        response = test_client.post("/token")
        
        # بررسی پاسخ
        assert response.status_code == 422  # Unprocessable Entity
    
    @patch("api.main.Database")
    def test_login_endpoint_invalid_credentials(self, mock_db, test_client):
        """تست مسیر ورود با اعتبارنامه نامعتبر"""
        # تنظیم mock برای دیتابیس
        mock_db.get_user.return_value = None
        
        # فراخوانی API با داده‌های نادرست
        response = test_client.post(
            "/token",
            data={"username": "wrong_user", "password": "wrong_pass"}
        )
        
        # بررسی پاسخ
        assert response.status_code == 401
        assert "نام کاربری یا رمز عبور نادرست است" in response.json()["detail"]
