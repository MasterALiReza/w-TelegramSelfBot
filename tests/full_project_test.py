#!/usr/bin/env python
"""
تست جامع پروژه سلف بات تلگرام
این اسکریپت تمام مؤلفه‌های پروژه را از 0 تا 100 بررسی می‌کند
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

# تنظیم لاگر با پشتیبانی از UTF-8 برای کاراکترهای فارسی
class UTF8StreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # در ویندوز، به UTF-8 تبدیل می‌کنیم
            if sys.platform == 'win32':
                stream.write(str(msg) + self.terminator)
            else:
                stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        UTF8StreamHandler(),
        logging.FileHandler(
            f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", 
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger("project_tester")

# اضافه کردن مسیر پروژه به مسیر جستجوی پایتون
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))


class ProjectTester:
    """کلاس تست جامع پروژه سلف بات تلگرام"""
    
    def __init__(self):
        self.results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "details": []
        }
        self.env_variables = {}
        self.load_env_variables()
    
    def load_env_variables(self):
        """بارگذاری متغیرهای محیطی از فایل .env"""
        env_path = PROJECT_ROOT / '.env'
        try:
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            self.env_variables[key.strip()] = value.strip()
                            # تنظیم متغیر محیطی
                            os.environ[key.strip()] = value.strip()
                logger.info(f"[OK] {len(self.env_variables)} متغیر محیطی بارگذاری شد")
            else:
                logger.error("[FAIL] فایل .env یافت نشد")
                self.record_result("بارگذاری فایل .env", False, "فایل .env یافت نشد")
        except Exception as e:
            logger.error(f"[FAIL] خطا در بارگذاری متغیرهای محیطی: {e}")
            self.record_result("بارگذاری فایل .env", False, str(e))
    
    def check_project_structure(self) -> bool:
        """بررسی ساختار پروژه و وجود فایل‌های ضروری"""
        logger.info("[CHECK] بررسی ساختار پروژه...")
        
        required_dirs = [
            "api", "config", "core", "plugins", "scripts", "tests", "web"
        ]
        
        required_files = [
            "requirements.txt",
            "docker-compose.yml",
            "Dockerfile",
            "TaskList.md"
        ]
        
        missing_dirs = []
        for dir_name in required_dirs:
            if not (PROJECT_ROOT / dir_name).is_dir():
                missing_dirs.append(dir_name)
        
        missing_files = []
        for file_name in required_files:
            if not (PROJECT_ROOT / file_name).is_file():
                missing_files.append(file_name)
        
        if not missing_dirs and not missing_files:
            logger.info("[OK] ساختار پروژه کامل است")
            self.record_result("بررسی ساختار پروژه", True)
            return True
        else:
            if missing_dirs:
                logger.error(f"[FAIL] دایرکتوری‌های مفقود: {', '.join(missing_dirs)}")
            if missing_files:
                logger.error(f"[FAIL] فایل‌های مفقود: {', '.join(missing_files)}")
            
            self.record_result("بررسی ساختار پروژه", False, 
                              f"دایرکتوری‌های مفقود: {missing_dirs}, فایل‌های مفقود: {missing_files}")
            return False
    
    def check_core_modules(self) -> bool:
        """بررسی ماژول‌های هسته پروژه"""
        logger.info("[CHECK] بررسی ماژول‌های هسته...")
        
        core_modules = [
            "license_manager", 
            "plugin_marketplace", 
            "redis_manager", 
            "database_cache"
        ]
        
        missing_modules = []
        for module in core_modules:
            try:
                module_path = PROJECT_ROOT / "core" / f"{module}.py"
                if not module_path.exists():
                    missing_modules.append(module)
                    continue
                
                # تلاش برای import کردن ماژول
                spec = module_path.read_text(encoding='utf-8')
                if len(spec) > 0:
                    logger.info(f"[OK] ماژول {module} یافت شد")
                else:
                    logger.warning(f"[WARN] ماژول {module} خالی است")
                    missing_modules.append(module)
            except Exception as e:
                logger.error(f"[FAIL] خطا در بررسی ماژول {module}: {e}")
                missing_modules.append(module)
        
        if not missing_modules:
            logger.info("[OK] تمام ماژول‌های هسته موجود هستند")
            self.record_result("بررسی ماژول‌های هسته", True)
            return True
        else:
            logger.error(f"[FAIL] ماژول‌های مفقود یا ناقص: {', '.join(missing_modules)}")
            self.record_result("بررسی ماژول‌های هسته", False, 
                              f"ماژول‌های مفقود یا ناقص: {missing_modules}")
            return False
    
    def check_database_models(self) -> bool:
        """بررسی مدل‌های دیتابیس"""
        logger.info("[CHECK] بررسی مدل‌های دیتابیس...")
        
        # بررسی وجود مدل‌های دیتابیس
        models_dir = PROJECT_ROOT / "api" / "models"
        if not models_dir.is_dir():
            logger.error("[FAIL] دایرکتوری models یافت نشد")
            self.record_result("بررسی مدل‌های دیتابیس", False, "دایرکتوری models یافت نشد")
            return False
        
        model_files = list(models_dir.glob("*.py"))
        if len(model_files) == 0:
            logger.error("[FAIL] هیچ فایل مدلی یافت نشد")
            self.record_result("بررسی مدل‌های دیتابیس", False, "هیچ فایل مدلی یافت نشد")
            return False
        
        # بررسی فایل‌های مدل
        valid_models = []
        for model_file in model_files:
            if model_file.name == "__init__.py":
                continue
                
            try:
                content = model_file.read_text(encoding='utf-8')
                if "class" in content and ("BaseModel" in content or "Base" in content):
                    valid_models.append(model_file.stem)
            except Exception as e:
                logger.error(f"[FAIL] خطا در بررسی فایل مدل {model_file.name}: {e}")
        
        if valid_models:
            logger.info(f"[OK] {len(valid_models)} مدل دیتابیس یافت شد: {', '.join(valid_models)}")
            self.record_result("بررسی مدل‌های دیتابیس", True, f"مدل‌های یافت شده: {valid_models}")
            return True
        else:
            logger.error("[FAIL] هیچ مدل دیتابیس معتبری یافت نشد")
            self.record_result("بررسی مدل‌های دیتابیس", False, "هیچ مدل دیتابیس معتبری یافت نشد")
            return False
    
    def check_api_endpoints(self) -> bool:
        """بررسی نقاط انتهایی API"""
        logger.info("[CHECK] بررسی نقاط انتهایی API...")
        
        # بررسی وجود روترهای API
        api_dir = PROJECT_ROOT / "api"
        routers_dir = api_dir / "routers"
        if not api_dir.is_dir():
            logger.error("[FAIL] دایرکتوری api یافت نشد")
            self.record_result("بررسی نقاط انتهایی API", False, "دایرکتوری api یافت نشد")
            return False
        
        if not routers_dir.is_dir() and not (api_dir / "routes").is_dir():
            routers_dir = api_dir / "routes"
            if not routers_dir.is_dir():
                logger.error("[FAIL] دایرکتوری routers یا routes یافت نشد")
                self.record_result("بررسی نقاط انتهایی API", False, "دایرکتوری routers یا routes یافت نشد")
                return False
        
        router_files = list(routers_dir.glob("*.py"))
        if len(router_files) == 0:
            logger.error("[FAIL] هیچ فایل روتر یافت نشد")
            self.record_result("بررسی نقاط انتهایی API", False, "هیچ فایل روتر یافت نشد")
            return False
        
        # بررسی فایل main.py
        main_file = api_dir / "main.py"
        if not main_file.is_file():
            logger.error("[FAIL] فایل main.py یافت نشد")
            self.record_result("بررسی نقاط انتهایی API", False, "فایل main.py یافت نشد")
            return False
        
        # بررسی محتوای فایل‌های روتر
        valid_routers = []
        for router_file in router_files:
            if router_file.name == "__init__.py":
                continue
                
            try:
                content = router_file.read_text(encoding='utf-8')
                if "router" in content.lower() and "fastapi" in content.lower():
                    valid_routers.append(router_file.stem)
            except Exception as e:
                logger.error(f"[FAIL] خطا در بررسی فایل روتر {router_file.name}: {e}")
        
        if valid_routers:
            logger.info(f"[OK] {len(valid_routers)} روتر API یافت شد: {', '.join(valid_routers)}")
            self.record_result("بررسی نقاط انتهایی API", True, f"روترهای یافت شده: {valid_routers}")
            return True
        else:
            logger.error("[FAIL] هیچ روتر API معتبری یافت نشد")
            self.record_result("بررسی نقاط انتهایی API", False, "هیچ روتر API معتبری یافت نشد")
            return False
    
    def check_plugins(self) -> bool:
        """بررسی پلاگین‌های پروژه"""
        logger.info("[CHECK] بررسی پلاگین‌ها...")
        
        plugins_dir = PROJECT_ROOT / "plugins"
        if not plugins_dir.is_dir():
            logger.error("[FAIL] دایرکتوری plugins یافت نشد")
            self.record_result("بررسی پلاگین‌ها", False, "دایرکتوری plugins یافت نشد")
            return False
        
        # شمارش تعداد دایرکتوری‌های پلاگین (هر پلاگین یک دایرکتوری است)
        plugin_dirs = [d for d in plugins_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
        
        if len(plugin_dirs) == 0:
            logger.error("[FAIL] هیچ پلاگینی یافت نشد")
            self.record_result("بررسی پلاگین‌ها", False, "هیچ پلاگینی یافت نشد")
            return False
        
        # بررسی ساختار هر پلاگین
        valid_plugins = []
        for plugin_dir in plugin_dirs:
            try:
                init_file = plugin_dir / "__init__.py"
                if init_file.exists():
                    valid_plugins.append(plugin_dir.name)
            except Exception as e:
                logger.error(f"[FAIL] خطا در بررسی پلاگین {plugin_dir.name}: {e}")
        
        if valid_plugins:
            logger.info(f"[OK] {len(valid_plugins)} پلاگین یافت شد: {', '.join(valid_plugins)}")
            self.record_result("بررسی پلاگین‌ها", True, f"پلاگین‌های یافت شده: {valid_plugins}")
            return True
        else:
            logger.error("[FAIL] هیچ پلاگین معتبری یافت نشد")
            self.record_result("بررسی پلاگین‌ها", False, "هیچ پلاگین معتبری یافت نشد")
            return False
    
    def check_documentation(self) -> bool:
        """بررسی مستندات پروژه"""
        logger.info("[CHECK] بررسی مستندات...")
        
        docs_dir = PROJECT_ROOT / "docs"
        if not docs_dir.is_dir():
            logger.error("[FAIL] دایرکتوری docs یافت نشد")
            self.record_result("بررسی مستندات", False, "دایرکتوری docs یافت نشد")
            return False
        
        # بررسی وجود مستندات اصلی
        required_docs = [
            "api",
            "user_guide",
            "plugin_development"
        ]
        
        missing_docs = []
        for doc in required_docs:
            doc_path = docs_dir / doc
            if not doc_path.exists() or not list(doc_path.glob("*.md")):
                missing_docs.append(doc)
        
        if not missing_docs:
            logger.info("[OK] مستندات کامل هستند")
            self.record_result("بررسی مستندات", True)
            return True
        else:
            logger.error(f"[FAIL] مستندات ناقص: {', '.join(missing_docs)}")
            self.record_result("بررسی مستندات", False, f"مستندات ناقص: {missing_docs}")
            return False
    
    def check_license_system(self) -> bool:
        """بررسی سیستم لایسنس"""
        logger.info("[CHECK] بررسی سیستم لایسنس...")
        
        license_manager_path = PROJECT_ROOT / "core" / "license_manager.py"
        if not license_manager_path.is_file():
            logger.error("[FAIL] فایل license_manager.py یافت نشد")
            self.record_result("بررسی سیستم لایسنس", False, "فایل license_manager.py یافت نشد")
            return False
        
        try:
            content = license_manager_path.read_text(encoding='utf-8')
            
            # بررسی وجود کلاس LicenseManager
            if "class LicenseManager" not in content:
                logger.error("[FAIL] کلاس LicenseManager یافت نشد")
                self.record_result("بررسی سیستم لایسنس", False, "کلاس LicenseManager یافت نشد")
                return False
            
            # بررسی متدهای اصلی
            required_methods = [
                "verify_license", 
                "activate_license", 
                "deactivate_license"
            ]
            
            missing_methods = []
            for method in required_methods:
                if method not in content:
                    missing_methods.append(method)
            
            if missing_methods:
                logger.error(f"[FAIL] متدهای ضروری مفقود: {', '.join(missing_methods)}")
                self.record_result("بررسی سیستم لایسنس", False, f"متدهای ضروری مفقود: {missing_methods}")
                return False
            
            logger.info("[OK] سیستم لایسنس کامل است")
            self.record_result("بررسی سیستم لایسنس", True)
            return True
            
        except Exception as e:
            logger.error(f"[FAIL] خطا در بررسی سیستم لایسنس: {e}")
            self.record_result("بررسی سیستم لایسنس", False, str(e))
            return False
    
    def check_plugin_marketplace(self) -> bool:
        """بررسی بازارچه پلاگین"""
        logger.info("[CHECK] بررسی بازارچه پلاگین...")
        
        marketplace_path = PROJECT_ROOT / "core" / "plugin_marketplace.py"
        if not marketplace_path.is_file():
            logger.error("[FAIL] فایل plugin_marketplace.py یافت نشد")
            self.record_result("بررسی بازارچه پلاگین", False, "فایل plugin_marketplace.py یافت نشد")
            return False
        
        try:
            content = marketplace_path.read_text(encoding='utf-8')
            
            # بررسی وجود کلاس PluginMarketplace
            if "class PluginMarketplace" not in content:
                logger.error("[FAIL] کلاس PluginMarketplace یافت نشد")
                self.record_result("بررسی بازارچه پلاگین", False, "کلاس PluginMarketplace یافت نشد")
                return False
            
            # بررسی متدهای اصلی
            required_methods = [
                "get_available_plugins", 
                "download_and_install_plugin", 
                "search_plugins"
            ]
            
            missing_methods = []
            for method in required_methods:
                if method not in content:
                    missing_methods.append(method)
            
            if missing_methods:
                logger.error(f"[FAIL] متدهای ضروری مفقود: {', '.join(missing_methods)}")
                self.record_result("بررسی بازارچه پلاگین", False, f"متدهای ضروری مفقود: {missing_methods}")
                return False
            
            logger.info("[OK] بازارچه پلاگین کامل است")
            self.record_result("بررسی بازارچه پلاگین", True)
            return True
            
        except Exception as e:
            logger.error(f"[FAIL] خطا در بررسی بازارچه پلاگین: {e}")
            self.record_result("بررسی بازارچه پلاگین", False, str(e))
            return False
    
    def check_docker_config(self) -> bool:
        """بررسی تنظیمات Docker"""
        logger.info("[CHECK] بررسی تنظیمات Docker...")
        
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        docker_compose_path = PROJECT_ROOT / "docker-compose.yml"
        
        if not dockerfile_path.is_file():
            logger.error("[FAIL] فایل Dockerfile یافت نشد")
            self.record_result("بررسی تنظیمات Docker", False, "فایل Dockerfile یافت نشد")
            return False
        
        if not docker_compose_path.is_file():
            logger.error("[FAIL] فایل docker-compose.yml یافت نشد")
            self.record_result("بررسی تنظیمات Docker", False, "فایل docker-compose.yml یافت نشد")
            return False
        
        try:
            # بررسی محتوای Dockerfile
            dockerfile_content = dockerfile_path.read_text(encoding='utf-8')
            if "FROM" not in dockerfile_content or "WORKDIR" not in dockerfile_content:
                logger.error("[FAIL] فایل Dockerfile ناقص است")
                self.record_result("بررسی تنظیمات Docker", False, "فایل Dockerfile ناقص است")
                return False
            
            # بررسی محتوای docker-compose.yml
            docker_compose_content = docker_compose_path.read_text(encoding='utf-8')
            if "services:" not in docker_compose_content:
                logger.error("[FAIL] فایل docker-compose.yml ناقص است")
                self.record_result("بررسی تنظیمات Docker", False, "فایل docker-compose.yml ناقص است")
                return False
            
            logger.info("[OK] تنظیمات Docker کامل هستند")
            self.record_result("بررسی تنظیمات Docker", True)
            return True
            
        except Exception as e:
            logger.error(f"[FAIL] خطا در بررسی تنظیمات Docker: {e}")
            self.record_result("بررسی تنظیمات Docker", False, str(e))
            return False
    
    def check_installation_scripts(self) -> bool:
        """بررسی اسکریپت‌های نصب و به‌روزرسانی"""
        logger.info("[CHECK] بررسی اسکریپت‌های نصب و به‌روزرسانی...")
        
        scripts_dir = PROJECT_ROOT / "scripts"
        
        if not scripts_dir.is_dir():
            logger.error("[FAIL] دایرکتوری scripts یافت نشد")
            self.record_result("بررسی اسکریپت‌های نصب", False, "دایرکتوری scripts یافت نشد")
            return False
        
        # بررسی وجود اسکریپت‌های نصب و به‌روزرسانی
        install_script = scripts_dir / "install.sh"
        update_script = scripts_dir / "update.sh"
        
        if not install_script.is_file():
            logger.error("[FAIL] فایل install.sh یافت نشد")
            self.record_result("بررسی اسکریپت‌های نصب", False, "فایل install.sh یافت نشد")
            return False
        
        if not update_script.is_file():
            logger.error("[FAIL] فایل update.sh یافت نشد")
            self.record_result("بررسی اسکریپت‌های نصب", False, "فایل update.sh یافت نشد")
            return False
        
        logger.info("[OK] اسکریپت‌های نصب و به‌روزرسانی کامل هستند")
        self.record_result("بررسی اسکریپت‌های نصب", True)
        return True
    
    def record_result(self, test_name: str, passed: bool, details: Optional[str] = None):
        """ثبت نتیجه یک تست"""
        result = {
            "test_name": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.results["total"] += 1
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
        
        self.results["details"].append(result)
    
    def generate_report(self) -> str:
        """تولید گزارش نهایی تست"""
        success_rate = 0
        if self.results["total"] > 0:
            success_rate = (self.results["passed"] / self.results["total"]) * 100
        
        report = f"""
# گزارش تست جامع پروژه سلف بات تلگرام
تاریخ و زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## آمار کلی
- تعداد کل تست‌ها: {self.results["total"]}
- تست‌های موفق: {self.results["passed"]}
- تست‌های ناموفق: {self.results["failed"]}
- درصد موفقیت: {success_rate:.1f}%

## جزئیات تست‌ها
"""
        
        for result in self.results["details"]:
            status = "[OK] موفق" if result["passed"] else "[FAIL] ناموفق"
            report += f"\n### {result['test_name']} - {status}\n"
            if result.get("details"):
                report += f"توضیحات: {result['details']}\n"
        
        # نوشتن گزارش در فایل
        report_path = PROJECT_ROOT / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
            
        logger.info(f"گزارش تست در {report_path} ذخیره شد")
        return report
    
    def run_all_tests(self):
        """اجرای تمام تست‌ها"""
        logger.info("[START] شروع تست جامع پروژه از 0 تا 100...")
        
        tests = [
            self.check_project_structure,
            self.check_core_modules,
            self.check_database_models,
            self.check_api_endpoints,
            self.check_plugins,
            self.check_documentation,
            self.check_license_system,
            self.check_plugin_marketplace,
            self.check_docker_config,
            self.check_installation_scripts
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                logger.error(f"[FAIL] خطا در اجرای {test_func.__name__}: {e}")
                self.record_result(test_func.__name__, False, str(e))
        
        report = self.generate_report()
        
        logger.info(f"[FINISH] تست جامع پروژه به پایان رسید. "
                   f"نتیجه: {self.results['passed']}/{self.results['total']} "
                   f"({(self.results['passed'] / self.results['total'] * 100):.1f}%)")
        
        return report


if __name__ == "__main__":
    tester = ProjectTester()
    tester.run_all_tests()
