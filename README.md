# QA Polls Bot

Телеграм-бот для оценки навыков тестировщика.

## Развертывание на Render.com

1. Создайте новый Web Service в Render.com
2. Подключите этот репозиторий
3. Установите переменные окружения:
   - `SECRET_TOKEN` - сгенерируйте случайную строку (можно использовать команду `openssl rand -hex 16`)
4. Укажите команды:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`

## Важные настройки
- Токен бота уже встроен в код
- Render автоматически предоставляет переменную `RENDER_EXTERNAL_URL`
- Для проверки работоспособности: `https://your-service.onrender.com/health`
