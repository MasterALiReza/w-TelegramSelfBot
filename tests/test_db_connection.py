#!/usr/bin/env python
"""
تست اتصال به دیتابیس PostgreSQL
"""

import os
import sys
import asyncio
from pathlib import Path

# اضافه کردن مسیر پروژه به sys.path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import Config
from core.database import Database


async def test_database_connection():
    """
    تست اتصال به دیتابیس و انجام یک کوئری ساده
    """
    print("در حال بارگذاری تنظیمات...")
    config = Config()
    
    print("در حال اتصال به دیتابیس...")
    db = Database(
        host=config.get("DB_HOST"),
        user=config.get("DB_USER"),
        password=config.get("DB_PASSWORD"),
        database=config.get("DB_NAME"),
        port=config.get("DB_PORT", 5432),
    )
    
    connected = await db.connect()
    if connected:
        print("✅ اتصال به دیتابیس با موفقیت برقرار شد")
        
        # تست یک کوئری ساده
        try:
            version = await db.fetchrow("SELECT version()")
            print(f"✅ کوئری با موفقیت اجرا شد - نسخه دیتابیس: {version['version']}")
        except Exception as e:
            print(f"❌ خطا در اجرای کوئری: {str(e)}")
    else:
        print("❌ اتصال به دیتابیس ناموفق بود")
    
    # بستن اتصال
    await db.disconnect()
    print("اتصال دیتابیس بسته شد")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_database_connection())
