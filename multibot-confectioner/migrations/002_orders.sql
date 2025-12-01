-- Миграция для создания таблицы заказов
CREATE TABLE IF NOT EXISTS orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    weight DECIMAL(4,2), -- до 99.99 кг
    ingredients TEXT[], -- массив ингредиентов
    delivery_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL, -- 'pending', 'confirmed', 'in_progress', 'completed', 'cancelled'
    price DECIMAL(10,2),
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Индекс для быстрого поиска заказов по пользователю
    INDEX idx_orders_user_id (user_id),
    
    -- Индекс для быстрого поиска заказов по статусу
    INDEX idx_orders_status (status),
    
    -- Индекс для быстрого поиска заказов по дате доставки
    INDEX idx_orders_delivery_date (delivery_date)
);

-- Триггер для автоматического обновления поля updated_at
CREATE TRIGGER update_orders_updated_at 
    BEFORE UPDATE ON orders 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();