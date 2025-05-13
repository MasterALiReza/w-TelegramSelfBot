-- Migration: 03_default_data
-- Description: افزودن داده‌های پیش‌فرض به جداول
-- Version: 1.0
-- ایجاد شده در: 2025-05-12

-- وارد کردن تنظیمات پیش‌فرض
INSERT INTO settings (key, value, description) VALUES
('language', '"fa"', 'زبان پیش‌فرض سلف بات'),
('auto_delete_messages', 'false', 'حذف خودکار پیام‌ها پس از مدت مشخص'),
('auto_delete_interval', '3600', 'فاصله زمانی حذف خودکار پیام‌ها (ثانیه)'),
('security_level', '"medium"', 'سطح امنیتی پیش‌فرض (low, medium, high)'),
('notification_enabled', 'true', 'فعال‌سازی اعلان‌ها'),
('analytics_enabled', 'true', 'فعال‌سازی تحلیل‌ها'),
('log_level', '"info"', 'سطح لاگ سیستم (debug, info, warning, error)'),
('max_parallel_tasks', '5', 'حداکثر تعداد وظایف همزمان'),
('admin_chat_id', 'null', 'شناسه چت مدیر اصلی')
ON CONFLICT (key) DO NOTHING;

-- وارد کردن پلاگین‌های پیش‌فرض
INSERT INTO plugins (name, version, description, author, category, is_enabled, config) VALUES
('BotManager', '1.0.0', 'مدیریت عملیات اصلی ربات', 'SelfBot Team', 'admin', true, '{}'),
('UserManager', '1.0.0', 'مدیریت کاربران و سطوح دسترسی', 'SelfBot Team', 'admin', true, '{}'),
('AccountProtection', '1.0.0', 'محافظت از حساب کاربری و گروه‌ها', 'SelfBot Team', 'security', true, '{}'),
('SecurityEvents', '1.0.0', 'ثبت و مدیریت رویدادهای امنیتی', 'SelfBot Team', 'security', true, '{}'),
('AutoResponder', '1.0.0', 'پاسخ خودکار به پیام‌ها', 'SelfBot Team', 'tools', true, '{}'),
('OpenAIInterface', '1.0.0', 'رابط ارتباطی با OpenAI', 'SelfBot Team', 'ai', true, '{}'),
('ImageGenerator', '1.0.0', 'تولید تصاویر با هوش مصنوعی', 'SelfBot Team', 'ai', true, '{}'),
('ActivityTracker', '1.0.0', 'ردیابی و تحلیل فعالیت‌ها', 'SelfBot Team', 'analytics', true, '{}'),
('CommunicationAnalyzer', '1.0.0', 'تحلیل الگوهای ارتباطی', 'SelfBot Team', 'analytics', true, '{}'),
('WebhookManager', '1.0.0', 'مدیریت وب‌هوک‌ها', 'SelfBot Team', 'integration', true, '{}'),
('ExternalServicesConnector', '1.0.0', 'اتصال به سرویس‌های خارجی', 'SelfBot Team', 'integration', true, '{}')
ON CONFLICT (name) DO NOTHING;

-- وارد کردن یک کاربر مدیر پیش‌فرض
INSERT INTO users (user_id, first_name, last_name, username, access_level, is_admin, metadata) VALUES
(0, 'Admin', 'User', 'admin', 'admin', true, '{"note": "این یک کاربر موقت است. لطفاً با کاربر واقعی جایگزین شود."}')
ON CONFLICT (user_id) DO NOTHING;

-- وارد کردن چند پاسخ خودکار نمونه
INSERT INTO auto_responses (trigger_pattern, response_text, is_regex, is_enabled) VALUES
('سلام', 'سلام! چطور می‌توانم کمک کنم؟', false, true),
('بات', 'من یک سلف بات تلگرام هستم.', false, true),
('راهنما', 'برای دیدن راهنمای دستورات از `.help` استفاده کنید.', false, true),
('!help', 'برای دیدن راهنمای دستورات از `.help` استفاده کنید.', false, true)
ON CONFLICT DO NOTHING;

-- ایجاد یک وظیفه زمان‌بندی شده پیش‌فرض
INSERT INTO scheduled_tasks (name, task_type, schedule, is_enabled, task_data) VALUES
('daily_backup', 'backup', '0 0 * * *', true, '{"target": "settings", "format": "json"}'),
('clean_old_logs', 'cleanup', '0 1 * * *', true, '{"days_old": 7, "target": "logs"}')
ON CONFLICT (name) DO NOTHING;

-- پایان مایگریشن
