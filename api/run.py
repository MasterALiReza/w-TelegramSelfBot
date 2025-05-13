"""
فایل راه‌اندازی سرور API سلف بات تلگرام
"""
import os
import logging
import uvicorn

# تنظیم لاگر
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("api.launcher")

if __name__ == "__main__":
    try:
        # دریافت تنظیمات از متغیرهای محیطی یا مقادیر پیش‌فرض
        host = os.environ.get("API_HOST", "0.0.0.0")
        port = int(os.environ.get("API_PORT", 8000))
        reload = os.environ.get("API_RELOAD", "False").lower() == "true"

        logger.info(f"در حال راه‌اندازی سرور API روی {host}:{port}...")

        # راه‌اندازی سرور
        uvicorn.run(
            "api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"خطا در راه‌اندازی سرور API: {str(e)}")
