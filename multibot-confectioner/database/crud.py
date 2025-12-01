from typing import List, Optional
from .models import User, Order, Chat
from .init import get_supabase_client
import logging

logger = logging.getLogger(__name__)

# CRUD операции для User
async def create_user(user: User) -> User:
    supabase = get_supabase_client()
    try:
        response = supabase.table('users').insert(user.dict(exclude_unset=True)).execute()
        created_user = response.data[0]
        return User(**created_user)
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {e}")
        raise

async def get_user_by_platform_id(platform: str, platform_user_id: str) -> Optional[User]:
    supabase = get_supabase_client()
    try:
        response = (
            supabase.table('users')
            .select('*')
            .eq('platform', platform)
            .eq('platform_user_id', platform_user_id)
            .execute()
        )
        if response.data:
            return User(**response.data[0])
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        raise

async def update_user(user_id: str, user: User) -> User:
    supabase = get_supabase_client()
    try:
        response = supabase.table('users').update(user.dict(exclude_unset=True)).eq('id', user_id).execute()
        updated_user = response.data[0]
        return User(**updated_user)
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя: {e}")
        raise

# CRUD операции для Order
async def create_order(order: Order) -> Order:
    supabase = get_supabase_client()
    try:
        response = supabase.table('orders').insert(order.dict(exclude_unset=True)).execute()
        created_order = response.data[0]
        return Order(**created_order)
    except Exception as e:
        logger.error(f"Ошибка при создании заказа: {e}")
        raise

async def get_order_by_id(order_id: str) -> Optional[Order]:
    supabase = get_supabase_client()
    try:
        response = supabase.table('orders').select('*').eq('id', order_id).execute()
        if response.data:
            return Order(**response.data[0])
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении заказа: {e}")
        raise

async def update_order(order_id: str, order: Order) -> Order:
    supabase = get_supabase_client()
    try:
        response = supabase.table('orders').update(order.dict(exclude_unset=True)).eq('id', order_id).execute()
        updated_order = response.data[0]
        return Order(**updated_order)
    except Exception as e:
        logger.error(f"Ошибка при обновлении заказа: {e}")
        raise

async def get_orders_by_user_id(user_id: str) -> List[Order]:
    supabase = get_supabase_client()
    try:
        response = supabase.table('orders').select('*').eq('user_id', user_id).execute()
        return [Order(**order) for order in response.data]
    except Exception as e:
        logger.error(f"Ошибка при получении заказов пользователя: {e}")
        raise

# CRUD операции для Chat
async def create_chat(chat: Chat) -> Chat:
    supabase = get_supabase_client()
    try:
        response = supabase.table('chats').insert(chat.dict(exclude_unset=True)).execute()
        created_chat = response.data[0]
        return Chat(**created_chat)
    except Exception as e:
        logger.error(f"Ошибка при создании чата: {e}")
        raise

async def get_chats_by_user_id(user_id: str) -> List[Chat]:
    supabase = get_supabase_client()
    try:
        response = supabase.table('chats').select('*').eq('user_id', user_id).execute()
        return [Chat(**chat) for chat in response.data]
    except Exception as e:
        logger.error(f"Ошибка при получении чатов пользователя: {e}")
        raise