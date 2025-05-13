"""
ماژول مدیریت تنظیمات سلف بات تلگرام
"""
import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """
    کلاس مدیریت تنظیمات برنامه
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        """پیاده‌سازی الگوی Singleton"""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, env_file: str = None, config_dir: str = None):
        """
        مقداردهی اولیه

        Args:
            env_file: مسیر فایل .env
            config_dir: مسیر دایرکتوری تنظیمات
        """
        # اگر قبلاً مقداردهی شده، خروج
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self.config_values = {}
        
        # تنظیم مسیر پروژه
        self.project_root = Path(__file__).parent.parent.absolute()
        
        # بارگذاری متغیرهای محیطی از فایل .env
        self._load_env_variables(env_file)
        
        # بارگذاری تنظیمات از فایل‌های JSON
        self._config_dir = config_dir or os.path.join(self.project_root, 'config')
        self._load_config_files()

    def _load_env_variables(self, env_file: str = None) -> None:
        """
        بارگذاری متغیرهای محیطی از فایل .env

        Args:
            env_file: مسیر فایل .env
        """
        env_path = env_file or os.path.join(self.project_root, '.env')
        
        if os.path.exists(env_path):
            logger.info(f"در حال بارگذاری متغیرهای محیطی از {env_path}")
            load_dotenv(env_path)
            
            # افزودن متغیرهای محیطی به دیکشنری تنظیمات
            for key, value in os.environ.items():
                self.config_values[key] = value
        else:
            logger.warning(f"فایل .env در مسیر {env_path} یافت نشد")

    def _load_config_files(self) -> None:
        """
        بارگذاری تنظیمات از فایل‌های JSON در دایرکتوری config
        """
        if not os.path.exists(self._config_dir):
            logger.warning(f"دایرکتوری تنظیمات {self._config_dir} یافت نشد")
            return
        
        for file_name in os.listdir(self._config_dir):
            if file_name.endswith('.json'):
                file_path = os.path.join(self._config_dir, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        
                    # افزودن تنظیمات به دیکشنری تنظیمات
                    config_name = file_name.replace('.json', '')
                    self.config_values[config_name] = config_data
                    logger.info(f"فایل تنظیمات {file_name} بارگذاری شد")
                except Exception as e:
                    logger.error(f"خطا در بارگذاری فایل تنظیمات {file_name}: {str(e)}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        دریافت مقدار تنظیمات

        Args:
            key: کلید تنظیمات
            default: مقدار پیش‌فرض در صورت عدم وجود کلید

        Returns:
            Any: مقدار تنظیمات
        """
        # ابتدا بررسی متغیرهای محیطی
        if key in os.environ:
            return os.environ[key]
        
        # سپس بررسی دیکشنری تنظیمات
        return self.config_values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        تنظیم مقدار تنظیمات

        Args:
            key: کلید تنظیمات
            value: مقدار تنظیمات
        """
        self.config_values[key] = value

    def save(self, key: str, file_name: str) -> bool:
        """
        ذخیره تنظیمات در فایل JSON

        Args:
            key: کلید تنظیمات
            file_name: نام فایل

        Returns:
            bool: وضعیت ذخیره‌سازی
        """
        if key not in self.config_values:
            logger.error(f"کلید {key} در تنظیمات یافت نشد")
            return False
        
        file_path = os.path.join(self._config_dir, f"{file_name}.json")
        try:
            # اطمینان از وجود دایرکتوری config
            os.makedirs(self._config_dir, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_values[key], f, ensure_ascii=False, indent=4)
            
            logger.info(f"تنظیمات {key} در فایل {file_name}.json ذخیره شد")
            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره تنظیمات {key}: {str(e)}")
            return False
