-- Migration: Create Base Tables
-- Description: ایجاد جداول پایه برای سلف بات تلگرام
-- Timestamp: 1747096500

-- ایجاد جدول کاربران
CREATE TABLE IF NOT EXISTS public.users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone_number VARCHAR(20),
    access_level VARCHAR(20) DEFAULT 'user',
    is_admin BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ایجاد جدول گروه‌ها
CREATE TABLE IF NOT EXISTS public.chats (
    id BIGINT PRIMARY KEY,
    title VARCHAR(255),
    type VARCHAR(20) CHECK (type IN ('private', 'group', 'supergroup', 'channel')),
    is_managed BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ایجاد جدول پلاگین‌ها
CREATE TABLE IF NOT EXISTS public.plugins (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    author VARCHAR(100),
    category VARCHAR(50),
    is_enabled BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ایجاد جدول دستورات
CREATE TABLE IF NOT EXISTS public.commands (
    id SERIAL PRIMARY KEY,
    plugin_id INTEGER REFERENCES public.plugins(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    usage TEXT,
    cooldown INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (plugin_id, name)
);

-- ایجاد جدول پیام‌های زمان‌بندی شده
CREATE TABLE IF NOT EXISTS public.scheduled_messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES public.users(id),
    chat_id BIGINT REFERENCES public.chats(id),
    message TEXT NOT NULL,
    schedule_type VARCHAR(20) CHECK (schedule_type IN ('once', 'interval', 'cron')),
    schedule_data JSONB NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ایجاد جدول پاسخ‌های خودکار
CREATE TABLE IF NOT EXISTS public.auto_responses (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES public.users(id),
    trigger_type VARCHAR(20) CHECK (trigger_type IN ('text', 'regex', 'command')),
    trigger_value TEXT NOT NULL,
    response_text TEXT NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ایجاد جدول تنظیمات
CREATE TABLE IF NOT EXISTS public.settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ایجاد جدول تاریخچه پیام‌ها
CREATE TABLE IF NOT EXISTS public.message_history (
    id SERIAL PRIMARY KEY,
    message_id BIGINT,
    user_id BIGINT REFERENCES public.users(id),
    chat_id BIGINT REFERENCES public.chats(id),
    message_type VARCHAR(20),
    content TEXT,
    is_outgoing BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ایجاد جدول مهاجرت‌ها
CREATE TABLE IF NOT EXISTS public.migrations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    plugin_name VARCHAR(100),
    batch INTEGER NOT NULL,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- تنظیم RLS برای جداول
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.plugins ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scheduled_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auto_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.migrations ENABLE ROW LEVEL SECURITY;

-- سیاست دسترسی پایه (فقط برای حساب‌های تایید شده)
CREATE POLICY "Auth Users Only" 
ON public.users FOR ALL
USING (auth.role() = 'authenticated');

CREATE POLICY "Auth Users Only" 
ON public.chats FOR ALL
USING (auth.role() = 'authenticated');

CREATE POLICY "Auth Users Only" 
ON public.plugins FOR ALL
USING (auth.role() = 'authenticated');

CREATE POLICY "Auth Users Only" 
ON public.commands FOR ALL
USING (auth.role() = 'authenticated');

CREATE POLICY "Auth Users Only" 
ON public.scheduled_messages FOR ALL
USING (auth.role() = 'authenticated');

CREATE POLICY "Auth Users Only" 
ON public.auto_responses FOR ALL
USING (auth.role() = 'authenticated');

CREATE POLICY "Auth Users Only" 
ON public.settings FOR ALL
USING (auth.role() = 'authenticated');

CREATE POLICY "Auth Users Only" 
ON public.message_history FOR ALL
USING (auth.role() = 'authenticated');

CREATE POLICY "Auth Users Only" 
ON public.migrations FOR ALL
USING (auth.role() = 'authenticated');

-- افزودن مقادیر پیش‌فرض به جدول تنظیمات
INSERT INTO public.settings (key, value, description)
VALUES 
('language', '"fa"', 'زبان پیش‌فرض سیستم'),
('message_history_days', '30', 'تعداد روزهای نگهداری تاریخچه پیام‌ها'),
('auto_response_enabled', 'true', 'فعال‌سازی پاسخ خودکار'),
('auto_backup_enabled', 'true', 'فعال‌سازی پشتیبان‌گیری خودکار');
