import openai
from config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Установка API ключа OpenAI
openai.api_key = settings.openai_api_key
if settings.openai_org_id:
    openai.organization = settings.openai_org_id


async def generate_cake_image(description: str, weight: Optional[float] = None, 
                             photo_analysis: Optional[str] = None) -> Optional[str]:
    """
    Генерация изображения торта с помощью DALL-E 3
    :param description: Описание торта
    :param weight: Вес торта в кг
    :param photo_analysis: Анализ фото-примера (если есть)
    :return: URL сгенерированного изображения
    """
    try:
        # Формирование промпта для DALL-E
        prompt = f"Реалистичный торт {description}"
        
        if weight:
            prompt += f", вес {weight} кг"
        
        if photo_analysis:
            prompt += f", в стиле {photo_analysis}"
        
        prompt += ", вид сверху, студийное освещение, высокое качество, фотореалистичный стиль"
        
        # Ограничение длины промпта для DALL-E
        if len(prompt) > 1000:
            prompt = prompt[:1000]
        
        response = await openai.Image.acreate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard"
        )
        
        image_url = response.data[0].url
        return image_url
    
    except Exception as e:
        logger.error(f"Ошибка при генерации изображения: {e}")
        return None


async def analyze_photo_style(photo_url: str) -> Optional[str]:
    """
    Анализ стиля торта по фото (псевдо-реализация, так как DALL-E не анализирует фото напрямую)
    В реальной реализации можно использовать другие модели или сервисы для анализа изображений
    :param photo_url: URL фото торта
    :return: Описание стиля
    """
    try:
        # В реальной реализации здесь будет вызов модели компьютерного зрения
        # или другого сервиса анализа изображений
        # Пока возвращаем заглушку
        return "в стиле классического французского десерта с кремом и ягодами"
    except Exception as e:
        logger.error(f"Ошибка при анализе фото: {e}")
        return None