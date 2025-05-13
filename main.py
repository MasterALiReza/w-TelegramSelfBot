#!/usr/bin/env python
"""
فایل اصلی برای راه‌اندازی سلف بات تلگرام
"""
import os
import sys
import signal
import logging
import asyncio
from pathlib import Path

# افزودن مسیر فعلی به مسیر جستجوی پایتون
sys.path.insert(0, str(Path(__file__).parent.absolute()))

# وارد کردن ماژول‌های پروژه
from core.logger import get_logger
from core.config import Config
from core.database import Database
from core.redis_manager import initialize_redis
from core.database_cache import DatabaseCache
from core.crypto import CryptoManager
from core.license_manager import LicenseManager
from core.plugin_marketplace import PluginMarketplace
from core.client import TelegramClient
from core.plugin_manager import PluginManager
from core.event_handler import EventHandler

# تنظیم لاگر
logger = get_logger("main")


async def initialize_selfbot():
    """
    راه‌اندازی سلف بات و ماژول‌های آن
    """
    logger.info("در حال راه‌اندازی سلف بات تلگرام...")
    
    # بارگذاری تنظیمات
    config = Config()
    logger.info("تنظیمات بارگذاری شد")
    
    # اتصال به دیتابیس
    db = Database(
        host=config.get("DB_HOST", "localhost"),
        port=config.get("DB_PORT", 5432),
        user=config.get("DB_USER", "postgres"),
        password=config.get("DB_PASSWORD", "postgres"),
        database=config.get("DB_NAME", "selfbot")
    )
    connected = await db.connect()
    if not connected:
        logger.error("خطا در اتصال به دیتابیس. لطفاً تنظیمات را بررسی کنید.")
        return None
    logger.info("اتصال به دیتابیس با موفقیت برقرار شد")
    
    # اتصال به Redis
    redis = await initialize_redis(
        host=config.get("REDIS_HOST", "localhost"),
        port=config.get("REDIS_PORT", 6379),
        db=config.get("REDIS_DB", 0),
        password=config.get("REDIS_PASSWORD", ""),
        prefix=config.get("REDIS_PREFIX", "selfbot:")
    )
    logger.info("اتصال به Redis با موفقیت برقرار شد")
    
    # ایجاد نمونه DatabaseCache
    db_cache = DatabaseCache(db, redis)
    logger.info("مدیریت کش دیتابیس راه‌اندازی شد")
    
    # ایجاد CryptoManager
    crypto_manager = CryptoManager(config.get("LICENSE_ENCRYPT_KEY", "default_key"))
    logger.info("ماژول رمزنگاری راه‌اندازی شد")
    
    # ایجاد LicenseManager
    license_manager = LicenseManager(db_cache, crypto_manager)
    await license_manager.initialize()
    logger.info("مدیریت لایسنس راه‌اندازی شد")

    # ایجاد PluginMarketplace
    plugin_marketplace = PluginMarketplace(db_cache, license_manager)
    await plugin_marketplace.initialize()
    logger.info("بازارچه پلاگین راه‌اندازی شد")
    
    # ایجاد کلاینت تلگرام
    try:
        api_id = int(config.get("TELEGRAM_API_ID", "0"))
        api_hash = config.get("TELEGRAM_API_HASH", "")
        
        if api_id == 0 or not api_hash:
            logger.error("TELEGRAM_API_ID و TELEGRAM_API_HASH در فایل .env تنظیم نشده‌اند")
            logger.info("برای دریافت API ID و API Hash، به سایت my.telegram.org مراجعه کنید")
            return None
            
        phone = config.get("TELEGRAM_PHONE", "")
        session_name = config.get("TELEGRAM_SESSION_NAME", "selfbot_session")
        
        client = TelegramClient(
            api_id=api_id,
            api_hash=api_hash,
            phone=phone,
            session_name=session_name
        )
        logger.info("کلاینت تلگرام ایجاد شد")
    except Exception as e:
        logger.error(f"خطا در ایجاد کلاینت تلگرام: {str(e)}")
        return None
    
    # ایجاد مدیریت پلاگین
    plugin_manager = PluginManager(client, db_cache)
    await plugin_manager.initialize()
    logger.info("مدیریت پلاگین راه‌اندازی شد")
    
    # ایجاد مدیریت رویدادها
    event_handler = EventHandler(client, plugin_manager)
    logger.info("مدیریت رویدادها راه‌اندازی شد")
    
    # مقداردهی event_handler در client
    client.set_event_handler(event_handler)
    
    # ایجاد آبجکت برای بازگرداندن
    selfbot = {
        "config": config,
        "db": db,
        "redis": redis,
        "db_cache": db_cache,
        "crypto_manager": crypto_manager,
        "license_manager": license_manager,
        "plugin_marketplace": plugin_marketplace,
        "client": client,
        "plugin_manager": plugin_manager,
        "event_handler": event_handler
    }
    
    return selfbot


async def run_selfbot():
    """
    اجرای سلف بات
    """
    # راه‌اندازی ماژول‌ها
    selfbot = await initialize_selfbot()
    if not selfbot:
        logger.error("خطا در راه‌اندازی سلف بات")
        return
    
    # تعریف سیگنال‌ها برای خروج مناسب
    def signal_handler(sig, frame):
        logger.info("سیگنال خروج دریافت شد. در حال خاموش کردن...")
        asyncio.create_task(shutdown_selfbot(selfbot))
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # لاگین به تلگرام
    client = selfbot["client"]
    try:
        logger.info("در حال اتصال به تلگرام...")
        await client.connect()
        
        if not await client.is_logged_in():
            logger.info("نیاز به احراز هویت تلگرام...")
            await client.start()
        
        logger.info("اتصال به تلگرام با موفقیت انجام شد")
        
        # بارگذاری پلاگین‌ها
        plugin_manager = selfbot["plugin_manager"]
        loaded_plugins = await plugin_manager.load_all_plugins()
        logger.info(f"{len(loaded_plugins)} پلاگین بارگذاری شد")
        
        # اجرای وظایف پس‌زمینه
        tasks = []
        
        # نگه داشتن برنامه در حال اجرا
        logger.info("سلف بات با موفقیت راه‌اندازی شد و در حال اجراست")
        logger.info("برای خروج، کلید Ctrl+C را فشار دهید")
        
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("برنامه توسط کاربر متوقف شد")
    except Exception as e:
        logger.error(f"خطا در اجرای سلف بات: {str(e)}")
    finally:
        await shutdown_selfbot(selfbot)


async def shutdown_selfbot(selfbot):
    """
    خاموش کردن سلف بات و آزادسازی منابع
    """
    logger.info("در حال خاموش کردن سلف بات...")
    
    # قطع اتصال کلاینت تلگرام
    try:
        await selfbot["client"].disconnect()
    except:
        pass
    
    # قطع اتصال دیتابیس
    try:
        await selfbot["db"].disconnect()
    except:
        pass
    
    # قطع اتصال Redis
    try:
        await selfbot["redis"].disconnect()
    except:
        pass
    
    logger.info("سلف بات با موفقیت خاموش شد")


if __name__ == "__main__":
    # تنظیم asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # اجرای برنامه
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_selfbot())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
