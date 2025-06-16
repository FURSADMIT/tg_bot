import os
import logging
import threading
import requests
import time
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackContext
)

# Конфигурация
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '').rstrip('/')  # Удаляем слэш в конце
SECRET_TOKEN = os.getenv('SECRET_TOKEN', 'default-secret-token')
BOT_NAME = "@QaPollsBot"

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
QUESTIONS, NAME, EMAIL = range(3)

# Вопросы теста
questions = [
    "Замечаете ли вы опечатки в текстах?",
    "Любите ли вы решать головоломки и логические задачи?",
    "Как вы реагируете на необходимость многократно проверять одно и то же?",
    "Изучая новое приложение, вы стараетесь разобраться во всех его функциях?",
    "Насколько вам интересны новые технологии и IT-сфера?"
]

# Клавиатура для ответов
reply_keyboard = [["1", "2", "3", "4", "5"]]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

async def health(update: Update, context: CallbackContext) -> None:
    """Эндпоинт для проверки работоспособности"""
    await update.message.reply_text(f"✅ {BOT_NAME} работает нормально!\n"
                                 f"Режим: {'WEBHOOK' if WEBHOOK_URL else 'POLLING'}")

def keep_awake(app_url):
    """Функция для поддержания активности на Render"""
    # Дадим приложению время запуститься перед первым пингом
    time.sleep(15)
    
    logger.info("Starting keep-alive service")
    
    while True:
        try:
            if app_url:
                # Используем базовый URL без /health для пинга
                response = requests.get(app_url, timeout=5)
                logger.info(f"Keep-alive ping to {app_url}, status: {response.status_code}")
        except Exception as e:
            logger.error(f"Keep-alive error: {str(e)}")
        
        # Увеличим интервал до 10 минут (600 секунд)
        time.sleep(600)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info(f"User {user.id} started conversation")
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я {BOT_NAME}, помогу определить твою предрасположенность к тестированию ПО.\n\n"
        "Ответь на 5 вопросов по шкале от 1 до 5, где:\n"
        "1 - совсем не обо мне\n"
        "5 - это точно про меня\n\n"
        "Первый вопрос:\n" + questions[0],
        reply_markup=markup
    )
    return QUESTIONS

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    if not answer.isdigit() or int(answer) < 1 or int(answer) > 5:
        await update.message.reply_text("Пожалуйста, выберите цифру от 1 до 5", reply_markup=markup)
        return QUESTIONS
    
    context.user_data.setdefault('answers', []).append(int(answer))
    question_index = len(context.user_data['answers'])
    
    if question_index < len(questions):
        await update.message.reply_text(questions[question_index], reply_markup=markup)
        return QUESTIONS
    
    await update.message.reply_text(
        "Тест завершен! Введите ваше имя:",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Введите ваш email для получения результатов:")
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text
    context.user_data['email'] = email
    
    # Расчет результатов
    total = sum(context.user_data['answers'])
    result = "🔍 Ваши результаты 🔍\n\n"
    
    if total >= 6:
        result += "Отличные задатки для тестировщика! Рекомендуем пройти наш курс:\nhttps://example.com/course"
    elif total == 5:
        result += "Есть потенциал! Развивайте навыки внимательности."
    else:
        result += "Тестирование может не быть вашим призванием, но попробуйте наш вводный урок:\nhttps://example.com/trial"
    
    await update.message.reply_text(result)
    
    # Кнопка для повторного прохождения
    await update.message.reply_text(
        "Хотите пройти тест еще раз?",
        reply_markup=ReplyKeyboardMarkup([["/start"]], one_time_keyboard=True)
    )
    
    logger.info(f"User completed test: {context.user_data}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Тест отменен", reply_markup=ReplyKeyboardRemove())
    logger.info("Test canceled by user")
    return ConversationHandler.END

def main() -> None:
    # Создаем Application
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем health-эндпоинт
    application.add_handler(CommandHandler("health", health))
    
    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    application.add_handler(conv_handler)
    
    # Определяем порт для Render
    port = int(os.environ.get("PORT", 10000))
    
    if WEBHOOK_URL:
        logger.info(f"Starting bot in WEBHOOK mode on port {port}")
        
        # Запускаем keep-alive в отдельном потоке
        threading.Thread(
            target=keep_awake,
            args=(WEBHOOK_URL,),
            daemon=True
        ).start()
        
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=WEBHOOK_URL,
            secret_token=SECRET_TOKEN,
            drop_pending_updates=True
        )
    else:
        logger.info("Starting bot in POLLING mode")
        application.run_polling()

if __name__ == "__main__":
    logger.info(f"Starting {BOT_NAME} with token: {TOKEN[:5]}...{TOKEN[-5:]}")
    logger.info(f"WEBHOOK_URL: {WEBHOOK_URL or 'Not set, using POLLING'}")
    main()
