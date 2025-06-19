import os
import logging
import threading
import requests
import time
from flask import Flask, jsonify
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, MenuButtonCommands
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

# Создаем Flask приложение
app = Flask(__name__)

@app.route('/health')
def health():
    """HTTP эндпоинт для проверки работоспособности"""
    return jsonify({"status": "ok", "bot": BOT_NAME}), 200

@app.route('/')
def home():
    """Корневой эндпоинт"""
    return jsonify({"message": "QA Polls Bot is running"}), 200

# Состояния разговора
QUESTIONS = 1

# Вопросы теста
questions = [
    "*1.* *Замечаю опечатки в текстах*",
    "*2.* *Люблю решать головоломки и логические задачи*",
    "*3.* *Могу многократно проверять одно и то же*",
    "*4.* *Изучая новое приложение, стараюсь разобраться во всех его функциях*",
    "*5.* *Насколько вам интересны новые технологии и IT-сфера?*"
]

# Клавиатура для ответов с эмодзи
reply_keyboard = [[
    KeyboardButton("1 😞"),
    KeyboardButton("2 😐"),
    KeyboardButton("3 🙂"),
    KeyboardButton("4 😊"),
    KeyboardButton("5 😍")
]]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

# Текст для кнопки "О курсе"
ABOUT_COURSE_TEXT = """
🚀 *Мой путь в IT* 🚀

Я прошел путь от директора магазина (Adidas/Reebok) до тестировщика в одной из лучших IT-компаний!

Я всегда любил свою работу, вкладывался в нее на все 100%, но за 8 лет в рознице понял, что не готов пропускать жизнь мимо и хочу большего: путешествия, новые возможности и карьерный рост, поэтому решил сменить сферу.

🔍 *Как я начинал в IT:*
- Прошел ряд курсов (в том числе получил диплом в одной из крупнейших школ на рынке онлайн-образования)
- Изучил сотни доступных видео и статей
- На их основе создал обучающие материалы для себя

Только благодаря этому мне удалось войти и закрепиться в новой сфере. Сейчас я собрал самые эффективные практики и готов делиться своими знаниями.

🧪 *Тестирование* - это реальный и доступный каждому порог входа в IT.

📚 *Что вас ждет на курсе?*
- Теория и практические занятия (онлайн)
- Поддержка на всех этапах обучения
- Подготовка к собеседованиям и успешное трудоустройство

💼 *А после курса:*
- Новые возможности IT-компаний
- Конкурентная ЗП, ДМС, льготы
- Возможность удаленной работы
- Крутые офисы с тренажерными залами, бесплатной едой, вечеринками
- Большие перспективы на будущее

📩 За подробностями пишите мне в личные сообщения - все расскажу!
"""

def keep_alive():
    """Функция для поддержания активности приложения"""
    time.sleep(15)
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
        time.sleep(300)

def create_telegram_app():
    """Создаем и настраиваем Telegram приложение"""
    application = Application.builder().token(TOKEN).build()
    
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
    application.add_handler(CommandHandler("about", about_course))
    application.add_error_handler(error_handler)
    
    # Устанавливаем меню бота
    application.bot.set_my_commands([
        ("start", "Начать тест"),
        ("about", "О курсе тестирования")
    ])
    
    return application

async def set_bot_menu(application: Application):
    """Устанавливаем меню бота"""
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonCommands()
    )

async def telegram_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram команда для проверки работоспособности"""
    await update.message.reply_text(f"✅ {BOT_NAME} работает нормально!")

async def about_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для информации о курсе"""
    try:
        await update.message.reply_text(
            ABOUT_COURSE_TEXT,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error in about command: {str(e)}")
        await update.message.reply_text("⚠️ Произошла ошибка при отображении информации о курсе.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.message.from_user
        logger.info(f"Command /start received from user {user.id}")
        
        # Очищаем предыдущие ответы
        context.user_data.clear()
        context.user_data['answers'] = []
        context.user_data['current_question_index'] = 0
        
        # Приветственное сообщение с кнопками
        welcome_text = (
            f"👋 Привет, {user.first_name}! Я {BOT_NAME}, помогу оценить твои качества для работы в тестировании.\n\n"
            "🔹 Нажми /start - чтобы начать тест\n"
            "🔹 Нажми /about - чтобы узнать о курсе тестирования\n\n"
            "Ответь на 5 тезисов по шкале от 1 до 5:\n"
            "1 😞 - совсем не обо мне\n"
            "5 😍 - это точно про меня\n"
        )
        
        # Отправляем приветствие
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown"
        )
        
        # Отправляем первый вопрос с клавиатурой
        await update.message.reply_text(
            questions[0],
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        return QUESTIONS
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text("⚠️ Произошла ошибка при запуске. Попробуйте снова.")
        return ConversationHandler.END

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.message.from_user
        answer_text = update.message.text
        logger.info(f"User {user.id} answer: {answer_text}")
        
        # Извлекаем цифру из ответа (учитываем эмодзи)
        answer = ''.join(filter(str.isdigit, answer_text))
        
        # Получаем текущее состояние
        answers = context.user_data.get('answers', [])
        current_question_index = context.user_data.get('current_question_index', 0)
        
        # Проверка корректности ответа
        if not answer or int(answer) < 1 or int(answer) > 5:
            await update.message.reply_text(
                "Пожалуйста, выберите цифру от 1 до 5",
                reply_markup=markup
            )
            await update.message.reply_text(
                questions[current_question_index],
                reply_markup=markup,
                parse_mode="Markdown"
            )
            return QUESTIONS
        
        # Сохраняем ответ
        answers.append(int(answer))
        context.user_data['answers'] = answers
        
        # Переходим к следующему вопросу
        next_question_index
