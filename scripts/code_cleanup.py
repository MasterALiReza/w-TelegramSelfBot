#!/usr/bin/env python
"""
اسکریپت اصلاح خودکار مشکلات کد

این اسکریپت مشکلات پیدا شده توسط pylint را به صورت خودکار اصلاح می‌کند:
1. حذف فضاهای خالی انتهایی
2. اصلاح f-string در توابع logging
3. حذف import‌های استفاده نشده
4. اصلاح خطوط طولانی
"""

import os
import re
import sys
from pathlib import Path

# تنظیم مسیر پروژه
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
MAX_LINE_LENGTH = 100

def fix_trailing_whitespace(file_path):
    """حذف فضاهای خالی انتهایی در فایل"""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # حذف فضاهای خالی انتهایی
    fixed_content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
    
    # نوشتن محتوای اصلاح شده
    if content != fixed_content:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(fixed_content)
        return True
    
    return False

def fix_logging_fstrings(file_path):
    """تبدیل f-string در توابع logging به فرمت %s"""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # الگوی تشخیص f-string در توابع logging
    pattern = r'(logging\.[a-z]+\(f["\'].*?["\'])'
    
    def replace_fstring(match):
        log_call = match.group(1)
        # تبدیل f-string به فرمت %s
        if 'f"' in log_call or "f'" in log_call:
            # حذف f از ابتدای رشته
            if 'f"' in log_call:
                log_call = log_call.replace('f"', '"', 1)
            else:
                log_call = log_call.replace("f'", "'", 1)
                
            # جایگزینی {var} با %s
            log_call = re.sub(r'\{([^}]+)\}', '%s', log_call)
        
        return log_call
    
    fixed_content = re.sub(pattern, replace_fstring, content)
    
    # نوشتن محتوای اصلاح شده
    if content != fixed_content:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(fixed_content)
        return True
    
    return False

def fix_long_lines(file_path):
    """اصلاح خطوط طولانی با شکستن آنها"""
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    fixed_lines = []
    modified = False
    
    for line in lines:
        if len(line.rstrip('\n')) > MAX_LINE_LENGTH:
            # سعی در شکستن خطوط طولانی
            # اضافه کردن \ در انتهای خط
            if '(' in line and ')' in line and line.rindex(')') > line.rindex('('):
                # شکستن خط در پرانتزها
                parts = []
                current_part = ""
                depth = 0
                for char in line.rstrip('\n'):
                    current_part += char
                    if char == '(':
                        depth += 1
                    elif char == ')':
                        depth -= 1
                        if depth == 0 and len(current_part) > 50:  # حداقل 50 کاراکتر برای هر خط
                            parts.append(current_part)
                            current_part = ""
                
                if current_part:
                    parts.append(current_part)
                
                if len(parts) > 1:
                    # ایجاد خطوط شکسته شده
                    indent = len(line) - len(line.lstrip())
                    new_lines = [parts[0].rstrip() + " \\\n"]
                    for part in parts[1:]:
                        new_lines.append(' ' * (indent + 4) + part.strip() + " \\\n")
                    
                    fixed_lines.extend(new_lines)
                    modified = True
                    continue
            
            # اگر نتوانیم خط را بشکنیم، آن را بدون تغییر اضافه می‌کنیم
            fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    # نوشتن محتوای اصلاح شده
    if modified:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(fixed_lines)
        return True
    
    return False

def fix_unused_imports(file_path):
    """حذف import‌های استفاده نشده"""
    try:
        import autoflake
        from tempfile import NamedTemporaryFile
        
        # استفاده از autoflake برای حذف import‌های استفاده نشده
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # استفاده از نسخه موقت برای جلوگیری از تغییر فایل اصلی
        with NamedTemporaryFile(mode='w', delete=False, suffix='.py', encoding='utf-8') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # اجرای autoflake روی فایل موقت
        import subprocess
        subprocess.run([
            'autoflake',
            '--remove-all-unused-imports',
            '--remove-unused-variables',
            '--in-place',
            temp_file_path
        ])
        
        # خواندن محتوای اصلاح شده
        with open(temp_file_path, 'r', encoding='utf-8') as temp_file:
            fixed_content = temp_file.read()
            
        # حذف فایل موقت
        os.remove(temp_file_path)
        
        # نوشتن محتوای اصلاح شده
        if content != fixed_content:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(fixed_content)
            return True
        
        return False
    except ImportError:
        print("برای حذف import‌های استفاده نشده، نیاز به نصب autoflake دارید: pip install autoflake")
        return False

def fix_python_file(file_path):
    """اصلاح مشکلات یک فایل پایتون"""
    print(f"در حال اصلاح {file_path}...")
    fixes_applied = []
    
    # اعمال اصلاحات
    if fix_trailing_whitespace(file_path):
        fixes_applied.append("حذف فضاهای خالی انتهایی")
    
    if fix_logging_fstrings(file_path):
        fixes_applied.append("اصلاح f-string در توابع logging")
    
    if fix_long_lines(file_path):
        fixes_applied.append("اصلاح خطوط طولانی")
    
    if fix_unused_imports(file_path):
        fixes_applied.append("حذف import‌های استفاده نشده")
    
    if fixes_applied:
        print(f"  اصلاحات اعمال شده: {', '.join(fixes_applied)}")
    else:
        print("  بدون تغییر")
    
    return len(fixes_applied) > 0

def find_python_files(directory):
    """پیدا کردن تمام فایل‌های پایتون در یک دایرکتوری"""
    python_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    return python_files

def main():
    """تابع اصلی برنامه"""
    if len(sys.argv) > 1:
        # اصلاح فایل‌های مشخص شده
        for file_path in sys.argv[1:]:
            if os.path.isfile(file_path) and file_path.endswith('.py'):
                fix_python_file(file_path)
            else:
                print(f"خطا: {file_path} یک فایل پایتون معتبر نیست.")
    else:
        # اصلاح تمام فایل‌های پایتون در پروژه
        directories = ['core', 'api', 'plugins']
        total_files = 0
        fixed_files = 0
        
        for directory in directories:
            dir_path = os.path.join(PROJECT_ROOT, directory)
            if os.path.isdir(dir_path):
                python_files = find_python_files(dir_path)
                total_files += len(python_files)
                
                for file_path in python_files:
                    if fix_python_file(file_path):
                        fixed_files += 1
        
        print(f"\nاصلاح کامل شد: {fixed_files} از {total_files} فایل اصلاح شدند.")

if __name__ == "__main__":
    main()
