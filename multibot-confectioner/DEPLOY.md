# Инструкция по деплою AI-помощника кондитера

## 1. Подготовка к деплою

### 1.1. Локальный запуск для тестирования
```bash
# Установка зависимостей
pip install -r requirements.txt

# Создание файла .env на основе .env.example
cp .env.example .env
# Заполните .env вашими значениями

# Запуск приложения
python main.py
```

### 1.2. Запуск в Docker
```bash
# Сборка и запуск через Docker Compose
docker-compose up --build

# Или запуск в detached режиме
docker-compose up --build -d
```

## 2. Деплой на Render

### 2.1. Создание аккаунта на Render
1. Зарегистрируйтесь на [https://render.com](https://render.com)
2. Создайте новую Web Service
3. Выберите репозиторий с вашим проектом (или импортируйте его)

### 2.2. Настройка Web Service
- **Environment**: Python
- **Branch**: main
- **Root Directory**: `/multibot-confectioner`
- **Build Command**: 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
- **Environment Variables**: Добавьте все переменные из .env файла

### 2.3. Настройка Redis
1. Создайте новый Redis instance на Render
2. Добавьте переменную окружения `REDIS_URL` в Web Service

### 2.4. Настройка Supabase
1. Создайте проект на [https://supabase.com](https://supabase.com)
2. Выполните миграции из папки `migrations`
3. Добавьте URL и ключи в переменные окружения

## 3. Деплой на другие платформы

### 3.1. Heroku
1. Установите Heroku CLI
2. Создайте приложение:
   ```bash
   heroku create your-app-name
   ```
3. Добавьте buildpack для Python:
   ```bash
   heroku buildpacks:set heroku/python
   ```
4. Задеплойте код:
   ```bash
   git push heroku main
   ```
5. Установите переменные окружения:
   ```bash
   heroku config:set TELEGRAM_BOT_TOKEN=your_token
   # и так для всех переменных
   ```

### 3.2. VPS/Сервер
1. Клонируйте репозиторий на сервер
2. Установите Python 3.12 и зависимости
3. Настройте PostgreSQL и Redis
4. Используйте Gunicorn или Uvicorn для запуска
5. Настройте Nginx как reverse proxy
6. Используйте systemd для автозапуска

## 4. Настройка webhook URL (для Telegram)

Если вы используете webhook вместо polling, установите webhook URL:
```bash
curl -F "url=https://your-domain.com/webhook/telegram/BOT_TOKEN" https://api.telegram.org/botBOT_TOKEN/setWebhook
```

## 5. Настройка переменных окружения

Обязательные переменные:
- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `TELEGRAM_CONFECTIONER_CHAT_ID` - ID чата кондитера
- `VK_ACCESS_TOKEN` - токен доступа VK
- `VK_GROUP_ID` - ID группы VK
- `VK_CONFIRMATION_TOKEN` - токен подтверждения
- `AVITO_CLIENT_ID` - ID клиента Avito
- `AVITO_CLIENT_SECRET` - секретный ключ Avito
- `OPENAI_API_KEY` - API ключ OpenAI
- `SUPABASE_URL` - URL проекта Supabase
- `SUPABASE_KEY` - API ключ Supabase
- `DATABASE_URL` - URL базы данных

## 6. Миграции базы данных

После деплоя выполните миграции:
1. Подключитесь к Supabase
2. Выполните SQL из файлов в папке `migrations`
3. Или используйте Alembic/другой инструмент миграций

## 7. Тестирование после деплоя

1. Проверьте доступность API: `https://your-domain.com/health`
2. Протестируйте ботов на всех платформах
3. Убедитесь, что уведомления доходят до кондитера
4. Проверьте генерацию изображений
5. Проверьте сохранение заказов в базе данных

## 8. Мониторинг и логирование

- Настройте логирование в приложении
- Используйте Sentry для отслеживания ошибок
- Настройте уведомления о сбоях
- Мониторьте использование API-ключей

## 9. Безопасность

- Не храните API-ключи в открытом виде
- Используйте HTTPS
- Проверяйте валидность webhook запросов
- Ограничьте доступ к административным функциям