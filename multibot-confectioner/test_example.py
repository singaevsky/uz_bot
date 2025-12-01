"""
Примеры тестов для проекта AI-помощника кондитера
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from ai.chat import generate_response, analyze_order_description
from ai.image_gen import generate_cake_image
from database.crud import create_user, get_user_by_platform_id
from core.utils import extract_weight_from_text, extract_date_from_text


@pytest.mark.asyncio
async def test_generate_response():
    """Тест генерации ответа от AI"""
    message = "Хочу торт с вишней"
    user_info = {"age": 25, "gender": "female"}
    
    with patch('openai.ChatCompletion.acreate') as mock_openai:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Отличный выбор! Какой вес торта вы preferете?"
        mock_openai.return_value = mock_response
        
        response = await generate_response(message, user_info)
        
        assert "вес" in response.lower()
        mock_openai.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_order_description():
    """Тест анализа описания заказа"""
    description = "Хочу торт весом 2.5 кг с вишней и кремом, на 20 декабря"
    
    with patch('openai.ChatCompletion.acreate') as mock_openai:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"weight": 2.5, "ingredients": ["вишня", "крем"], "decor": null, "delivery_date": "20 декабря"}'
        mock_openai.return_value = mock_response
        
        result = await analyze_order_description(description)
        
        assert result["weight"] == 2.5
        assert "вишня" in result["ingredients"]
        assert "крем" in result["ingredients"]


def test_extract_weight_from_text():
    """Тест извлечения веса из текста"""
    assert extract_weight_from_text("торт 2.5 кг") == 2.5
    assert extract_weight_from_text("торт весом 3,2 кг") == 3.2
    assert extract_weight_from_text("нужен торт 1500 г") == 1.5  # 1500 г = 1.5 кг
    assert extract_weight_from_text("примерно 2 кг") == 2.0
    assert extract_weight_from_text("торт") is None


def test_extract_date_from_text():
    """Тест извлечения даты из текста"""
    from datetime import datetime
    
    result = extract_date_from_text("на 20.12.2023")
    expected = datetime(2023, 12, 20)
    assert result == expected
    
    result = extract_date_from_text("доставка 25/12/2023")
    expected = datetime(2023, 12, 25)
    assert result == expected
    
    result = extract_date_from_text("хочу на 2023-12-30")
    expected = datetime(2023, 12, 30)
    assert result == expected


@pytest.mark.asyncio
async def test_user_crud_operations():
    """Тест операций с пользователями"""
    # Тест создания пользователя
    user_data = {
        "platform": "telegram",
        "platform_user_id": "123456789",
        "first_name": "Test",
        "last_name": "User"
    }
    
    with patch('database.init.get_supabase_client') as mock_supabase:
        mock_response = MagicMock()
        mock_response.data = [user_data]
        mock_supabase.return_value.table.return_value.insert.return_value.execute.return_value = mock_response
        
        created_user = await create_user(user_data)
        
        assert created_user.platform == "telegram"
        assert created_user.platform_user_id == "123456789"
        
        # Тест получения пользователя
        mock_get_response = MagicMock()
        mock_get_response.data = [user_data]
        mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_get_response
        
        retrieved_user = await get_user_by_platform_id("telegram", "123456789")
        
        assert retrieved_user.platform_user_id == "123456789"


@pytest.mark.asyncio
async def test_generate_cake_image():
    """Тест генерации изображения торта"""
    description = "шоколадный торт с вишней"
    weight = 2.0
    
    with patch('openai.Image.acreate') as mock_openai:
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].url = "https://example.com/cake_image.jpg"
        mock_openai.return_value = mock_response
        
        image_url = await generate_cake_image(description, weight)
        
        assert image_url == "https://example.com/cake_image.jpg"
        mock_openai.assert_called_once()