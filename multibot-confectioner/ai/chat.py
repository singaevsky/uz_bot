import openai
from config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Установка API ключа OpenAI
openai.api_key = settings.openai_api_key
if settings.openai_org_id:
    openai.organization = settings.openai_org_id


async def generate_response(message: str, user_info: dict = None) -> str:
    """
    Генерация ответа с помощью GPT-4o-mini
    :param message: Сообщение от пользователя
    :param user_info: Информация о пользователе (возраст, пол и т.д.)
    :return: Сгенерированный ответ
    """
    try:
        # Подготовка промпта с учетом персонализации
        age = user_info.get('age') if user_info else None
        gender = user_info.get('gender') if user_info else None
        
        system_prompt = "Ты - AI-помощник кондитера. Помоги клиенту оформить заказ на торт или десерт. "
        system_prompt += "Уточни детали: вес, форму, начинку, декор, дату доставки. "
        system_prompt += "Стиль общения адаптируй под клиента. "
        
        if age:
            if age < 18:
                system_prompt += "Клиент несовершеннолетний, общайся с уважением и осторожно. "
            elif age > 60:
                system_prompt += "Клиент пожилой, общайся с уважением и терпением. "
        
        if gender:
            if gender.lower() == 'male':
                system_prompt += "Клиент мужчина. "
            elif gender.lower() == 'female':
                system_prompt += "Клиент женщина. "
        
        system_prompt += "Отвечай кратко и по существу, задавай уточняющие вопросы."

        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        return "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, повторите попытку позже."


async def analyze_order_description(description: str) -> dict:
    """
    Анализ описания заказа для извлечения ключевых параметров
    :param description: Описание заказа от пользователя
    :return: Словарь с извлеченными параметрами
    """
    try:
        prompt = f"""
        Проанализируй описание заказа на торт и извлеки следующую информацию:
        - Вес (в кг)
        - Основные ингредиенты/начинка
        - Предпочтения по декору
        - Дата доставки (если указана)
        
        Описание: {description}
        
        Ответь в формате JSON с ключами: weight, ingredients, decor, delivery_date.
        Если какая-то информация отсутствует, верни null для этого поля.
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        import json
        extracted_info = json.loads(response.choices[0].message.content.strip())
        return extracted_info
    
    except Exception as e:
        logger.error(f"Ошибка при анализе описания заказа: {e}")
        return {"weight": None, "ingredients": None, "decor": None, "delivery_date": None}