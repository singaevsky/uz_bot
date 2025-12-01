"""
Модуль для управления состояниями диалога
Поскольку FSM реализован по-разному в различных библиотеках ботов,
этот модуль предоставляет общие состояния и интерфейс для управления ими
"""
from enum import Enum
from typing import Dict, Any, Optional
import json
import time

class OrderState(Enum):
    """Перечисление состояний заказа"""
    IDLE = "idle"  # Начальное состояние
    WAITING_FOR_DESCRIPTION = "waiting_for_description"  # Ожидание описания торта
    WAITING_FOR_WEIGHT = "waiting_for_weight"  # Ожидание веса
    WAITING_FOR_INGREDIENTS = "waiting_for_ingredients"  # Ожидание ингредиентов
    WAITING_FOR_DELIVERY_DATE = "waiting_for_delivery_date"  # Ожидание даты доставки
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"  # Ожидание подтверждения
    ORDER_COMPLETED = "order_completed"  # Заказ завершен

class FSM:
    """Класс для управления состояниями пользователей"""
    
    def __init__(self):
        # В реальной реализации лучше использовать Redis или базу данных
        self.user_states: Dict[str, Dict[str, Any]] = {}
        self.state_timestamps: Dict[str, float] = {}
    
    def get_state(self, user_id: str, platform: str) -> OrderState:
        """Получение текущего состояния пользователя"""
        user_key = f"{platform}:{user_id}"
        return OrderState(self.user_states.get(user_key, {}).get('state', OrderState.IDLE.value))
    
    def set_state(self, user_id: str, platform: str, state: OrderState, data: Optional[Dict[str, Any]] = None):
        """Установка состояния пользователя"""
        user_key = f"{platform}:{user_id}"
        
        if data is None:
            data = {}
        
        # Если пользователь уже был в каком-то состоянии, сохраняем его данные
        if user_key in self.user_states:
            existing_data = self.user_states[user_key].get('data', {})
            data = {**existing_data, **data}
        
        self.user_states[user_key] = {
            'state': state.value,
            'data': data
        }
        self.state_timestamps[user_key] = time.time()
    
    def update_state_data(self, user_id: str, platform: str, data: Dict[str, Any]):
        """Обновление данных состояния пользователя"""
        user_key = f"{platform}:{user_id}"
        
        if user_key not in self.user_states:
            self.user_states[user_key] = {
                'state': OrderState.IDLE.value,
                'data': data
            }
        else:
            existing_data = self.user_states[user_key].get('data', {})
            self.user_states[user_key]['data'] = {**existing_data, **data}
        
        self.state_timestamps[user_key] = time.time()
    
    def get_state_data(self, user_id: str, platform: str) -> Dict[str, Any]:
        """Получение данных состояния пользователя"""
        user_key = f"{platform}:{user_id}"
        return self.user_states.get(user_key, {}).get('data', {})
    
    def reset_state(self, user_id: str, platform: str):
        """Сброс состояния пользователя"""
        user_key = f"{platform}:{user_id}"
        if user_key in self.user_states:
            del self.user_states[user_key]
        if user_key in self.state_timestamps:
            del self.state_timestamps[user_key]
    
    def cleanup_expired_states(self, max_age: int = 3600):
        """Очистка устаревших состояний (по умолчанию за 1 час)"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.state_timestamps.items()
            if current_time - timestamp > max_age
        ]
        
        for key in expired_keys:
            if key in self.user_states:
                del self.user_states[key]
            if key in self.state_timestamps:
                del self.state_timestamps[key]

# Глобальный экземпляр FSM
fsm = FSM()