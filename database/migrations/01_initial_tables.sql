-- Migration: 01_initial_tables
-- Description: ایجاد جداول اصلی سلف بات تلگرام
-- Version: 1.0
-- ایجاد شده در: 2025-05-12

-- اطمینان از پاک شدن تغییرات نیمه‌کاره قبلی
-- NOTICE: استفاده از BEGIN, COMMIT و ROLLBACK طبق قوانین کاربر ممنوع است

-- ایجاد جدول تنظیمات
CREATE TABLE IF NOT EXISTS settings (
    id BIGSERIAL PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    value JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE settings IS 'تنظیمات عمومی سلف بات';

-- ایجاد جدول پلاگین‌ها
CREATE TABLE IF NOT EXISTS plugins (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    version TEXT NOT NULL,
    description TEXT,
    author TEXT,
    category TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE plugins IS 'اطلاعات پلاگین‌های نصب شده';

-- ایجاد جدول کاربران
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT,
    username TEXT,
    access_level TEXT NOT NULL DEFAULT 'regular',
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    last_interaction TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_user_id ON users (user_id);
CREATE INDEX IF NOT EXISTS idx_users_access_level ON users (access_level);

COMMENT ON TABLE users IS 'کاربران شناخته شده توسط سلف بات';

-- ایجاد جدول گروه‌ها
CREATE TABLE IF NOT EXISTS chats (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,
    title TEXT,
    type TEXT NOT NULL,
    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    protection_settings JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chats_chat_id ON chats (chat_id);
CREATE INDEX IF NOT EXISTS idx_chats_type ON chats (type);

COMMENT ON TABLE chats IS 'گروه‌ها و چت‌های شناخته شده توسط سلف بات';

-- ایجاد جدول پاسخ‌های خودکار
CREATE TABLE IF NOT EXISTS auto_responses (
    id BIGSERIAL PRIMARY KEY,
    trigger_pattern TEXT NOT NULL,
    response_text TEXT NOT NULL,
    is_regex BOOLEAN NOT NULL DEFAULT FALSE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    chat_scope JSONB NOT NULL DEFAULT '[]',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auto_responses_trigger ON auto_responses (trigger_pattern);
CREATE INDEX IF NOT EXISTS idx_auto_responses_enabled ON auto_responses (is_enabled);

COMMENT ON TABLE auto_responses IS 'پاسخ‌های خودکار به پیام‌های دریافتی';

-- ایجاد جدول وب‌هوک‌ها
CREATE TABLE IF NOT EXISTS webhooks (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    events JSONB NOT NULL DEFAULT '["message"]',
    secret TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhooks_name ON webhooks (name);
CREATE INDEX IF NOT EXISTS idx_webhooks_enabled ON webhooks (enabled);

COMMENT ON TABLE webhooks IS 'وب‌هوک‌های فعال برای ارسال رویدادها';

-- ایجاد جدول سرویس‌های خارجی
CREATE TABLE IF NOT EXISTS external_services (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_external_services_name ON external_services (name);
CREATE INDEX IF NOT EXISTS idx_external_services_type ON external_services (type);

COMMENT ON TABLE external_services IS 'سرویس‌های خارجی متصل به سلف بات';

-- ایجاد جدول رویدادهای امنیتی
CREATE TABLE IF NOT EXISTS security_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    source TEXT,
    event_data JSONB NOT NULL DEFAULT '{}',
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events (event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events (severity);
CREATE INDEX IF NOT EXISTS idx_security_events_created_at ON security_events (created_at);

COMMENT ON TABLE security_events IS 'رویدادهای امنیتی ثبت شده توسط سلف بات';

-- ایجاد جدول وظایف زمان‌بندی شده
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    task_type TEXT NOT NULL,
    schedule TEXT NOT NULL,
    last_run TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    task_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_name ON scheduled_tasks (name);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_enabled ON scheduled_tasks (is_enabled);

COMMENT ON TABLE scheduled_tasks IS 'وظایف زمان‌بندی شده برای اجرای خودکار';

-- ایجاد تابع به‌روزرسانی زمان
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ایجاد تریگرهای به‌روزرسانی زمان
CREATE TRIGGER update_settings_timestamp BEFORE UPDATE ON settings FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER update_plugins_timestamp BEFORE UPDATE ON plugins FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER update_users_timestamp BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER update_chats_timestamp BEFORE UPDATE ON chats FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER update_auto_responses_timestamp BEFORE UPDATE ON auto_responses FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER update_webhooks_timestamp BEFORE UPDATE ON webhooks FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER update_external_services_timestamp BEFORE UPDATE ON external_services FOR EACH ROW EXECUTE FUNCTION update_timestamp();
CREATE TRIGGER update_scheduled_tasks_timestamp BEFORE UPDATE ON scheduled_tasks FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- پایان مایگریشن
