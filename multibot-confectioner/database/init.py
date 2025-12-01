import asyncio
from supabase import create_client, Client
from config import settings
from .models import User, Order, Chat
import logging

logger = logging.getLogger(__name__)

supabase_client: Client = None

async def init_db():
    """Инициализация подключения к Supabase"""
    global supabase_client
    try:
        supabase_client = create_client(settings.supabase_url, settings.supabase_key)
        logger.info("Подключение к Supabase успешно установлено")
        return supabase_client
    except Exception as e:
        logger.error(f"Ошибка подключения к Supabase: {e}")
        raise

def get_supabase_client():
    """Получение клиента Supabase"""
    global supabase_client
    if supabase_client is None:
        raise RuntimeError("Supabase клиент не инициализирован. Вызовите init_db() сначала.")
    return supabase_client