from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
from config import settings
from bots.telegram import setup_telegram_bot
from bots.vk import setup_vk_bot
from bots.avito import setup_avito_bot
from database.init import init_db
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI-Помощник Кондитера", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("Инициализация ботов...")
    await setup_telegram_bot()
    setup_vk_bot()
    setup_avito_bot()
    logger.info("Приложение запущено")

@app.get("/")
async def root():
    return {"message": "AI-Помощник Кондитера", "status": "ok"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/webhook/telegram/{token}")
async def telegram_webhook(token: str, request: Request):
    # Обработка вебхука от Telegram
    data = await request.json()
    logger.info(f"Получено сообщение от Telegram: {data}")
    # Здесь будет логика обработки сообщения от Telegram
    return {"ok": True}

@app.post("/webhook/vk")
async def vk_webhook(request: Request):
    # Обработка вебхука от VK
    data = await request.json()
    logger.info(f"Получено сообщение от VK: {data}")
    # Здесь будет логика обработки сообщения от VK
    return {"ok": True}

@app.post("/webhook/avito")
async def avito_webhook(request: Request):
    # Обработка вебхука от Avito
    data = await request.json()
    logger.info(f"Получено сообщение от Avito: {data}")
    # Здесь будет логика обработки сообщения от Avito
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(
        "main.py:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )