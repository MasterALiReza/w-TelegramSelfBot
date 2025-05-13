"""
ماژول لاگینگ مرکزی برای سلف بات تلگرام با پشتیبانی از UTF-8
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class UTF8StreamHandler(logging.StreamHandler):
    """
    کلاس هندلر جریان با پشتیبانی از UTF-8 برای کاراکترهای فارسی
    """
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


class UTF8FileHandler(logging.FileHandler):
    """
    کلاس هندلر فایل با پشتیبانی از UTF-8 برای کاراکترهای فارسی
    """
    def __init__(self, filename, mode='a', encoding='utf-8', delay=False):
        """
        مقداردهی اولیه با تنظیم پیش‌فرض encoding به utf-8
        """
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)


class UTF8RotatingFileHandler(RotatingFileHandler):
    """
    کلاس هندلر فایل چرخشی با پشتیبانی از UTF-8 برای کاراکترهای فارسی
    """
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding='utf-8', delay=False):
        """
        مقداردهی اولیه با تنظیم پیش‌فرض encoding به utf-8
        """
        RotatingFileHandler.__init__(self, filename, mode, maxBytes, backupCount, encoding, delay)


class UTF8TimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    کلاس هندلر فایل چرخشی زمانی با پشتیبانی از UTF-8 برای کاراکترهای فارسی
    """
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding='utf-8', delay=False, utc=False, atTime=None):
        """
        مقداردهی اولیه با تنظیم پیش‌فرض encoding به utf-8
        """
        TimedRotatingFileHandler.__init__(self, filename, when, interval, backupCount, encoding, delay, utc, atTime)


class Logger:
    """
    کلاس مدیریت لاگ مرکزی با پشتیبانی از UTF-8 و سینگلتون
    """
    _instance = None
    _loggers = {}

    def __new__(cls, *args, **kwargs):
        """پیاده‌سازی الگوی Singleton"""
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir=None, log_level=logging.INFO, log_format=None, console_output=True, file_output=True,
                 max_file_size=10*1024*1024, backup_count=5):
        """
        مقداردهی اولیه

        Args:
            log_dir: مسیر دایرکتوری ذخیره فایل‌های لاگ
            log_level: سطح لاگ (logging.DEBUG, logging.INFO, ...)
            log_format: فرمت لاگ
            console_output: آیا لاگ‌ها در کنسول نمایش داده شوند؟
            file_output: آیا لاگ‌ها در فایل ذخیره شوند؟
            max_file_size: حداکثر اندازه فایل لاگ قبل از چرخش (به بایت)
            backup_count: تعداد فایل‌های لاگ پشتیبان
        """
        # اگر قبلاً مقداردهی شده، خروج
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._initialized = True
        self.log_dir = log_dir or os.path.join(Path(__file__).parent.parent.absolute(), 'logs')
        self.log_level = log_level
        self.log_format = log_format or '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        self.console_output = console_output
        self.file_output = file_output
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        
        # اطمینان از وجود دایرکتوری لاگ
        if self.file_output and not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)

    def get_logger(self, name, log_file=None, level=None):
        """
        دریافت لاگر با تنظیمات خاص

        Args:
            name: نام لاگر
            log_file: نام فایل لاگ (اختیاری، پیش‌فرض: name.log)
            level: سطح لاگ (اختیاری، پیش‌فرض: سطح پیش‌فرض کلاس)

        Returns:
            logging.Logger: شیء لاگر
        """
        # اگر لاگر قبلاً ایجاد شده، بازگرداندن آن
        if name in self._loggers:
            return self._loggers[name]
        
        # ایجاد لاگر جدید
        logger = logging.getLogger(name)
        logger.setLevel(level or self.log_level)
        
        # جلوگیری از انتشار لاگ به لاگر والد
        logger.propagate = False
        
        # فرمتر لاگ
        formatter = logging.Formatter(self.log_format)
        
        # اضافه کردن هندلر کنسول
        if self.console_output:
            console_handler = UTF8StreamHandler()
            console_handler.setLevel(level or self.log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # اضافه کردن هندلر فایل
        if self.file_output:
            log_file = log_file or f"{name.replace('.', '_')}.log"
            file_path = os.path.join(self.log_dir, log_file)
            file_handler = UTF8RotatingFileHandler(
                file_path,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level or self.log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # ذخیره لاگر در دیکشنری
        self._loggers[name] = logger
        return logger


# تابع کمکی برای دسترسی سریع به لاگر
def get_logger(name=None, log_file=None, level=None):
    """
    دریافت لاگر با تنظیمات خاص

    Args:
        name: نام لاگر (اختیاری، پیش‌فرض: __name__ استفاده می‌شود)
        log_file: نام فایل لاگ (اختیاری)
        level: سطح لاگ (اختیاری)

    Returns:
        logging.Logger: شیء لاگر
    """
    # اگر نام مشخص نشده باشد، از __name__ فراخوانی کننده استفاده کن
    if name is None:
        import inspect
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        name = module.__name__
    
    logger_instance = Logger()
    return logger_instance.get_logger(name, log_file, level)
