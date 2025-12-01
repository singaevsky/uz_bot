-- Миграция для создания таблицы чатов
CREATE TABLE IF NOT EXISTS chats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    response TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ai_model VARCHAR(100), -- модель ИИ, которая сгенерировала ответ
    
    -- Индекс для быстрого поиска чатов по пользователю
    INDEX idx_chats_user_id (user_id),
    
    -- Индекс для быстрого поиска чатов по платформе
    INDEX idx_chats_platform (platform),
    
    -- Индекс для сортировки по времени
    INDEX idx_chats_timestamp (timestamp)
);

-- Таблица для хранения сессий FSM (состояний пользователей)
CREATE TABLE IF NOT EXISTS fsm_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    state VARCHAR(100) NOT NULL,
    data JSONB, -- хранение дополнительных данных состояния в формате JSON
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Уникальный индекс для предотвращения дубликатов сессий
    CONSTRAINT unique_user_platform_session UNIQUE (user_id, platform),
    
    -- Индекс для быстрого поиска сессий по пользователю и платформе
    INDEX idx_fsm_sessions_user_platform (user_id, platform)
);

-- Триггер для автоматического обновления поля updated_at для FSM сессий
CREATE TRIGGER update_fsm_sessions_updated_at 
    BEFORE UPDATE ON fsm_sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();