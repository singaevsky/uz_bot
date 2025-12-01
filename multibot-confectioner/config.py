from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str
    telegram_webhook_url: Optional[str] = None
    telegram_confectioner_chat_id: str

    # VK
    vk_group_id: str
    vk_access_token: str
    vk_confirmation_token: str
    vk_secret_key: str

    # Avito
    avito_client_id: str
    avito_client_secret: str
    avito_access_token: str
    avito_refresh_token: str

    # OpenAI
    openai_api_key: str
    openai_org_id: Optional[str] = None

    # Supabase
    supabase_url: str
    supabase_key: str

    # Database
    database_url: str

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    class Config:
        env_file = ".env"


settings = Settings()