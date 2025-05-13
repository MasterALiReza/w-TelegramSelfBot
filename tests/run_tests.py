#!/usr/bin/env python
"""
اسکریپت اجرای خودکار تست‌های پروژه سلف بات تلگرام
"""
import os
import sys
import argparse
import subprocess
import datetime
import logging

# تنظیم لاگر
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("test_runner")


def setup_test_environment():
    """آماده‌سازی محیط برای اجرای تست‌ها"""
    # تنظیم متغیرهای محیطی
    os.environ["APP_ENV"] = "test"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_PASSWORD"] = ""
    os.environ["SUPABASE_URL"] = "http://localhost:54321"
    os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
    os.environ["SECRET_KEY"] = "test_secret_key_for_tests"
    os.environ["CRYPTO_KEY"] = "test_encryption_key_for_tests"
    
    logger.info("محیط تست آماده شد")


def run_test_command(command, label):
    """اجرای دستور تست و بررسی نتیجه"""
    logger.info(f"در حال اجرای {label}...")
    
    try:
        # اجرای دستور تست
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        # بررسی نتیجه
        if result.returncode == 0:
            logger.info(f"{label} با موفقیت اجرا شد.")
            return True, result.stdout
        else:
            logger.error(f"{label} با خطا مواجه شد.")
            logger.error(f"خروجی خطا: {result.stderr}")
            return False, result.stderr
    
    except Exception as e:
        logger.error(f"خطا در اجرای {label}: {str(e)}")
        return False, str(e)


def generate_report(results, output_dir=None):
    """تولید گزارش نتایج تست‌ها"""
    # تنظیم دایرکتوری خروجی
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "reports")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # ایجاد نام فایل گزارش
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f"test_report_{timestamp}.txt")
    
    # ایجاد متن گزارش
    report = f"گزارش اجرای تست - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    report += "=" * 80 + "\n\n"
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - passed_tests
    
    report += f"تعداد کل تست‌ها: {total_tests}\n"
    report += f"تست‌های موفق: {passed_tests}\n"
    report += f"تست‌های ناموفق: {failed_tests}\n\n"
    
    report += "جزئیات اجرای تست‌ها:\n"
    report += "=" * 80 + "\n\n"
    
    for result in results:
        status = "✅ موفق" if result["success"] else "❌ ناموفق"
        report += f"{result['name']} - {status}\n"
        if not result["success"]:
            report += f"خروجی خطا:\n{result['output']}\n\n"
    
    # نوشتن گزارش در فایل
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info(f"گزارش تست در فایل {report_file} ذخیره شد")
    return report_file


def main():
    """تابع اصلی اجرای تست‌ها"""
    parser = argparse.ArgumentParser(description="اجرای خودکار تست‌های پروژه سلف بات تلگرام")
    parser.add_argument("--unit", action="store_true", help="اجرای تست‌های واحد")
    parser.add_argument("--integration", action="store_true", help="اجرای تست‌های یکپارچه‌سازی")
    parser.add_argument("--e2e", action="store_true", help="اجرای تست‌های End-to-End")
    parser.add_argument("--all", action="store_true", help="اجرای تمام تست‌ها")
    parser.add_argument("--output", help="مسیر ذخیره گزارش تست")
    parser.add_argument("--coverage", action="store_true", help="تولید گزارش پوشش کد")
    
    args = parser.parse_args()
    
    # آماده‌سازی محیط
    setup_test_environment()
    
    # تنظیم دستورات تست
    results = []
    
    # اجرای تست‌های واحد
    if args.unit or args.all:
        success, output = run_test_command(
            "python -m pytest tests/unit/ -v",
            "تست‌های واحد"
        )
        results.append({
            "name": "تست‌های واحد",
            "success": success,
            "output": output
        })
    
    # اجرای تست‌های یکپارچه‌سازی
    if args.integration or args.all:
        success, output = run_test_command(
            "python -m pytest tests/integration/ -v",
            "تست‌های یکپارچه‌سازی"
        )
        results.append({
            "name": "تست‌های یکپارچه‌سازی",
            "success": success,
            "output": output
        })
    
    # اجرای تست‌های End-to-End
    if args.e2e or args.all:
        success, output = run_test_command(
            "python -m pytest tests/e2e/ -v",
            "تست‌های End-to-End"
        )
        results.append({
            "name": "تست‌های End-to-End",
            "success": success,
            "output": output
        })
    
    # اجرای تست پوشش کد
    if args.coverage:
        success, output = run_test_command(
            "python -m pytest tests/ --cov=core --cov=api --cov-report=html",
            "تست پوشش کد"
        )
        results.append({
            "name": "تست پوشش کد",
            "success": success,
            "output": output
        })
    
    # تولید گزارش
    if results:
        report_file = generate_report(results, args.output)
        logger.info(f"گزارش در فایل {report_file} ذخیره شد")
    else:
        logger.error("هیچ تستی اجرا نشد. از --unit، --integration، --e2e، یا --all استفاده کنید.")
        return 1
    
    # تعیین وضعیت خروجی
    if all(result["success"] for result in results):
        logger.info("تمام تست‌ها با موفقیت انجام شد")
        return 0
    else:
        logger.error("برخی از تست‌ها با خطا مواجه شدند")
        return 1


if __name__ == "__main__":
    sys.exit(main())
