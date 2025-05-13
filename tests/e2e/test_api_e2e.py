"""
تست‌های End-to-End برای API
"""
import os
import jwt
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from api.main import create_access_token


@pytest.mark.e2e
def test_api_root_endpoint(test_client):
    """تست نقطه پایانی اصلی API"""
    response = test_client.get("/")
    
    # بررسی پاسخ
    assert response.status_code == 200
    assert "به API سلف بات تلگرام خوش آمدید" in response.json()["message"]


@pytest.mark.e2e
def test_api_status_endpoint(test_client):
    """تست نقطه پایانی وضعیت API"""
    response = test_client.get("/status")
    
    # بررسی پاسخ
    assert response.status_code == 200
    assert response.json()["status"] in ["active", "initializing"]
    assert "version" in response.json()


@pytest.mark.e2e
def test_token_generation_and_validation():
    """تست تولید و اعتبارسنجی توکن"""
    # داده‌های کاربر
    user_data = {
        "sub": "test_user",
        "name": "کاربر تست",
        "role": "user"
    }
    
    # تولید توکن
    token = create_access_token(user_data)
    
    # بررسی ساختار توکن
    assert isinstance(token, str)
    assert token.count(".") == 2  # format: header.payload.signature
    
    # اعتبارسنجی توکن با رمزگشایی آن
    secret_key = os.environ["SECRET_KEY"]
    payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    
    # بررسی محتوای payload
    assert payload["sub"] == "test_user"
    assert payload["name"] == "کاربر تست"
    assert payload["role"] == "user"
    assert "exp" in payload  # زمان انقضا


@pytest.mark.e2e
@pytest.mark.auth
def test_auth_flow(test_client, test_env):
    """تست گردش کار احراز هویت"""
    # داده‌های ورود
    login_data = {
        "username": "admin",
        "password": "admin_password"
    }
    
    # فراخوانی API برای ورود
    response = test_client.post("/token", data=login_data)
    
    # اگر کاربر در دیتابیس وجود ندارد، احتمالاً با خطای 401 مواجه می‌شویم
    # در محیط واقعی، باید ابتدا کاربر را در دیتابیس ایجاد کنیم
    if response.status_code == 401:
        pytest.skip("کاربر admin در دیتابیس وجود ندارد. نیاز به راه‌اندازی داده‌های تست است.")
    
    # بررسی پاسخ موفقیت‌آمیز
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "token_type" in response.json()
    assert response.json()["token_type"] == "bearer"
    
    # استخراج توکن
    token = response.json()["access_token"]
    
    # استفاده از توکن برای دریافت اطلاعات کاربر
    user_response = test_client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # بررسی پاسخ اطلاعات کاربر
    assert user_response.status_code == 200
    assert user_response.json()["username"] == "admin"


@pytest.mark.e2e
@pytest.mark.users
def test_users_list_endpoint(test_client, auth_headers):
    """تست نقطه پایانی لیست کاربران"""
    response = test_client.get("/users/", headers=auth_headers)
    
    # بررسی پاسخ
    if response.status_code == 403:
        pytest.skip("کاربر تست دسترسی کافی برای مشاهده لیست کاربران ندارد.")
        
    assert response.status_code == 200
    assert "users" in response.json()
    assert "count" in response.json()
    assert "page" in response.json()
    assert "total_pages" in response.json()


@pytest.mark.e2e
@pytest.mark.plugins
def test_plugins_list_endpoint(test_client, auth_headers):
    """تست نقطه پایانی لیست پلاگین‌ها"""
    response = test_client.get("/plugins/", headers=auth_headers)
    
    # بررسی پاسخ
    if response.status_code == 403:
        pytest.skip("کاربر تست دسترسی کافی برای مشاهده لیست پلاگین‌ها ندارد.")
        
    assert response.status_code == 200
    assert "plugins" in response.json()
    assert "count" in response.json()
    assert "page" in response.json()
    assert "total_pages" in response.json()


@pytest.mark.e2e
@pytest.mark.plugins
def test_plugin_crud_operations(test_client, auth_headers):
    """تست عملیات CRUD پلاگین"""
    # 1. ایجاد پلاگین جدید
    new_plugin_data = {
        "name": "test_e2e_plugin",
        "version": "1.0.0",
        "description": "پلاگین تست E2E",
        "author": "آزمونگر",
        "category": "test",
        "source_code": "async def start(message):\n    return 'این یک پلاگین تست است'"
    }
    
    create_response = test_client.post(
        "/plugins/",
        json=new_plugin_data,
        headers=auth_headers
    )
    
    # در صورت خطای دسترسی، تست را رد می‌کنیم
    if create_response.status_code == 403:
        pytest.skip("کاربر تست دسترسی کافی برای ایجاد پلاگین ندارد.")
    
    # بررسی پاسخ ایجاد
    assert create_response.status_code == 201
    assert "plugin" in create_response.json()
    assert create_response.json()["plugin"]["name"] == "test_e2e_plugin"
    
    # دریافت شناسه پلاگین ایجاد شده
    plugin_id = create_response.json()["plugin"]["id"]
    
    # 2. دریافت اطلاعات پلاگین
    get_response = test_client.get(
        f"/plugins/{plugin_id}",
        headers=auth_headers
    )
    
    # بررسی پاسخ دریافت
    assert get_response.status_code == 200
    assert get_response.json()["plugin"]["id"] == plugin_id
    assert get_response.json()["plugin"]["name"] == "test_e2e_plugin"
    
    # 3. به‌روزرسانی پلاگین
    update_data = {
        "description": "توضیحات به‌روزرسانی شده برای پلاگین تست"
    }
    
    update_response = test_client.patch(
        f"/plugins/{plugin_id}",
        json=update_data,
        headers=auth_headers
    )
    
    # بررسی پاسخ به‌روزرسانی
    assert update_response.status_code == 200
    assert update_response.json()["plugin"]["description"] == "توضیحات به‌روزرسانی شده برای پلاگین تست"
    
    # 4. تغییر وضعیت پلاگین (فعال/غیرفعال)
    toggle_data = {
        "is_enabled": False
    }
    
    toggle_response = test_client.put(
        f"/plugins/{plugin_id}/toggle",
        json=toggle_data,
        headers=auth_headers
    )
    
    # بررسی پاسخ تغییر وضعیت
    assert toggle_response.status_code == 200
    assert toggle_response.json()["plugin"]["is_enabled"] is False
    
    # 5. حذف پلاگین
    delete_response = test_client.delete(
        f"/plugins/{plugin_id}",
        headers=auth_headers
    )
    
    # بررسی پاسخ حذف
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "success"
    assert "با موفقیت حذف شد" in delete_response.json()["message"]
    
    # تایید حذف با تلاش برای دریافت مجدد
    get_deleted_response = test_client.get(
        f"/plugins/{plugin_id}",
        headers=auth_headers
    )
    
    assert get_deleted_response.status_code == 404
