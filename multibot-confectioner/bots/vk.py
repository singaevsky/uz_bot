import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from config import settings
from ai.chat import generate_response, analyze_order_description
from ai.image_gen import generate_cake_image
from database.crud import create_user, get_user_by_platform_id, create_order, create_chat
import threading
import logging

logger = logging.getLogger(__name__)

vk_session = None
longpoll = None
vk_api_connection = None

# Словарь для хранения состояний пользователей (в реальной реализации лучше использовать Redis или базу данных)
user_states = {}

def setup_vk_bot():
    """Инициализация VK бота"""
    global vk_session, longpoll, vk_api_connection
    
    try:
        vk_session = vk_api.VkApi(token=settings.vk_access_token)
        longpoll = VkBotLongPoll(vk_session, settings.vk_group_id)
        vk_api_connection = vk_session.get_api()
        
        logger.info("VK бот инициализирован")
        
        # Запускаем обработку сообщений в отдельном потоке
        thread = threading.Thread(target=process_vk_messages)
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        logger.error(f"Ошибка инициализации VK бота: {e}")
        raise

def process_vk_messages():
    """Обработка сообщений от VK в отдельном потоке"""
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                handle_message(event.obj.message)
    except Exception as e:
        logger.error(f"Ошибка обработки сообщений VK: {e}")

def handle_message(message_data):
    """Обработка сообщения от VK"""
    try:
        user_id = message_data['from_id']
        message_text = message_data['text']
        peer_id = message_data['peer_id']
        
        # Проверяем, есть ли пользователь в базе
        user = get_user_by_platform_id_sync("vk", str(user_id))
        
        if not user:
            # Создаем нового пользователя
            user_data = {
                "platform": "vk",
                "platform_user_id": str(user_id),
            }
            user = create_user_sync(user_data)
        
        # Сохраняем сообщение в чат
        create_chat_sync({
            "user_id": user.id,
            "platform": "vk",
            "message": message_text,
            "ai_model": "user"
        })
        
        # Получаем текущее состояние пользователя
        current_state = user_states.get(user_id)
        
        if message_text.lower() == 'начать' or message_text.lower() == 'start':
            # Начинаем новый заказ
            user_states[user_id] = 'waiting_for_description'
            
            # Отправляем приветственное сообщение
            welcome_text = (
                "🎂 Добро пожаловать в кондитерскую AI-помощника!\n\n"
                "Я помогу вам оформить заказ на торт или десерт. "
                "Давайте начнем с описания, какой торт вы хотите?"
            )
            
            send_message(peer_id, welcome_text)
            return
        
        # Обработка в зависимости от состояния
        if current_state == 'waiting_for_description':
            handle_description(user, user_id, peer_id, message_text)
        elif current_state == 'waiting_for_weight':
            handle_weight(user, user_id, peer_id, message_text)
        elif current_state == 'waiting_for_ingredients':
            handle_ingredients(user, user_id, peer_id, message_text)
        elif current_state == 'waiting_for_delivery_date':
            handle_delivery_date(user, user_id, peer_id, message_text)
        elif current_state == 'waiting_for_confirmation':
            handle_confirmation(user, user_id, peer_id, message_text)
        else:
            # Если состояние не установлено, отвечаем с помощью AI
            response = generate_response_sync(message_text, {
                "age": user.age if user else None,
                "gender": user.gender if user else None
            })
            
            # Сохраняем ответ в чат
            create_chat_sync({
                "user_id": user.id,
                "platform": "vk",
                "message": message_text,
                "response": response,
                "ai_model": "gpt-4o-mini"
            })
            
            # Отправляем ответ пользователю
            send_message(peer_id, response)
    
    except Exception as e:
        logger.error(f"Ошибка в handle_message: {e}")
        send_message(message_data['peer_id'], "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_description(user, user_id, peer_id, message_text):
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
            "platform": "vk",
            "message": message_text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем ответ пользователю
        send_message(peer_id, response)
        
        # Запрашиваем вес
        send_message(peer_id, "Теперь укажите вес торта в килограммах:")
        
        # Обновляем состояние
        user_states[user_id] = 'waiting_for_weight'
        
    except Exception as e:
        logger.error(f"Ошибка в handle_description: {e}")
        send_message(peer_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_weight(user, user_id, peer_id, message_text):
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
            "platform": "vk",
            "message": message_text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем ответ пользователю
        send_message(peer_id, response)
        
        # Запрашиваем ингредиенты
        user_states[user_id] = 'waiting_for_ingredients'
        
    except Exception as e:
        logger.error(f"Ошибка в handle_weight: {e}")
        send_message(peer_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_ingredients(user, user_id, peer_id, message_text):
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
            "platform": "vk",
            "message": message_text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем ответ пользователю
        send_message(peer_id, response)
        
        # Запрашиваем дату доставки
        user_states[user_id] = 'waiting_for_delivery_date'
        
    except Exception as e:
        logger.error(f"Ошибка в handle_ingredients: {e}")
        send_message(peer_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_delivery_date(user, user_id, peer_id, message_text):
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
            "platform": "vk",
            "message": message_text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем сообщение с подтверждением
        send_message(peer_id, response)
        send_message(peer_id, confirmation_msg)
        
        # Устанавливаем состояние ожидания подтверждения
        user_states[user_id] = 'waiting_for_confirmation'
        
    except Exception as e:
        logger.error(f"Ошибка в handle_delivery_date: {e}")
        send_message(peer_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_confirmation(user, user_id, peer_id, message_text):
    """Обработка подтверждения заказа"""
    try:
        state_data = user_states[user_id]
        
        # Проверяем, подтверждает ли пользователь заказ
        confirmation_text = message_text.lower()
        if confirmation_text in ['да', 'ок', 'подтверждаю', 'yes', 'y']:
            # Создаем заказ в базе данных
            order_data = {
                "user_id": user.id,
                "platform": "vk",
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
                # В VK нельзя отправить изображение напрямую по URL, нужно сначала загрузить на сервер VK
                # Для упрощения в этой версии просто укажем URL в тексте
                send_message(peer_id, f"Вот как будет выглядеть ваш торт! {image_url}")
            
            # Отправляем уведомление кондитеру
            notify_confectioner_vkontakte(order, image_url)
            
            # Удаляем состояние пользователя
            if user_id in user_states:
                del user_states[user_id]
            
            send_message(
                peer_id,
                "Ваш заказ принят! 🎂 Кондитер свяжется с вами в ближайшее время для уточнения деталей. "
                "Спасибо за заказ!"
            )
        else:
            # Если пользователь не подтверждает, возвращаем к предыдущему шагу
            send_message(peer_id, "Пожалуйста, уточните, что вы хотели бы изменить в заказе.")
            user_states[user_id] = 'waiting_for_delivery_date'
        
    except Exception as e:
        logger.error(f"Ошибка в handle_confirmation: {e}")
        send_message(peer_id, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def send_message(peer_id, message):
    """Отправка сообщения пользователю через VK API"""
    try:
        vk_api_connection.messages.send(
            peer_id=peer_id,
            message=message,
            random_id=0  # Для предотвращения дублирования
        )
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в VK: {e}")

def notify_confectioner_vkontakte(order, image_url: str = None):
    """Уведомление кондитера о новом заказе через VK"""
    try:
        notification_text = (
            f"🔔 Новый заказ от VK!\n\n"
            f"ID заказа: {order.id}\n"
            f"Клиент: {order.user_id}\n"
            f"Описание: {order.description}\n"
            f"Вес: {order.weight} кг\n"
            f"Ингредиенты: {', '.join(order.ingredients) if order.ingredients else 'Не указаны'}\n"
            f"Дата доставки: {order.delivery_date}\n"
        )
        
        if image_url:
            notification_text += f"\nИзображение торта: {image_url}"
        
        # Отправляем уведомление в чат кондитера через Telegram (как в случае с Telegram)
        # Для упрощения используем Telegram для уведомлений, как и в случае с Telegram ботом
        import requests
        telegram_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        data = {
            'chat_id': settings.telegram_confectioner_chat_id,
            'text': notification_text
        }
        requests.post(telegram_url, data=data)
            
    except Exception as e:
        logger.error(f"Ошибка при уведомлении кондитера из VK: {e}")

# Синхронные версии асинхронных функций для VK (в реальной реализации лучше использовать Redis или другой асинхронный подход)
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