import os
import logging
import threading
import requests
import time
from flask import Flask, jsonify
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Конфигурация
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
SECRET_TOKEN = os.getenv('SECRET_TOKEN', 'default-secret-token')
BOT_NAME = "@QaPollsBot"
TG_LINK = "https://t.me/Dmitrii_Fursa8"
VK_LINK = "https://m.vk.com/id119459855"

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем Flask приложение для обработки HTTP-запросов
http_app = Flask(__name__)

@http_app.route('/health')
def http_health():
    """HTTP эндпоинт для проверки работоспособности"""
    return jsonify({"status": "ok", "bot": BOT_NAME}), 200

@http_app.route('/')
def home():
    """Корневой эндпоинт"""
    return jsonify({"message": "QA Polls Bot is running"}), 200

# Состояния разговора
QUESTIONS = 1

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

def keep_alive():
    """Функция для поддержания активности приложения"""
    time.sleep(15)  # Даем время на запуск основного приложения
    logger.info("Starting keep-alive service")
    
    while True:
        try:
            if WEBHOOK_URL:
                health_url = f"{WEBHOOK_URL}/health"
                response = requests.get(health_url, timeout=10)
                logger.info(f"Keep-alive: Service status {response.status_code}")
            else:
                logger.info("Keep-alive: WEBHOOK_URL not set")
        except Exception as e:
            logger.error(f"Keep-alive error: {str(e)}")
        
        # Интервал 5 минут (300 секунд)
        time.sleep(300)

async def telegram_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram команда для проверки работоспособности"""
    await update.message.reply_text(f"✅ {BOT_NAME} работает нормально!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.message.from_user
        logger.info(f"Command /start received from user {user.id}")
        
        # Очищаем предыдущие ответы
        context.user_data.clear()
        context.user_data['answers'] = []
        context.user_data['current_question'] = 0
        
        await update.message.reply_text(
            f"Привет, {user.first_name}! Я {BOT_NAME}, помогу определить твою предрасположенность к тестированию ПО.\n\n"
            "Ответь на 5 вопросов по шкале от 1 до 5, где:\n"
            "1 - совсем не обо мне\n"
            "5 - это точно про меня\n\n"
            "Первый вопрос:\n" + questions[0],
            reply_markup=markup
        )
        return QUESTIONS
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text("⚠️ Произошла ошибка при запуске. Попробуйте снова.")
        return ConversationHandler.END

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.message.from_user
        answer = update.message.text
        logger.info(f"User {user.id} answer: {answer}")
        
        # Получаем текущее состояние
        answers = context.user_data.get('answers', [])
        current_question = context.user_data.get('current_question', 0)
        
        # Проверка корректности ответа
        if not answer.isdigit() or int(answer) < 1 or int(answer) > 5:
            await update.message.reply_text(
                "Пожалуйста, выберите цифру от 1 до 5",
                reply_markup=markup
            )
            await update.message.reply_text(questions[current_question], reply_markup=markup)
            return QUESTIONS
        
        # Сохраняем ответ
        answers.append(int(answer))
        context.user_data['answers'] = answers
        next_question = len(answers)
        context.user_data['current_question'] = next_question
        
        # Проверяем, все ли вопросы отвечены
        if next_question < len(questions):
            await update.message.reply_text(questions[next_question], reply_markup=markup)
            return QUESTIONS
        
        # Все вопросы отвечены - показываем результат
        total = sum(answers)
        result = "🔍 *Ваши результаты* 🔍\n\n"
        
        if total >= 20:
            result += (
                "🚀 *Отличные задатки для тестировщика!*\n\n"
                "Твой результат показывает высокую предрасположенность к QA. "
                "Чтобы превратить это в профессию:\n\n"
                f"👉 Напиши мне в Telegram: [@Dmitrii_Fursa8]({TG_LINK})\n"
                f"👉 Подписывайся на меня в ВКонтакте: [Dmitrii Fursa]({VK_LINK})"
            )
        elif total >= 15:
            result += (
                "🌟 *Хороший потенциал!*\n\n"
                "У тебя есть базовые качества тестировщика. "
                "Чтобы развить их до профессионального уровня:\n\n"
                f"👉 Напиши мне в Telegram: [@Dmitrii_Fursa8]({TG_LINK})\n"
                f"👉 Подписывайся на меня в ВКонтакте: [Dmitrii Fursa]({VK_LINK})"
            )
        else:
            result += (
                "💡 *Тестирование ПО может быть не твоим основным призванием, но это не значит, что IT не для тебя!*\n\n"
                "Если ты хочешь:\n"
                "• Стать тестировщиком и войти в IT\n"
                "• Получить востребованную профессию\n"
                "• Освоить навыки, которые откроют двери в мир технологий\n\n"
                f"👉 Пиши мне в Telegram: [@Dmitrii_Fursa8]({TG_LINK})\n"
                f"👉 Подписывайся на меня в ВКонтакте: [Dmitrii Fursa]({VK_LINK})"
            )
        
        await update.message.reply_text(
            result,
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Кнопка для повторного прохождения
        await update.message.reply_text(
            "Хотите пройти тест еще раз? Используйте команду /start"
        )
        
        logger.info(f"Test completed for user {user.id}. Score: {total}")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error handling answer: {str(e)}")
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте начать заново командой /start")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        await update.message.reply_text("Тест отменен", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in cancel command: {str(e)}")
        return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок для Telegram бота"""
    logger.error("Exception while handling Telegram update:", exc_info=context.error)
    
    # Уведомляем пользователя об ошибке
    if update and update.effective_message:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="😢 Произошла непредвиденная ошибка. Пожалуйста, попробуйте снова."
            )
        except Exception:
            logger.error("Failed to send error notification to user")

def run_flask():
    """Запуск Flask сервера"""
    logger.info(f"Starting Flask server on port {PORT}")
    http_app.run(host='0.0.0.0', port=PORT)

def main() -> None:
    # Создаем Telegram Application
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем глобальный обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Регистрируем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("health", telegram_health))
    
    # Запускаем keep-alive в отдельном потоке
    if WEBHOOK_URL:
        threading.Thread(target=keep_alive, daemon=True).start()
        logger.info(f"Starting keep-alive service for {WEBHOOK_URL}")
    
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Запускаем Telegram бота в режиме polling
    logger.info("Starting Telegram bot in POLLING mode")
    application.run_polling()

if __name__ == "__main__":
    logger.info(f"Starting {BOT_NAME}")
    logger.info(f"TOKEN: {TOKEN[:5]}...{TOKEN[-5:]}")
    logger.info(f"WEBHOOK_URL: {WEBHOOK_URL}")
    logger.info(f"PORT: {PORT}")
    logger.info(f"SECRET_TOKEN: {SECRET_TOKEN[:3]}...")
    logger.info(f"TG_LINK: {TG_LINK}")
    logger.info(f"VK_LINK: {VK_LINK}")
    
    main()
