#!/usr/bin/env python
"""
اسکریپت بررسی و گزارش‌گیری مشکلات سلف بات تلگرام
"""

import os
import sys
import json
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Any, Tuple

# اضافه کردن مسیر پروژه به مسیر جستجوی پایتون
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# ایمپورت ماژول لاگر بهبود یافته
from core.logger import get_logger

# تنظیم لاگر
logger = get_logger("debug_checker")


class DebugChecker:
    """کلاس بررسی و گزارش‌گیری مشکلات پروژه"""
    
    def __init__(self):
        """مقداردهی اولیه"""
        self.core_modules = [
            'database', 'redis_manager', 'database_cache', 'license_manager',
            'plugin_marketplace', 'client', 'event_handler', 'plugin_manager',
            'scheduler', 'background_tasks', 'crypto', 'localization', 'config', 'logger'
        ]
        self.api_modules = ['main', 'routers.users', 'routers.plugins']
        self.issues = []
        
    def check_module_imports(self, module_path: str) -> List[str]:
        """
        بررسی ایمپورت‌های موجود در ماژول
        
        Args:
            module_path: مسیر ماژول (مثال: core.database)
            
        Returns:
            List[str]: لیست مشکلات یافت شده
        """
        issues = []
        try:
            # تلاش برای ایمپورت ماژول
            module = importlib.import_module(module_path)
            logger.info(f"✅ ماژول {module_path} با موفقیت ایمپورت شد")
        except ModuleNotFoundError as e:
            issues.append(f"❌ ماژول {module_path} یافت نشد: {str(e)}")
            logger.error(f"ماژول {module_path} یافت نشد: {str(e)}")
        except ImportError as e:
            issues.append(f"❌ خطا در ایمپورت ماژول {module_path}: {str(e)}")
            logger.error(f"خطا در ایمپورت ماژول {module_path}: {str(e)}")
        except Exception as e:
            issues.append(f"❌ خطای نامشخص در ایمپورت ماژول {module_path}: {str(e)}")
            logger.error(f"خطای نامشخص در ایمپورت ماژول {module_path}: {str(e)}")
            
        return issues
    
    def check_core_modules(self) -> List[str]:
        """
        بررسی ماژول‌های هسته
        
        Returns:
            List[str]: لیست مشکلات یافت شده
        """
        issues = []
        logger.info("در حال بررسی ماژول‌های هسته...")
        
        for module in self.core_modules:
            module_path = f"core.{module}"
            module_issues = self.check_module_imports(module_path)
            issues.extend(module_issues)
            
        return issues
    
    def check_api_modules(self) -> List[str]:
        """
        بررسی ماژول‌های API
        
        Returns:
            List[str]: لیست مشکلات یافت شده
        """
        issues = []
        logger.info("در حال بررسی ماژول‌های API...")
        
        for module in self.api_modules:
            module_path = f"api.{module}"
            module_issues = self.check_module_imports(module_path)
            issues.extend(module_issues)
            
        return issues
    
    def check_plugin_structure(self) -> List[str]:
        """
        بررسی ساختار پلاگین‌ها
        
        Returns:
            List[str]: لیست مشکلات یافت شده
        """
        issues = []
        logger.info("در حال بررسی ساختار پلاگین‌ها...")
        
        plugins_dir = os.path.join(PROJECT_ROOT, "plugins")
        if not os.path.exists(plugins_dir):
            issues.append("❌ دایرکتوری plugins یافت نشد")
            return issues
            
        # بررسی زیردایرکتوری‌های plugins
        plugin_categories = [
            "admin", "security", "tools", "ai", "analytics", "integration"
        ]
        
        for category in plugin_categories:
            category_dir = os.path.join(plugins_dir, category)
            if not os.path.exists(category_dir):
                issues.append(f"❌ دایرکتوری پلاگین {category} یافت نشد")
            else:
                # بررسی وجود __init__.py در هر دایرکتوری پلاگین
                init_file = os.path.join(category_dir, "__init__.py")
                if not os.path.exists(init_file):
                    issues.append(f"❌ فایل __init__.py در دایرکتوری پلاگین {category} یافت نشد")
                    
        return issues
    
    def check_database_models(self) -> List[str]:
        """
        بررسی مدل‌های دیتابیس
        
        Returns:
            List[str]: لیست مشکلات یافت شده
        """
        issues = []
        logger.info("در حال بررسی مدل‌های دیتابیس...")
        
        models_dir = os.path.join(PROJECT_ROOT, "api", "models")
        if not os.path.exists(models_dir):
            issues.append("❌ دایرکتوری api/models یافت نشد")
            return issues
            
        # بررسی فایل‌های مدل
        expected_models = ["__init__.py", "user.py", "plugin.py", "license.py"]
        for model_file in expected_models:
            file_path = os.path.join(models_dir, model_file)
            if not os.path.exists(file_path):
                issues.append(f"❌ فایل مدل {model_file} یافت نشد")
                
        return issues
    
    def check_config_files(self) -> List[str]:
        """
        بررسی فایل‌های تنظیمات
        
        Returns:
            List[str]: لیست مشکلات یافت شده
        """
        issues = []
        logger.info("در حال بررسی فایل‌های تنظیمات...")
        
        # بررسی وجود فایل .env یا .env.example
        env_file = os.path.join(PROJECT_ROOT, ".env")
        env_example_file = os.path.join(PROJECT_ROOT, ".env.example")
        
        if not os.path.exists(env_file) and not os.path.exists(env_example_file):
            issues.append("❌ فایل‌های .env یا .env.example یافت نشدند")
            
        # بررسی دایرکتوری config
        config_dir = os.path.join(PROJECT_ROOT, "config")
        if not os.path.exists(config_dir):
            issues.append("❌ دایرکتوری config یافت نشد")
        else:
            # بررسی فایل‌های تنظیمات در دایرکتوری config
            expected_configs = ["app.json", "logging.json"]
            for config_file in expected_configs:
                file_path = os.path.join(config_dir, config_file)
                if not os.path.exists(file_path):
                    issues.append(f"❌ فایل تنظیمات {config_file} یافت نشد")
                    
        return issues
    
    def run_all_checks(self) -> Dict[str, Any]:
        """
        اجرای تمام بررسی‌ها
        
        Returns:
            Dict[str, Any]: نتایج بررسی‌ها
        """
        logger.info("شروع بررسی مشکلات پروژه...")
        
        # بررسی ماژول‌های هسته
        core_issues = self.check_core_modules()
        self.issues.extend(core_issues)
        
        # بررسی ماژول‌های API
        api_issues = self.check_api_modules()
        self.issues.extend(api_issues)
        
        # بررسی ساختار پلاگین‌ها
        plugin_issues = self.check_plugin_structure()
        self.issues.extend(plugin_issues)
        
        # بررسی مدل‌های دیتابیس
        model_issues = self.check_database_models()
        self.issues.extend(model_issues)
        
        # بررسی فایل‌های تنظیمات
        config_issues = self.check_config_files()
        self.issues.extend(config_issues)
        
        # تولید گزارش
        total_issues = len(self.issues)
        if total_issues == 0:
            logger.info("✅ هیچ مشکلی یافت نشد! پروژه آماده استفاده است.")
        else:
            logger.info(f"❌ {total_issues} مشکل یافت شد:")
            for i, issue in enumerate(self.issues, 1):
                logger.info(f"{i}. {issue}")
                
        return {
            "status": "success" if total_issues == 0 else "issues_found",
            "total_issues": total_issues,
            "issues": self.issues
        }
        
    def generate_report(self, output_file="debug_report.json") -> None:
        """
        تولید گزارش به فرمت JSON
        
        Args:
            output_file: نام فایل خروجی
        """
        results = self.run_all_checks()
        
        report_path = os.path.join(PROJECT_ROOT, output_file)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
            
        logger.info(f"گزارش دیباگ در {report_path} ذخیره شد")
        
        return results


if __name__ == "__main__":
    checker = DebugChecker()
    results = checker.generate_report()
    
    sys.exit(0 if results["total_issues"] == 0 else 1)
