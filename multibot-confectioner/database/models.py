from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class User(BaseModel):
    id: Optional[str] = None
    platform: str  # telegram, vk, avito
    platform_user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None  # male, female, other
    phone: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Order(BaseModel):
    id: Optional[str] = None
    user_id: str
    platform: str  # telegram, vk, avito
    description: str
    weight: Optional[float] = None
    ingredients: Optional[List[str]] = None
    delivery_date: Optional[datetime] = None
    status: str = "pending"  # pending, confirmed, in_progress, completed, cancelled
    price: Optional[float] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Chat(BaseModel):
    id: Optional[str] = None
    user_id: str
    platform: str  # telegram, vk, avito
    message: str
    response: Optional[str] = None
    timestamp: Optional[datetime] = None
    ai_model: Optional[str] = None  # gpt-4o-mini, etc.