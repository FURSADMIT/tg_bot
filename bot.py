import os
import logging
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
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Полный URL вашего приложения на Render
SECRET_TOKEN = os.getenv('SECRET_TOKEN', 'your-secret-token')
BOT_NAME = "@QaPollsBot"

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
            result += "🚀 Отличные задатки для тестировщика!"
        elif total >= 15:
            result += "🌟 Хороший потенциал!"
        else:
            result += "💡 Тестирование ПО может быть не твоим основным призванием, но IT - для всех!"
        
        await update.message.reply_text(
            result,
            parse_mode="Markdown",
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
    """Обработчик ошибок для всего приложения"""
    logger.error("Exception while handling an update:", exc_info=context.error)

def main() -> None:
    # Создаем Application
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
    
    # Используем Webhook вместо Polling
    logger.info("Starting bot in WEBHOOK mode")
    
    # Установка webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/{SECRET_TOKEN}",
        secret_token=SECRET_TOKEN,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    logger.info(f"Starting {BOT_NAME}")
    logger.info(f"TOKEN: {TOKEN[:5]}...{TOKEN[-5:]}")
    logger.info(f"WEBHOOK_URL: {WEBHOOK_URL}")
    logger.info(f"PORT: {PORT}")
    main()
