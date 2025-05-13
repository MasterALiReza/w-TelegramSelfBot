-- Migration: 02_row_level_security
-- Description: پیاده‌سازی امنیت سطح سطر (RLS) برای جداول
-- Version: 1.0
-- ایجاد شده در: 2025-05-12

-- فعال‌سازی RLS برای همه جداول

-- جدول تنظیمات
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- ایجاد سیاست برای جدول تنظیمات
-- فقط کاربران احراز هویت شده با نقش service_role می‌توانند ویرایش کنند
CREATE POLICY settings_policy ON settings
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'service_role');

-- همه کاربران احراز هویت شده می‌توانند تنظیمات را ببینند
CREATE POLICY settings_select_policy ON settings
    FOR SELECT USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- جدول پلاگین‌ها
ALTER TABLE plugins ENABLE ROW LEVEL SECURITY;

-- ایجاد سیاست برای جدول پلاگین‌ها
CREATE POLICY plugins_policy ON plugins
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY plugins_select_policy ON plugins
    FOR SELECT USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- جدول کاربران
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- ایجاد سیاست برای جدول کاربران
CREATE POLICY users_policy ON users
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY users_select_policy ON users
    FOR SELECT USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- جدول گروه‌ها
ALTER TABLE chats ENABLE ROW LEVEL SECURITY;

-- ایجاد سیاست برای جدول گروه‌ها
CREATE POLICY chats_policy ON chats
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY chats_select_policy ON chats
    FOR SELECT USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- جدول پاسخ‌های خودکار
ALTER TABLE auto_responses ENABLE ROW LEVEL SECURITY;

-- ایجاد سیاست برای جدول پاسخ‌های خودکار
CREATE POLICY auto_responses_policy ON auto_responses
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY auto_responses_select_policy ON auto_responses
    FOR SELECT USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- جدول وب‌هوک‌ها
ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;

-- ایجاد سیاست برای جدول وب‌هوک‌ها
CREATE POLICY webhooks_policy ON webhooks
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY webhooks_select_policy ON webhooks
    FOR SELECT USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- جدول سرویس‌های خارجی
ALTER TABLE external_services ENABLE ROW LEVEL SECURITY;

-- ایجاد سیاست برای جدول سرویس‌های خارجی
CREATE POLICY external_services_policy ON external_services
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY external_services_select_policy ON external_services
    FOR SELECT USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- جدول رویدادهای امنیتی
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;

-- ایجاد سیاست برای جدول رویدادهای امنیتی
CREATE POLICY security_events_policy ON security_events
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY security_events_select_policy ON security_events
    FOR SELECT USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- جدول وظایف زمان‌بندی شده
ALTER TABLE scheduled_tasks ENABLE ROW LEVEL SECURITY;

-- ایجاد سیاست برای جدول وظایف زمان‌بندی شده
CREATE POLICY scheduled_tasks_policy ON scheduled_tasks
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY scheduled_tasks_select_policy ON scheduled_tasks
    FOR SELECT USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

-- پایان مایگریشن
