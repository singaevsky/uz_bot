"""
Вспомогательные функции для проекта AI-помощника кондитера
"""
import re
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def extract_weight_from_text(text: str) -> Optional[float]:
    """
    Извлечение веса из текста
    :param text: Текст, из которого нужно извлечь вес
    :return: Вес в килограммах или None, если не найден
    """
    # Регулярное выражение для поиска чисел с возможной запятой или точкой
    # и возможным указанием единиц измерения (кг, г, etc.)
    patterns = [
        r'(\d+[,\.]?\d*)\s*кг',  # Поиск числа с последующим "кг"
        r'(\d+[,\.]?\d*)\s*kg',  # Поиск числа с последующим "kg"
        r'(\d+[,\.]?\d*)\s*г',   # Поиск числа с последующим "г", затем преобразуем в кг
        r'(\d+[,\.]?\d*)\s*g',   # Поиск числа с последующим "g", затем преобразуем в кг
        r'(\d+[,\.]?\d*)'        # Просто число (предполагаем, что это кг)
    ]
    
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            try:
                weight = float(matches[0].replace(',', '.'))
                
                # Если нашли граммы, конвертируем в килограммы
                if i in [2, 3]:  # Это были граммы
                    weight = weight / 1000.0
                
                return weight
            except ValueError:
                continue
    
    return None

def extract_date_from_text(text: str) -> Optional[datetime]:
    """
    Извлечение даты из текста
    :param text: Текст, из которого нужно извлечь дату
    :return: Дата или None, если не найдена
    """
    # Регулярные выражения для различных форматов дат
    date_patterns = [
        r'(\d{1,2})\.(\d{1,2})\.(\d{4})',    # DD.MM.YYYY
        r'(\d{1,2})-(\d{1,2})-(\d{4})',     # DD-MM-YYYY
        r'(\d{1,2})/(\d{1,2})/(\d{4})',     # DD/MM/YYYY
        r'(\d{4})-(\d{1,2})-(\d{1,2})',     # YYYY-MM-DD
        r'(\d{1,2})\.(\d{1,2})\.(\d{2})',   # DD.MM.YY
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                match = matches[0]
                
                # Если год в формате YY, преобразуем в YYYY
                if len(match[2]) == 2:
                    year = int('20' + match[2])
                else:
                    year = int(match[2])
                
                month = int(match[1])
                day = int(match[0])
                
                return datetime(year, month, day)
            except ValueError:
                continue
    
    return None

def extract_ingredients_from_text(text: str) -> list:
    """
    Извлечение ингредиентов из текста
    :param text: Текст, из которого нужно извлечь ингредиенты
    :return: Список ингредиентов
    """
    # В реальной реализации можно использовать NLP для более точного извлечения
    # Пока что просто возвращаем все слова, которые могут быть ингредиентами
    
    # Пример простого подхода - извлечение ключевых слов
    ingredients_keywords = [
        'шоколад', 'вишня', 'клубника', 'крем', 'орехи', 'изюм', 'масло', 
        'сметана', 'творог', 'яйца', 'мука', 'сахар', 'ваниль', 'какао',
        'малина', 'черника', 'лимон', 'апельсин', 'кокос', 'миндаль',
        'фундук', 'кешью', 'фисташки', 'сливки', 'повидло', 'джем'
    ]
    
    text_lower = text.lower()
    found_ingredients = []
    
    for ingredient in ingredients_keywords:
        if ingredient in text_lower:
            found_ingredients.append(ingredient)
    
    return found_ingredients

def format_order_description(description: str, weight: Optional[float] = None, 
                           ingredients: Optional[list] = None, 
                           delivery_date: Optional[datetime] = None) -> str:
    """
    Форматирование описания заказа для отображения
    :param description: Основное описание
    :param weight: Вес
    :param ingredients: Ингредиенты
    :param delivery_date: Дата доставки
    :return: Форматированное описание
    """
    formatted_parts = [description]
    
    if weight:
        formatted_parts.append(f"Вес: {weight} кг")
    
    if ingredients and len(ingredients) > 0:
        formatted_parts.append(f"Ингредиенты: {', '.join(ingredients)}")
    
    if delivery_date:
        formatted_parts.append(f"Дата доставки: {delivery_date.strftime('%d.%m.%Y')}")
    
    return "\n".join(formatted_parts)

def validate_phone_number(phone: str) -> bool:
    """
    Проверка формата номера телефона
    :param phone: Номер телефона
    :return: True если формат правильный, иначе False
    """
    # Простая проверка формата российского номера телефона
    pattern = r'^(\+7|8)[\s-]?\(?(\d{3})\)?[\s-]?(\d{3})[\s-]?(\d{2})[\s-]?(\d{2})$'
    return bool(re.match(pattern, phone))

def validate_email(email: str) -> bool:
    """
    Проверка формата email
    :param email: Email
    :return: True если формат правильный, иначе False
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def sanitize_input(text: str) -> str:
    """
    Очистка пользовательского ввода от потенциально опасного содержимого
    :param text: Входной текст
    :return: Очищенный текст
    """
    # Удаление потенциально опасных символов или последовательностей
    # В реальной реализации может потребоваться более тщательная очистка
    sanitized = text.strip()
    
    # Защита от SQL-инъекций и XSS (базовая)
    dangerous_chars = ['<', '>', '"', "'", ';', '--', '/*', '*/']
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    return sanitized

def normalize_platform_name(platform: str) -> str:
    """
    Нормализация названия платформы
    :param platform: Название платформы
    :return: Нормализованное название
    """
    platform_map = {
        'telegram': 'telegram',
        'tg': 'telegram',
        'телеграм': 'telegram',
        'телега': 'telegram',
        
        'vkontakte': 'vk',
        'vk': 'vk',
        'вконтакте': 'vk',
        'вк': 'vk',
        
        'avito': 'avito',
        'авито': 'avito',
        'aвито': 'avito'
    }
    
    normalized = platform.lower().strip()
    return platform_map.get(normalized, normalized)