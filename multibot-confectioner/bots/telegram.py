from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import settings
from ai.chat import generate_response, analyze_order_description
from ai.image_gen import generate_cake_image
from database.crud import create_user, get_user_by_platform_id, create_order, create_chat
from typing import Dict
import logging

logger = logging.getLogger(__name__)

bot: Bot = None
dp: Dispatcher = None

# FSM для управления состоянием заказа
class OrderState(StatesGroup):
    waiting_for_description = State()
    waiting_for_weight = State()
    waiting_for_ingredients = State()
    waiting_for_delivery_date = State()
    waiting_for_confirmation = State()

async def setup_telegram_bot():
    """Инициализация Telegram бота"""
    global bot, dp
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    
    # Регистрация хендлеров
    dp.message.register(start_command, Command("start"))
    dp.message.register(handle_description, OrderState.waiting_for_description)
    dp.message.register(handle_weight, OrderState.waiting_for_weight)
    dp.message.register(handle_ingredients, OrderState.waiting_for_ingredients)
    dp.message.register(handle_delivery_date, OrderState.waiting_for_delivery_date)
    dp.message.register(process_confirmation, OrderState.waiting_for_confirmation)
    dp.message.register(message_handler, lambda message: True)
    
    logger.info("Telegram бот инициализирован")

async def start_command(message: types.Message, state: FSMContext):
    """Обработка команды /start"""
    try:
        # Проверяем, есть ли пользователь в базе
        user = await get_user_by_platform_id("telegram", str(message.from_user.id))
        
        if not user:
            # Создаем нового пользователя
            user_data = {
                "platform": "telegram",
                "platform_user_id": str(message.from_user.id),
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
            }
            user = await create_user(user_data)
        
        # Сохраняем сообщение в чат
        await create_chat({
            "user_id": user.id,
            "platform": "telegram",
            "message": "/start",
            "ai_model": "system"
        })
        
        # Отправляем приветственное сообщение
        welcome_text = (
            "🎂 Добро пожаловать в кондитерскую AI-помощника!\n\n"
            "Я помогу вам оформить заказ на торт или десерт. "
            "Давайте начнем с описания, какой торт вы хотите?"
        )
        
        await message.answer(welcome_text)
        await state.set_state(OrderState.waiting_for_description)
        
    except Exception as e:
        logger.error(f"Ошибка в start_command: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def handle_description(message: types.Message, state: FSMContext):
    """Обработка описания торта"""
    try:
        user = await get_user_by_platform_id("telegram", str(message.from_user.id))
        
        # Сохраняем сообщение в чат
        await create_chat({
            "user_id": user.id,
            "platform": "telegram",
            "message": message.text,
            "ai_model": "user"
        })
        
        # Анализируем описание заказа
        order_info = await analyze_order_description(message.text)
        
        # Сохраняем информацию в состоянии
        await state.update_data(description=message.text, **order_info)
        
        # Генерируем ответ от AI
        response = await generate_response(message.text, {
            "age": user.age if user else None,
            "gender": user.gender if user else None
        })
        
        # Сохраняем ответ в чат
        await create_chat({
            "user_id": user.id,
            "platform": "telegram",
            "message": message.text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем ответ пользователю
        await message.answer(response)
        
        # Запрашиваем вес
        await message.answer("Теперь укажите вес торта в килограммах:")
        await state.set_state(OrderState.waiting_for_weight)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_description: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def handle_weight(message: types.Message, state: FSMContext):
    """Обработка веса торта"""
    try:
        user = await get_user_by_platform_id("telegram", str(message.from_user.id))
        
        # Пробуем распознать вес из сообщения
        weight = None
        try:
            weight = float(message.text.replace(',', '.'))
        except ValueError:
            # Если не число, пробуем извлечь из текста с помощью AI
            response = await generate_response(f"Извлеки вес торта из сообщения: {message.text}", {"gender": user.gender if user else None})
            # Пробуем найти число в ответе AI
            import re
            numbers = re.findall(r'\d+\.?\d*', response)
            if numbers:
                weight = float(numbers[0])
        
        # Обновляем данные состояния
        await state.update_data(weight=weight)
        
        # Генерируем ответ от AI
        response = await generate_response(f"Вес торта: {weight} кг. Какие ингредиенты или начинку вы бы хотели?", {
            "age": user.age if user else None,
            "gender": user.gender if user else None
        })
        
        # Сохраняем сообщение и ответ в чат
        await create_chat({
            "user_id": user.id,
            "platform": "telegram",
            "message": message.text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем ответ пользователю
        await message.answer(response)
        
        # Запрашиваем ингредиенты
        await state.set_state(OrderState.waiting_for_ingredients)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_weight: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def handle_ingredients(message: types.Message, state: FSMContext):
    """Обработка ингредиентов/начинки"""
    try:
        user = await get_user_by_platform_id("telegram", str(message.from_user.id))
        
        # Обновляем данные состояния
        await state.update_data(ingredients=message.text)
        
        # Генерируем ответ от AI
        response = await generate_response(f"Ингредиенты: {message.text}. Когда вам нужна доставка торта?", {
            "age": user.age if user else None,
            "gender": user.gender if user else None
        })
        
        # Сохраняем сообщение и ответ в чат
        await create_chat({
            "user_id": user.id,
            "platform": "telegram",
            "message": message.text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем ответ пользователю
        await message.answer(response)
        
        # Запрашиваем дату доставки
        await state.set_state(OrderState.waiting_for_delivery_date)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_ingredients: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def handle_delivery_date(message: types.Message, state: FSMContext):
    """Обработка даты доставки"""
    try:
        user = await get_user_by_platform_id("telegram", str(message.from_user.id))
        
        # Обновляем данные состояния
        await state.update_data(delivery_date=message.text)
        
        # Получаем все данные заказа
        data = await state.get_data()
        
        # Формируем сообщение с подтверждением
        confirmation_msg = (
            f"Вот что мы знаем о вашем заказе:\n\n"
            f"Описание: {data.get('description', 'Не указано')}\n"
            f"Вес: {data.get('weight', 'Не указан')} кг\n"
            f"Ингредиенты: {data.get('ingredients', 'Не указаны')}\n"
            f"Дата доставки: {data.get('delivery_date', 'Не указана')}\n\n"
            f"Все верно? Отправьте 'Да' для подтверждения или уточните, что-то."
        )
        
        # Генерируем ответ от AI
        response = await generate_response(confirmation_msg, {
            "age": user.age if user else None,
            "gender": user.gender if user else None
        })
        
        # Сохраняем сообщение и ответ в чат
        await create_chat({
            "user_id": user.id,
            "platform": "telegram",
            "message": message.text,
            "response": response,
            "ai_model": "gpt-4o-mini"
        })
        
        # Отправляем сообщение с подтверждением
        await message.answer(response)
        await message.answer(confirmation_msg)
        
        # Устанавливаем состояние ожидания подтверждения
        await state.set_state(OrderState.waiting_for_confirmation)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_delivery_date: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def process_confirmation(message: types.Message, state: FSMContext):
    """Обработка подтверждения заказа"""
    try:
        user = await get_user_by_platform_id("telegram", str(message.from_user.id))
        
        # Получаем все данные заказа
        data = await state.get_data()
        
        # Проверяем, подтверждает ли пользователь заказ
        confirmation_text = message.text.lower()
        if confirmation_text in ['да', 'ок', 'подтверждаю', 'yes', 'y']:
            # Создаем заказ в базе данных
            order_data = {
                "user_id": user.id,
                "platform": "telegram",
                "description": data.get('description', ''),
                "weight": data.get('weight'),
                "ingredients": [data.get('ingredients')] if data.get('ingredients') else [],
                "delivery_date": data.get('delivery_date'),
                "status": "pending"
            }
            
            order = await create_order(order_data)
            
            # Генерируем изображение торта
            image_url = await generate_cake_image(
                data.get('description', ''),
                data.get('weight'),
                data.get('photo_analysis')  # если было загружено фото
            )
            
            if image_url:
                # Обновляем заказ с URL изображения
                order_data["image_url"] = image_url
                await create_order(order_data)  # в реальности нужно использовать update_order
                
                # Отправляем изображение пользователю
                await message.answer_photo(photo=image_url, caption="Вот как будет выглядеть ваш торт!")
            
            # Отправляем уведомление кондитеру
            await notify_confectioner(order, image_url)
            
            # Завершаем FSM
            await state.clear()
            
            await message.answer(
                "Ваш заказ принят! 🎂 Кондитер свяжется с вами в ближайшее время для уточнения деталей. "
                "Спасибо за заказ!"
            )
        else:
            # Если пользователь не подтверждает, возвращаем к предыдущему шагу
            await message.answer("Пожалуйста, уточните, что вы хотели бы изменить в заказе.")
            await state.set_state(OrderState.waiting_for_delivery_date)
        
    except Exception as e:
        logger.error(f"Ошибка в process_confirmation: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

async def notify_confectioner(order, image_url: str = None):
    """Уведомление кондитера о новом заказе"""
    try:
        notification_text = (
            f"🔔 Новый заказ от Telegram!\n\n"
            f"ID заказа: {order.id}\n"
            f"Клиент: {order.user_id}\n"
            f"Описание: {order.description}\n"
            f"Вес: {order.weight} кг\n"
            f"Ингредиенты: {', '.join(order.ingredients) if order.ingredients else 'Не указаны'}\n"
            f"Дата доставки: {order.delivery_date}\n"
        )
        
        if image_url:
            await bot.send_photo(chat_id=settings.telegram_confectioner_chat_id, photo=image_url, caption=notification_text)
        else:
            await bot.send_message(chat_id=settings.telegram_confectioner_chat_id, text=notification_text)
            
    except Exception as e:
        logger.error(f"Ошибка при уведомлении кондитера: {e}")

async def message_handler(message: types.Message, state: FSMContext):
    """Обработка обычных сообщений (вне FSM)"""
    try:
        current_state = await state.get_state()
        if current_state is None:
            # Если состояние не установлено, отвечаем с помощью AI
            user = await get_user_by_platform_id("telegram", str(message.from_user.id))
            
            # Сохраняем сообщение в чат
            await create_chat({
                "user_id": user.id,
                "platform": "telegram",
                "message": message.text,
                "ai_model": "user"
            })
            
            # Генерируем ответ от AI
            response = await generate_response(message.text, {
                "age": user.age if user else None,
                "gender": user.gender if user else None
            })
            
            # Сохраняем ответ в чат
            await create_chat({
                "user_id": user.id,
                "platform": "telegram",
                "message": message.text,
                "response": response,
                "ai_model": "gpt-4o-mini"
            })
            
            # Отправляем ответ пользователю
            await message.answer(response)
    
    except Exception as e:
        logger.error(f"Ошибка в message_handler: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")