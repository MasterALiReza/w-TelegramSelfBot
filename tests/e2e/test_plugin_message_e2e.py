"""
تست‌های End-to-End برای سیستم پلاگین و پردازش پیام‌ها
"""
import os
import pytest
import asyncio
import tempfile

from core.plugin_manager import PluginManager


@pytest.fixture
async def sample_plugins(plugins_dir):
    """فیکسچر برای ایجاد چند پلاگین نمونه"""
    # تعریف چند پلاگین ساده برای آزمایش
    plugins = {
        "echo": """
async def start(message):
    # پلاگین ساده تکرار پیام
    if message.get("text"):
        return {"response": message.get("text")}
    return {"response": "پیامی دریافت نشد!"}
""",
        "greeting": """
async def start(message):
    # پلاگین خوش‌آمدگویی
    name = message.get("sender_name", "کاربر")
    return {"response": f"سلام {name}! خوش آمدید."}
""",
        "calculator": """
import re

async def start(message):
    # پلاگین ماشین حساب ساده
    text = message.get("text", "")
    if not text or not text.startswith("/calc "):
        return {"response": "فرمت صحیح: /calc 2+2"}
    
    expression = text.replace("/calc ", "").strip()
    try:
        # بررسی امنیتی برای جلوگیری از اجرای کد
        if re.match(r'^[0-9\+\-\*\/\(\)\.\s]+$', expression):
            result = eval(expression)
            return {"response": f"{expression} = {result}"}
        else:
            return {"response": "عملیات غیرمجاز!"}
    except Exception as e:
        return {"response": f"خطا: {str(e)}"}
"""
    }
    
    # ایجاد فایل‌های پلاگین در دایرکتوری تست
    for name, content in plugins.items():
        file_path = os.path.join(plugins_dir, f"{name}.py")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    yield list(plugins.keys())


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_plugin_loading(plugin_manager, sample_plugins):
    """تست بارگذاری پلاگین‌ها"""
    # کشف و بارگذاری پلاگین‌ها
    discovered_plugins = await plugin_manager.discover_plugins()
    
    # بررسی کشف تمام پلاگین‌های نمونه
    for plugin_name in sample_plugins:
        assert plugin_name in discovered_plugins
    
    # بارگذاری هر پلاگین
    for plugin_name in sample_plugins:
        result = await plugin_manager.load_plugin(plugin_name)
        assert result is True
        assert plugin_name in plugin_manager.plugins
        assert plugin_manager.plugins[plugin_name]["enabled"] is True


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_plugin_execution(plugin_manager, sample_plugins):
    """تست اجرای پلاگین‌ها"""
    # اطمینان از بارگذاری پلاگین‌ها
    for plugin_name in sample_plugins:
        if plugin_name not in plugin_manager.plugins:
            await plugin_manager.load_plugin(plugin_name)
    
    # 1. تست پلاگین echo
    message_data = {
        "message_id": 123,
        "text": "این یک پیام تست است",
        "sender_id": 456,
        "sender_name": "کاربر تست",
        "chat_id": 789,
        "chat_title": "گروه تست"
    }
    
    echo_result = await plugin_manager.execute_plugin("echo", message_data)
    assert "response" in echo_result
    assert echo_result["response"] == "این یک پیام تست است"
    
    # 2. تست پلاگین greeting
    greeting_result = await plugin_manager.execute_plugin("greeting", message_data)
    assert "response" in greeting_result
    assert "سلام کاربر تست! خوش آمدید." in greeting_result["response"]
    
    # 3. تست پلاگین calculator با ورودی معتبر
    calc_message = message_data.copy()
    calc_message["text"] = "/calc 2+2*3"
    calc_result = await plugin_manager.execute_plugin("calculator", calc_message)
    assert "response" in calc_result
    assert "2+2*3 = 8" in calc_result["response"]
    
    # 4. تست پلاگین calculator با ورودی نامعتبر
    calc_message["text"] = "/calc print('hack')"
    calc_result = await plugin_manager.execute_plugin("calculator", calc_message)
    assert "response" in calc_result
    assert "عملیات غیرمجاز" in calc_result["response"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_plugin_disable_enable(plugin_manager, sample_plugins):
    """تست غیرفعال و فعال کردن پلاگین‌ها"""
    # اطمینان از بارگذاری پلاگین‌ها
    plugin_name = sample_plugins[0]  # استفاده از اولین پلاگین
    if plugin_name not in plugin_manager.plugins:
        await plugin_manager.load_plugin(plugin_name)
    
    # پیام تست
    message_data = {
        "message_id": 123,
        "text": "این یک پیام تست است",
        "sender_id": 456,
        "sender_name": "کاربر تست"
    }
    
    # 1. تأیید فعال بودن اولیه
    assert plugin_manager.plugins[plugin_name]["enabled"] is True
    
    # اجرای پلاگین در حالت فعال
    result1 = await plugin_manager.execute_plugin(plugin_name, message_data)
    assert "response" in result1
    
    # 2. غیرفعال کردن پلاگین
    disable_result = await plugin_manager.disable_plugin(plugin_name)
    assert disable_result is True
    assert plugin_manager.plugins[plugin_name]["enabled"] is False
    
    # تلاش برای اجرای پلاگین در حالت غیرفعال
    try:
        result2 = await plugin_manager.execute_plugin(plugin_name, message_data)
        # اگر به اینجا برسیم، باید خروجی نداشته باشیم یا خطا داشته باشیم
        assert "response" not in result2 or "error" in result2
    except Exception as e:
        # ممکن است اجرای پلاگین غیرفعال باعث خطا شود که قابل قبول است
        pass
    
    # 3. فعال کردن مجدد پلاگین
    enable_result = await plugin_manager.enable_plugin(plugin_name)
    assert enable_result is True
    assert plugin_manager.plugins[plugin_name]["enabled"] is True
    
    # اجرای پلاگین پس از فعال‌سازی مجدد
    result3 = await plugin_manager.execute_plugin(plugin_name, message_data)
    assert "response" in result3


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_plugin_update(plugin_manager, plugins_dir, sample_plugins):
    """تست به‌روزرسانی پلاگین‌ها"""
    # انتخاب یک پلاگین برای به‌روزرسانی
    plugin_name = sample_plugins[0]
    
    # اطمینان از بارگذاری پلاگین
    if plugin_name not in plugin_manager.plugins:
        await plugin_manager.load_plugin(plugin_name)
    
    # محتوای به‌روزرسانی شده پلاگین
    updated_content = """
async def start(message):
    # نسخه به‌روزرسانی شده پلاگین
    if message.get("text"):
        return {"response": f"پاسخ به‌روزرسانی شده: {message.get('text')}"}
    return {"response": "پیامی دریافت نشد!"}
"""
    
    # به‌روزرسانی فایل پلاگین
    file_path = os.path.join(plugins_dir, f"{plugin_name}.py")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    # اجرای به‌روزرسانی پلاگین
    reload_result = await plugin_manager.reload_plugin(plugin_name)
    assert reload_result is True
    
    # بررسی عملکرد پلاگین به‌روزرسانی شده
    message_data = {
        "message_id": 123,
        "text": "این یک پیام تست است",
        "sender_id": 456
    }
    
    result = await plugin_manager.execute_plugin(plugin_name, message_data)
    assert "response" in result
    assert "پاسخ به‌روزرسانی شده" in result["response"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_message_processing_flow(plugin_manager, sample_plugins):
    """تست گردش کار پردازش پیام"""
    # اطمینان از بارگذاری پلاگین‌ها
    for plugin_name in sample_plugins:
        if plugin_name not in plugin_manager.plugins:
            await plugin_manager.load_plugin(plugin_name)
    
    # شبیه‌سازی یک پیام ورودی
    incoming_message = {
        "message_id": 123,
        "text": "/calc 10+5*2",
        "sender_id": 456,
        "sender_name": "کاربر تست",
        "chat_id": 789,
        "chat_type": "private",
        "date": 1715619600  # 2025-05-13T17:00:00
    }
    
    # شبیه‌سازی تابع پردازش پیام
    async def process_message(message):
        # تشخیص دستور
        text = message.get("text", "")
        
        if text.startswith("/calc"):
            # استفاده از پلاگین calculator
            return await plugin_manager.execute_plugin("calculator", message)
        elif text.startswith("/echo"):
            # استفاده از پلاگین echo
            echo_message = message.copy()
            echo_message["text"] = text.replace("/echo", "").strip()
            return await plugin_manager.execute_plugin("echo", echo_message)
        else:
            # استفاده از پلاگین greeting به صورت پیش‌فرض
            return await plugin_manager.execute_plugin("greeting", message)
    
    # تست پردازش پیام با دستور calc
    calc_result = await process_message(incoming_message)
    assert "response" in calc_result
    assert "10+5*2 = 20" in calc_result["response"]
    
    # تست پردازش پیام با دستور echo
    echo_message = incoming_message.copy()
    echo_message["text"] = "/echo سلام دنیا!"
    echo_result = await process_message(echo_message)
    assert "response" in echo_result
    assert echo_result["response"] == "سلام دنیا!"
    
    # تست پردازش پیام بدون دستور خاص
    greeting_message = incoming_message.copy()
    greeting_message["text"] = "سلام"
    greeting_result = await process_message(greeting_message)
    assert "response" in greeting_result
    assert "سلام کاربر تست" in greeting_result["response"]
