import requests
from config import settings
from ai.chat import generate_response, analyze_order_description
from ai.image_gen import generate_cake_image
from database.crud import create_user, get_user_by_platform_id, create_order, create_chat
import threading
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Глобальные переменные для хранения токенов
access_token = None
expires_in = None
last_token_refresh = None

# Словарь для хранения состояний пользователей (в реальной реализации лучше использовать Redis или базу данных)
user_states = {}

def setup_avito_bot():
    """Инициализация Avito бота"""
    global access_token, last_token_refresh
    
    try:
        # Получаем токен при инициализации
        refresh_avito_token()
        
        logger.info("Avito бот инициализирован")
        
        # Запускаем обработку сообщений в отдельном потоке
        thread = threading.Thread(target=process_avito_messages)
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        logger.error(f"Ошибка инициализации Avito бота: {e}")
        raise

def refresh_avito_token():
    """Обновление токена Avito"""
    global access_token, expires_in, last_token_refresh
    
    try:
        url = "https://api.avito.ru/oauth/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': settings.avito_client_id,
            'client_secret': settings.avito_client_secret
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data['access_token']
        expires_in = token_data['expires_in']
        last_token_refresh = time.time()
        
        logger.info("Токен Avito успешно обновлен")
        
    except Exception as e:
        logger.error(f"Ошибка обновления токена Avito: {e}")
        raise

def check_token_validity():
    """Проверка валидности токена"""
    global last_token_refresh
    
    if last_token_refresh is None:
        return False
    
    # Обновляем токен за 10 минут до истечения
    if time.time() - last_token_refresh >= (expires_in - 600):
        refresh_avito_token()
        return True
    
    return True

def get_headers():
    """Получение заголовков для запросов к Avito API"""
    check_token_validity()
    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

def process_avito_messages():
    """Обработка сообщений от Avito в отдельном потоке"""
    try:
        while True:
            try:
                # Получаем новые сообщения
                messages = get_new_messages()
                
                for message in messages:
                    handle_message(message)
                
                # Пауза между запросами (чтобы не превышать лимиты API)
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Ошибка обработки сообщений Avito: {e}")
                time.sleep(60)  # Пауза перед повторной попыткой
                
    except Exception as e:
        logger.error(f"Критическая ошибка в процессе обработки сообщений Avito: {e}")

def get_new_messages() -> list:
    """Получение новых сообщений от Avito"""
    try:
        headers = get_headers()
        
        # URL для получения сообщений (в реальной реализации нужно использовать правильный endpoint)
        # Это пример - в реальности нужно использовать соответствующий API endpoint
        url = "https://api.avito.ru/messenger/v1/accounts/messages"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        messages = response.json()
        
        # Возвращаем только новые сообщения (в реальной реализации нужно отслеживать уже обработанные сообщения)
        return messages.get('messages', [])
        
    except Exception as e:
        logger.error(f"Ошибка получения сообщений от Avito: {e}")
        return []

def handle_message(message_data):
    """Обработка сообщения от Avito"""
    try:
        # Извлекаем информацию из сообщения
        user_id = str(message_data.get('user_id', ''))
        message_text = message_data.get('text', '')
        conversation_id = message_data.get('conversation_id', '')
        
        # Проверяем, есть ли пользователь в базе
        user = get_user_by_platform_id_sync("avito", user_id)
        
        if not user:
            # Создаем нового пользователя
            user_data = {
                "platform": "avito",
                "platform_user_id": user_id,
            }
            user = create_user_sync(user_data)
        
        # Сохраняем сообщение в чат
        create_chat_sync({
            "user_id": user.id,
            "platform": "avito",
            "message": message_text,
            "ai_model": "user"
        })
        
        # Получаем текущее состояние пользователя
        current_state = user_states.get(user_id)
        
        # Проверяем, является ли сообщение инициацией нового заказа
        if any(word in message_text.lower() for word in ['торт', 'десерт', 'заказ', 'хочу', 'нужен']):
            # Начинаем новый заказ
            user_states[user_id] = 'waiting_for_description'
            
            # Отправляем приветственное сообщение
            welcome_text = (
                "🎂 Спасибо за обращение! Я AI-помощник кондитерской.\n\n"
                "Давайте оформим ваш заказ на торт или десерт. "
                "Опишите, какой торт вы хотите?"
            )
            
            send_message_to_avito(conversation_id, welcome_text)
            return
        
        # Обработка в зависимости от состояния
        if current_state == 'waiting_for_description':
            handle_description(user, user_id, conversation_id, message_text)
        elif current_state == 'waiting_for_weight':
            handle_weight(user, user_id, conversation_id, message_text)
        elif current_state == 'waiting_for_ingredients':
            handle_ingredients(user, user_id, conversation_id, message_text)
        elif current_state == 'waiting_for_delivery_date':
            handle_delivery_date(user, user_id, conversation_id, message_text)
        elif current_state == 'waiting_for_confirmation':
            handle_confirmation(user, user_id, conversation_id, message_text)
        else:
            # Если состояние не установлено, отвечаем с помощью AI
            response = generate_response_sync(message_text, {
                "age": user.age if user else None,
                "gender": user.gender if user else None
            })
            
            # Сохраняем ответ в чат
            create_chat_sync({
                "user_id": user.id,
                "platform": "avito",
                "message": message_text,
                "response": response,
                "ai_model": "gpt-4o-mini"
            })
            
            # Отправляем ответ пользователю
            send_message_to_avito(conversation_id, response)
    
    except Exception as e:
        logger.error(f"Ошибка в handle_message: {e}")
        send_message_to_avito(message_data.get('conversation_id', ''), "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_description(user, user_id, conversation_id, message_text):
    """Обработка описания торта"""
    try:
        # Анализируем описание заказа
        order_info = analyze_order_description_sync(message_text)
        
        # Сохраняем информацию в состоянии
        user_states[user_id] = {
            'description': message_text,
            'weight': order_info.get('weight'),
            'ingredients': order_info.get('ingredients'),
            'delivery_date': order_info.get('delivery_date')
        }
        
        # Генерируем ответ от AI
        response = generate_response_sync(message_text, {
            "age": user.age if user else None,
            "gender": user.gender if user else None
        })
        
        # Сохраняем ответ в чат
        create_chat_sync({
            "user_id": user.id,
            "platform": "avito",
            "message": message_text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем ответ пользователю
        send_message_to_avito(conversation_id, response)
        
        # Запрашиваем вес
        send_message_to_avito(conversation_id, "Теперь укажите вес торта в килограммах:")
        
        # Обновляем состояние
        user_states[user_id] = 'waiting_for_weight'
        
    except Exception as e:
        logger.error(f"Ошибка в handle_description: {e}")
        send_message_to_avito(conversation_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_weight(user, user_id, conversation_id, message_text):
    """Обработка веса торта"""
    try:
        # Пробуем распознать вес из сообщения
        weight = None
        try:
            weight = float(message_text.replace(',', '.'))
        except ValueError:
            # Если не число, пробуем извлечь из текста с помощью AI
            response = generate_response_sync(f"Извлеки вес торта из сообщения: {message_text}", {"gender": user.gender if user else None})
            # Пробуем найти число в ответе AI
            import re
            numbers = re.findall(r'\d+\.?\d*', response)
            if numbers:
                weight = float(numbers[0])
        
        # Обновляем данные состояния
        state_data = user_states[user_id]
        if isinstance(state_data, dict):
            state_data['weight'] = weight
        else:
            state_data = {'weight': weight}
        
        user_states[user_id] = state_data
        
        # Генерируем ответ от AI
        response = generate_response_sync(f"Вес торта: {weight} кг. Какие ингредиенты или начинку вы бы хотели?", {
            "age": user.age if user else None,
            "gender": user.gender if user else None
        })
        
        # Сохраняем сообщение и ответ в чат
        create_chat_sync({
            "user_id": user.id,
            "platform": "avito",
            "message": message_text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем ответ пользователю
        send_message_to_avito(conversation_id, response)
        
        # Запрашиваем ингредиенты
        user_states[user_id] = 'waiting_for_ingredients'
        
    except Exception as e:
        logger.error(f"Ошибка в handle_weight: {e}")
        send_message_to_avito(conversation_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_ingredients(user, user_id, conversation_id, message_text):
    """Обработка ингредиентов/начинки"""
    try:
        # Обновляем данные состояния
        state_data = user_states[user_id]
        if isinstance(state_data, dict):
            state_data['ingredients'] = message_text
        else:
            state_data = {'ingredients': message_text}
        
        user_states[user_id] = state_data
        
        # Генерируем ответ от AI
        response = generate_response_sync(f"Ингредиенты: {message_text}. Когда вам нужна доставка торта?", {
            "age": user.age if user else None,
            "gender": user.gender if user else None
        })
        
        # Сохраняем сообщение и ответ в чат
        create_chat_sync({
            "user_id": user.id,
            "platform": "avito",
            "message": message_text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем ответ пользователю
        send_message_to_avito(conversation_id, response)
        
        # Запрашиваем дату доставки
        user_states[user_id] = 'waiting_for_delivery_date'
        
    except Exception as e:
        logger.error(f"Ошибка в handle_ingredients: {e}")
        send_message_to_avito(conversation_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_delivery_date(user, user_id, conversation_id, message_text):
    """Обработка даты доставки"""
    try:
        # Обновляем данные состояния
        state_data = user_states[user_id]
        if isinstance(state_data, dict):
            state_data['delivery_date'] = message_text
        else:
            state_data = {'delivery_date': message_text}
        
        user_states[user_id] = state_data
        
        # Формируем сообщение с подтверждением
        confirmation_msg = (
            f"Вот что мы знаем о вашем заказе:\n\n"
            f"Описание: {state_data.get('description', 'Не указано')}\n"
            f"Вес: {state_data.get('weight', 'Не указан')} кг\n"
            f"Ингредиенты: {state_data.get('ingredients', 'Не указаны')}\n"
            f"Дата доставки: {state_data.get('delivery_date', 'Не указана')}\n\n"
            f"Все верно? Отправьте 'Да' для подтверждения или уточните, что-то."
        )
        
        # Генерируем ответ от AI
        response = generate_response_sync(confirmation_msg, {
            "age": user.age if user else None,
            "gender": user.gender if user else None
        })
        
        # Сохраняем сообщение и ответ в чат
        create_chat_sync({
            "user_id": user.id,
            "platform": "avito",
            "message": message_text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем сообщение с подтверждением
        send_message_to_avito(conversation_id, response)
        send_message_to_avito(conversation_id, confirmation_msg)
        
        # Устанавливаем состояние ожидания подтверждения
        user_states[user_id] = 'waiting_for_confirmation'
        
    except Exception as e:
        logger.error(f"Ошибка в handle_delivery_date: {e}")
        send_message_to_avito(conversation_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_confirmation(user, user_id, conversation_id, message_text):
    """Обработка подтверждения заказа"""
    try:
        state_data = user_states[user_id]
        
        # Проверяем, подтверждает ли пользователь заказ
        confirmation_text = message_text.lower()
        if confirmation_text in ['да', 'ок', 'подтверждаю', 'yes', 'y']:
            # Создаем заказ в базе данных
            order_data = {
                "user_id": user.id,
                "platform": "avito",
                "description": state_data.get('description', ''),
                "weight": state_data.get('weight'),
                "ingredients": [state_data.get('ingredients')] if state_data.get('ingredients') else [],
                "delivery_date": state_data.get('delivery_date'),
                "status": "pending"
            }
            
            order = create_order_sync(order_data)
            
            # Генерируем изображение торта
            image_url = generate_cake_image_sync(
                state_data.get('description', ''),
                state_data.get('weight')
            )
            
            if image_url:
                # В тексте сообщения указываем URL изображения
                send_message_to_avito(conversation_id, f"Вот как будет выглядеть ваш торт! {image_url}")
            
            # Отправляем уведомление кондитеру
            notify_confectioner_avito(order, image_url)
            
            # Удаляем состояние пользователя
            if user_id in user_states:
                del user_states[user_id]
            
            send_message_to_avito(
                conversation_id,
                "Ваш заказ принят! 🎂 Кондитер свяжется с вами в ближайшее время для уточнения деталей. "
                "Спасибо за заказ!"
            )
        else:
            # Если пользователь не подтверждает, возвращаем к предыдущему шагу
            send_message_to_avito(conversation_id, "Пожалуйста, уточните, что вы хотели бы изменить в заказе.")
            user_states[user_id] = 'waiting_for_delivery_date'
        
    except Exception as e:
        logger.error(f"Ошибка в handle_confirmation: {e}")
        send_message_to_avito(conversation_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def send_message_to_avito(conversation_id: str, message: str):
    """Отправка сообщения пользователю через Avito API"""
    try:
        headers = get_headers()
        
        # URL для отправки сообщения (в реальной реализации нужно использовать правильный endpoint)
        url = f"https://api.avito.ru/messenger/v1/accounts/conversations/{conversation_id}/messages"
        
        data = {
            'text': message
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в Avito: {e}")

def notify_confectioner_avito(order, image_url: str = None):
    """Уведомление кондитера о новом заказе из Avito"""
    try:
        notification_text = (
            f"🔔 Новый заказ от Avito!\n\n"
            f"ID заказа: {order.id}\n"
            f"Клиент: {order.user_id}\n"
            f"Описание: {order.description}\n"
            f"Вес: {order.weight} кг\n"
            f"Ингредиенты: {', '.join(order.ingredients) if order.ingredients else 'Не указаны'}\n"
            f"Дата доставки: {order.delivery_date}\n"
        )
        
        if image_url:
            notification_text += f"\nИзображение торта: {image_url}"
        
        # Отправляем уведомление в чат кондитера через Telegram
        import requests
        telegram_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        data = {
            'chat_id': settings.telegram_confectioner_chat_id,
            'text': notification_text
        }
        requests.post(telegram_url, data=data)
            
    except Exception as e:
        logger.error(f"Ошибка при уведомлении кондитера из Avito: {e}")

# Синхронные версии асинхронных функций для Avito (в реальной реализации лучше использовать Redis или другой асинхронный подход)
def get_user_by_platform_id_sync(platform, platform_user_id):
    """Синхронная версия получения пользователя"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(get_user_by_platform_id(platform, platform_user_id))
    finally:
        loop.close()

def create_user_sync(user_data):
    """Синхронная версия создания пользователя"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(create_user(user_data))
    finally:
        loop.close()

def create_order_sync(order_data):
    """Синхронная версия создания заказа"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(create_order(order_data))
    finally:
        loop.close()

def create_chat_sync(chat_data):
    """Синхронная версия создания чата"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(create_chat(chat_data))
    finally:
        loop.close()

def generate_response_sync(message, user_info):
    """Синхронная версия генерации ответа"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(generate_response(message, user_info))
    finally:
        loop.close()

def analyze_order_description_sync(description):
    """Синхронная версия анализа описания заказа"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(analyze_order_description(description))
    finally:
        loop.close()

def generate_cake_image_sync(description, weight=None, photo_analysis=None):
    """Синхронная версия генерации изображения торта"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(generate_cake_image(description, weight, photo_analysis))
    finally:
        loop.close()