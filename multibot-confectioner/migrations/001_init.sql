-- Миграция для создания таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    platform_user_id VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    age INTEGER,
    gender VARCHAR(20), -- 'male', 'female', 'other'
    phone VARCHAR(50),
    email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Уникальный индекс для предотвращения дубликатов пользователей на одной платформе
    CONSTRAINT unique_platform_user UNIQUE (platform, platform_user_id)
);

-- Создание индекса для быстрого поиска пользователей по платформе и ID
CREATE INDEX IF NOT EXISTS idx_users_platform_user_id ON users(platform, platform_user_id);

-- Триггер для автоматического обновления поля updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();