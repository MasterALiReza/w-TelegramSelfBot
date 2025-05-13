"""
اسکریپت راه‌اندازی و تست Redis
"""
import os
import sys
import time
import redis
from dotenv import load_dotenv

# اضافه کردن مسیر اصلی پروژه به مسیرهای پایتون
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# بارگذاری متغیرهای محیطی
load_dotenv()


def check_redis_connection():
    """
    بررسی اتصال به Redis
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"تلاش برای اتصال به Redis در آدرس: {redis_url}")
    
    try:
        # ایجاد اتصال به Redis
        client = redis.from_url(redis_url)
        
        # تست اتصال با یک دستور ساده
        client.ping()
        
        print("✅ اتصال به Redis با موفقیت انجام شد!")
        return client
    except redis.ConnectionError:
        print("❌ خطا در اتصال به Redis. لطفاً مطمئن شوید که سرور Redis در حال اجراست.")
        return None
    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {str(e)}")
        return None


def run_redis_tests(client):
    """
    اجرای تست‌های پایه Redis
    
    Args:
        client: اتصال Redis
    """
    if not client:
        return False

    print("\n=== اجرای تست‌های پایه Redis ===")
    
    try:
        # تست ذخیره و بازیابی داده
        test_key = "test:selfbot:key"
        test_value = "این یک تست است!"
        
        print(f"ذخیره کلید: {test_key} = {test_value}")
        client.set(test_key, test_value, ex=60)  # منقضی شدن بعد از 60 ثانیه
        
        # بازیابی داده
        retrieved_value = client.get(test_key)
        if isinstance(retrieved_value, bytes):
            retrieved_value = retrieved_value.decode('utf-8')
        
        print(f"بازیابی کلید: {test_key} = {retrieved_value}")
        
        if retrieved_value == test_value:
            print("✅ تست ذخیره و بازیابی داده: موفق")
        else:
            print("❌ تست ذخیره و بازیابی داده: ناموفق")
            return False
        
        # تست صف پیام‌ها
        queue_name = "test:selfbot:queue"
        print(f"\nافزودن آیتم‌ها به صف: {queue_name}")
        
        # پاکسازی صف قبلی (اگر وجود داشته باشد)
        client.delete(queue_name)
        
        # اضافه کردن آیتم‌ها به صف
        for i in range(1, 6):
            client.lpush(queue_name, f"آیتم صف {i}")
            print(f"  + آیتم {i} به صف اضافه شد")
        
        # بازیابی آیتم‌ها از صف
        print("\nبازیابی آیتم‌ها از صف:")
        for i in range(1, 6):
            item = client.rpop(queue_name)
            if isinstance(item, bytes):
                item = item.decode('utf-8')
            print(f"  - آیتم بازیابی شده: {item}")
        
        # تست pub/sub
        channel_name = "test:selfbot:channel"
        print(f"\nتست سیستم Pub/Sub در کانال: {channel_name}")
        
        # ایجاد یک پابلیش برای تست
        message_count = client.publish(channel_name, "این یک پیام تست است")
        print(f"پیام به {message_count} مشترک ارسال شد")
        
        print("✅ تست‌های Redis با موفقیت انجام شد!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در اجرای تست‌ها: {str(e)}")
        return False


def setup_environment_variables():
    """
    تنظیم متغیرهای محیطی مورد نیاز
    """
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    
    # بررسی وجود فایل .env
    if not os.path.exists(env_file):
        print("فایل .env یافت نشد. ایجاد فایل .env جدید...")
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write("# تنظیمات Redis\n")
            f.write("REDIS_URL=redis://localhost:6379/0\n")
            f.write("REDIS_PASSWORD=\n")
        print("✅ فایل .env ایجاد شد.")
    else:
        # بررسی وجود تنظیمات Redis در فایل .env
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        if "REDIS_URL" not in env_content:
            print("اضافه کردن تنظیمات Redis به فایل .env...")
            with open(env_file, 'a', encoding='utf-8') as f:
                f.write("\n# تنظیمات Redis\n")
                f.write("REDIS_URL=redis://localhost:6379/0\n")
                f.write("REDIS_PASSWORD=\n")
            print("✅ تنظیمات Redis به فایل .env اضافه شد.")
    
    # بارگذاری مجدد متغیرهای محیطی
    load_dotenv()


def main():
    """
    تابع اصلی
    """
    print("=== راه‌اندازی و تست Redis ===\n")
    
    # تنظیم متغیرهای محیطی
    setup_environment_variables()
    
    # بررسی اتصال به Redis
    client = check_redis_connection()
    
    if client:
        # اجرای تست‌ها
        run_redis_tests(client)
        
        print("\nنکته: برای استفاده از Redis در محیط توسعه، می‌توانید از داکر استفاده کنید:")
        print("docker-compose up -d redis")
    else:
        print("\nراهنمای راه‌اندازی Redis:")
        print("1. اطمینان حاصل کنید که Docker نصب شده باشد.")
        print("2. با دستور زیر Redis را راه‌اندازی کنید:")
        print("   docker-compose up -d redis")
        print("3. سپس این اسکریپت را مجدداً اجرا کنید.")


if __name__ == "__main__":
    main()
