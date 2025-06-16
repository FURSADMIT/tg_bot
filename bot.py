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
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '').rstrip('/')
SECRET_TOKEN = os.getenv('SECRET_TOKEN', 'default-secret-token')
BOT_NAME = "@QaPollsBot"

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
QUESTIONS = 0

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

async def log_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Логируем все входящие сообщения для диагностики"""
    logger.info(f"Received message: {update.message.text} (User: {update.effective_user.id})")

def keep_awake(app_url):
    """Функция для поддержания активности на Render"""
    time.sleep(15)
    logger.info("Starting keep-alive service")
    health_url = f"{app_url}/health"
    
    while True:
        try:
            if app_url:
                response = requests.get(health_url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"Keep-alive: Service is alive (status {response.status_code})")
                else:
                    logger.warning(f"Unexpected status: {response.status_code}")
            else:
                logger.info("Keep-alive: WEBHOOK_URL not set, skipping")
        except Exception as e:
            logger.error(f"Keep-alive error: {str(e)}")
        time.sleep(600)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info(f"Command /start received from user {user.id}")
    
    # Очищаем предыдущие ответы и завершаем текущий опрос
    if 'answers' in context.user_data:
        context.user_data.clear()
        logger.info(f"Cleared previous state for user {user.id}")
    
    # Сбрасываем состояние
    if context.user_data.get('conversation_active', False):
        await update.message.reply_text(
            "Прерван предыдущий опрос. Начинаем новый тест.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    context.user_data['answers'] = []
    context.user_data['conversation_active'] = True
    
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
    user = update.message.from_user
    answer = update.message.text
    logger.info(f"User {user.id} answer: {answer}")
    
    # Если получена команда /start во время опроса
    if answer == "/start":
        await update.message.reply_text(
            "Завершите текущий тест или используйте /cancel для отмены",
            reply_markup=markup
        )
        return QUESTIONS
    
    # Проверка корректности ответа
    if not answer.isdigit() or int(answer) < 1 or int(answer) > 5:
        current_index = len(context.user_data.get('answers', []))
        if current_index < len(questions):
            await update.message.reply_text(
                "Пожалуйста, выберите цифру от 1 до 5",
                reply_markup=markup
            )
            await update.message.reply_text(questions[current_index], reply_markup=markup)
        return QUESTIONS
    
    # Сохраняем ответ
    context.user_data['answers'].append(int(answer))
    answers = context.user_data['answers']
    logger.info(f"User {user.id} answers: {answers}")
    
    # Проверяем, все ли вопросы отвечены
    if len(answers) < len(questions):
        next_index = len(answers)
        await update.message.reply_text(questions[next_index], reply_markup=markup)
        return QUESTIONS
    
    # Все вопросы отвечены - показываем результат
    total = sum(answers)
    result = "🔍 *Ваши результаты* 🔍\n\n"
    
    if total >= 20:
        result += (
            "🚀 *Отличные задатки для тестировщика!*\n\n"
            "Твой результат показывает высокую предрасположенность к QA. "
            "Чтобы превратить это в профессию:\n\n"
            "👉 Напиши мне в Telegram [@Dmitrii_Fursa8](https://t.me/Dmitrii_Fursa8)\n\n"
            "Подписывайся на мой канал: [QA Mentor](https://t.me/qa_mentor)"
        )
    elif total >= 15:
        result += (
            "🌟 *Хороший потенциал!*\n\n"
            "У тебя есть базовые качества тестировщика. "
            "Чтобы развить их до профессионального уровня:\n\n"
            "👉 Напиши мне в Telegram [@Dmitrii_Fursa8](https://t.me/Dmitrii_Fursa8)"
        )
    else:
        result += (
            "💡 *Тестирование ПО может быть не твоим основным призванием, но это не значит, что IT не для тебя!*\n\n"
            "Если ты хочешь:\n"
            "• Стать тестировщиком и войти в IT\n"
            "• Получить востребованную профессию\n"
            "• Освоить навыки, которые откроют двери в мир технологий\n\n"
            "👉 Пиши мне прямо сейчас: [@Dmitrii_Fursa8](https://t.me/Dmitrii_Fursa8)\n"
            "Я помогу тебе начать карьеру в IT, даже если сейчас кажется, что это не твое!"
        )
    
    await update.message.reply_text(
        result,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Кнопка для повторного прохождения
    await update.message.reply_text(
        "Хотите пройти тест еще раз? Используйте команду /start",
        reply_markup=ReplyKeyboardMarkup([["/start"]], one_time_keyboard=True)
    )
    
    # Сбрасываем состояние
    context.user_data['conversation_active'] = False
    logger.info(f"Test completed for user {user.id}. Score: {total}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    await update.message.reply_text("Тест отменен", reply_markup=ReplyKeyboardRemove())
    
    # Сбрасываем состояние
    if 'conversation_active' in context.user_data:
        context.user_data['conversation_active'] = False
        context.user_data.pop('answers', None)
    
    logger.info(f"Test canceled by user {user.id}")
    return ConversationHandler.END

async def handle_start_during_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start во время активного опроса"""
    user = update.message.from_user
    logger.warning(f"User {user.id} tried to start new conversation during active test")
    await update.message.reply_text(
        "⚠️ Сначала завершите текущий тест или используйте /cancel для отмены",
        reply_markup=ReplyKeyboardRemove()
    )

def main() -> None:
    # Создаем Application
    application = Application.builder().token(TOKEN).build()
    
    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            QUESTIONS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_answer
                ),
                # Обработка команды /start во время опроса
                CommandHandler(
                    "start",
                    handle_start_during_conversation
                )
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    application.add_handler(conv_handler)
    
    # Обработчик для health
    application.add_handler(CommandHandler("health", health))
    
    # Обработчик для логгирования
    application.add_handler(MessageHandler(filters.ALL, log_all_messages))
    
    # Определяем порт для Render
    port = int(os.environ.get("PORT", 10000))
    
    if WEBHOOK_URL:
        logger.info(f"Starting bot in WEBHOOK mode on port {port}")
        
        # Запускаем keep-alive
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
    logger.info(f"Starting {BOT_NAME}")
    logger.info(f"WEBHOOK_URL: {WEBHOOK_URL or 'Not set, using POLLING'}")
    logger.info(f"SECRET_TOKEN: {SECRET_TOKEN[:3]}...")
    main()
