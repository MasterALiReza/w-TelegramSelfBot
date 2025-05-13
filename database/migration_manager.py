"""
ماژول مدیریت migration‌های دیتابیس Supabase
"""
import os
import logging
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

from core.database import Database

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    کلاس مدیریت migration‌های دیتابیس
    """
    
    def __init__(self, database: Database):
        """
        مقداردهی اولیه
        
        Args:
            database: شیء اتصال به دیتابیس
        """
        self.db = database
        self.migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
        self.applied_migrations = []
        
    async def initialize(self) -> bool:
        """
        راه‌اندازی مدیریت migration
        
        Returns:
            bool: وضعیت راه‌اندازی
        """
        try:
            # ایجاد جدول migrations در صورت عدم وجود
            await self._create_migrations_table()
            
            # بارگیری migration‌های اجرا شده
            await self._load_applied_migrations()
            
            return True
        except Exception as e:
            logger.error(f"خطا در راه‌اندازی مدیریت migration: {str(e)}")
            return False
    
    async def _create_migrations_table(self) -> None:
        """
        ایجاد جدول migrations در صورت عدم وجود
        """
        try:
            query = """
            CREATE TABLE IF NOT EXISTS migrations (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                version TEXT,
                description TEXT,
                checksum TEXT
            );
            
            -- فعال‌سازی RLS برای جدول migrations
            ALTER TABLE migrations ENABLE ROW LEVEL SECURITY;
            
            -- ایجاد سیاست برای جدول migrations
            DROP POLICY IF EXISTS migrations_policy ON migrations;
            CREATE POLICY migrations_policy ON migrations
                USING (auth.role() = 'service_role' OR auth.role() = 'authenticated')
                WITH CHECK (auth.role() = 'service_role');
            
            DROP POLICY IF EXISTS migrations_select_policy ON migrations;
            CREATE POLICY migrations_select_policy ON migrations
                FOR SELECT USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');
            """
            
            await self.db.execute(query)
            logger.info("جدول migrations با موفقیت ایجاد شد")
        except Exception as e:
            logger.error(f"خطا در ایجاد جدول migrations: {str(e)}")
            raise
    
    async def _load_applied_migrations(self) -> None:
        """
        بارگیری لیست migration‌های اجرا شده
        """
        try:
            query = "SELECT name FROM migrations ORDER BY applied_at ASC"
            rows = await self.db.fetch_all(query)
            
            self.applied_migrations = [row['name'] for row in rows] if rows else []
            logger.info(f"تعداد {len(self.applied_migrations)} migration اجرا شده بارگیری شد")
        except Exception as e:
            logger.error(f"خطا در بارگیری migration‌های اجرا شده: {str(e)}")
            raise
    
    async def get_pending_migrations(self) -> List[str]:
        """
        دریافت لیست migration‌های در انتظار اجرا
        
        Returns:
            List[str]: لیست نام فایل‌های migration
        """
        try:
            # بررسی وجود دایرکتوری migrations
            if not os.path.exists(self.migrations_dir):
                logger.warning(f"دایرکتوری migration‌ها وجود ندارد: {self.migrations_dir}")
                return []
            
            # دریافت لیست فایل‌های migration
            migration_files = sorted([f for f in os.listdir(self.migrations_dir) 
                                      if f.endswith('.sql') and os.path.isfile(os.path.join(self.migrations_dir, f))])
            
            # فیلتر کردن migration‌های اجرا نشده
            pending_migrations = [f for f in migration_files if f not in self.applied_migrations]
            
            return pending_migrations
        except Exception as e:
            logger.error(f"خطا در دریافت migration‌های در انتظار: {str(e)}")
            return []
    
    async def apply_migration(self, migration_file: str) -> bool:
        """
        اجرای یک فایل migration
        
        Args:
            migration_file: نام فایل migration
            
        Returns:
            bool: وضعیت اجرای migration
        """
        try:
            # ساخت مسیر کامل فایل
            migration_path = os.path.join(self.migrations_dir, migration_file)
            
            # بررسی وجود فایل
            if not os.path.exists(migration_path):
                logger.error(f"فایل migration وجود ندارد: {migration_path}")
                return False
            
            # خواندن محتوای فایل
            with open(migration_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # استخراج توضیحات و نسخه
            description = version = None
            desc_match = re.search(r'-- Description: (.*?)$', content, re.MULTILINE)
            version_match = re.search(r'-- Version: (.*?)$', content, re.MULTILINE)
            
            if desc_match:
                description = desc_match.group(1).strip()
            if version_match:
                version = version_match.group(1).strip()
            
            # اجرای اسکریپت migration
            logger.info(f"در حال اجرای migration {migration_file}...")
            await self.db.execute(content)
            
            # ثبت migration در جدول migrations
            checksum = str(hash(content))
            await self.db.execute(
                "INSERT INTO migrations (name, version, description, checksum) VALUES ($1, $2, $3, $4)",
                (migration_file, version, description, checksum)
            )
            
            # افزودن به لیست migration‌های اجرا شده
            self.applied_migrations.append(migration_file)
            
            logger.info(f"Migration {migration_file} با موفقیت اجرا شد")
            return True
        except Exception as e:
            logger.error(f"خطا در اجرای migration {migration_file}: {str(e)}")
            return False
    
    async def apply_all_pending_migrations(self) -> Tuple[int, int]:
        """
        اجرای تمام migration‌های در انتظار
        
        Returns:
            Tuple[int, int]: تعداد migration‌های موفق و ناموفق
        """
        success_count = fail_count = 0
        
        # دریافت لیست migration‌های در انتظار
        pending_migrations = await self.get_pending_migrations()
        
        if not pending_migrations:
            logger.info("هیچ migration جدیدی برای اجرا وجود ندارد")
            return success_count, fail_count
        
        # اجرای migration‌ها به ترتیب
        for migration_file in pending_migrations:
            result = await self.apply_migration(migration_file)
            if result:
                success_count += 1
            else:
                fail_count += 1
                # توقف در صورت بروز خطا
                logger.error(f"اجرای migration‌ها به دلیل خطا در {migration_file} متوقف شد")
                break
        
        logger.info(f"تعداد {success_count} migration با موفقیت اجرا شد. تعداد {fail_count} migration با خطا مواجه شد.")
        return success_count, fail_count
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """
        دریافت وضعیت migration‌ها
        
        Returns:
            Dict[str, Any]: وضعیت migration‌ها
        """
        try:
            # دریافت لیست migration‌های اجرا شده
            query = """
            SELECT 
                name, 
                applied_at, 
                version, 
                description 
            FROM migrations 
            ORDER BY applied_at ASC
            """
            applied = await self.db.fetch_all(query)
            
            # دریافت migration‌های در انتظار
            pending = await self.get_pending_migrations()
            
            return {
                "applied": [dict(row) for row in applied] if applied else [],
                "pending": pending,
                "total_applied": len(self.applied_migrations),
                "total_pending": len(pending),
                "last_applied": applied[-1]['applied_at'] if applied else None
            }
        except Exception as e:
            logger.error(f"خطا در دریافت وضعیت migration‌ها: {str(e)}")
            return {"error": str(e)}


async def run_migrations(database: Database) -> bool:
    """
    اجرای تمام migration‌های جدید
    
    Args:
        database: شیء اتصال به دیتابیس
        
    Returns:
        bool: وضعیت اجرای migration‌ها
    """
    try:
        manager = MigrationManager(database)
        await manager.initialize()
        
        success, fail = await manager.apply_all_pending_migrations()
        
        return fail == 0
    except Exception as e:
        logger.error(f"خطا در اجرای migration‌ها: {str(e)}")
        return False
