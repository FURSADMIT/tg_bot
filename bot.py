import os
import logging
import threading
import requests
import time
from flask import Flask, jsonify, request
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
import asyncio

# Конфигурация
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7292601652:AAFAv9wtDXK_2CI3zHGu9RCHQsvPCfzwjUE')
PORT = int(os.environ.get('PORT', 10000))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://qa-polls-bot.onrender.com')
SECRET_TOKEN = os.getenv('SECRET_TOKEN', os.urandom(16).hex())
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

# Глобальная переменная для хранения приложения Telegram
application = None

@app.route('/health')
def health():
    return jsonify({"status": "ok", "bot": BOT_NAME}), 200

@app.route('/')
def home():
    return jsonify({"message": "QA Polls Bot is running"}), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != SECRET_TOKEN:
        logger.warning("Invalid secret token received")
        return jsonify({"status": "forbidden"}), 403
    
    json_data = request.get_json()
    update = Update.de_json(json_data, application.bot)
    
    # Запускаем обработку обновления в асинхронном цикле
    asyncio.run_coroutine_threadsafe(
        application.update_queue.put(update),
        application.updater._event_loop
    )
    
    return jsonify({"status": "ok"}), 200

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
reply_keyboard = [["1 😞", "2 😐", "3 😊", "4 😃", "5 🤩"]]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

# Главное меню
main_menu_keyboard = [
    [KeyboardButton("Начать тест 🚀"), KeyboardButton("О курсе ℹ️")],
    [KeyboardButton("Проверить бота ✅")]
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)

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

async def post_init(application: Application) -> None:
    """Настройка вебхука после инициализации приложения"""
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        secret_token=SECRET_TOKEN,
        drop_pending_updates=True
    )
    await application.bot.set_my_commands([
        ("start", "Начать тест"),
        ("about", "О курсе"),
        ("health", "Проверить работу бота"),
        ("menu", "Показать меню")
    ])

def create_telegram_app():
    """Создаем и настраиваем Telegram приложение"""
    global application
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
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
    application.add_handler(MessageHandler(filters.Regex("^О курсе ℹ️$"), about_course))
    application.add_handler(MessageHandler(filters.Regex("^Проверить бота ✅$"), telegram_health))
    application.add_handler(CommandHandler("menu", show_menu))
    application.add_error_handler(error_handler)
    
    return application

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать главное меню"""
    await update.message.reply_text(
        "🏠 *Главное меню* 🏠\n\nВыберите действие:",
        reply_markup=main_menu_markup,
        parse_mode="Markdown"
    )

async def about_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Информация о курсе"""
    about_text = """
🌟 *О курсе* 🌟

Я прошел путь от директора магазина (Adidas/Reebok) до тестировщика в одной из лучших IT-компаний!

Я всегда любил свою работу, вкладывался в нее на все 100, но за 8 лет в рознице понял, что не готов пропускать жизнь мимо и хочу большего: путешествия, новые возможности и карьерный рост, поэтому решил сменить сферу.

Начал изучать IT:
- прошел ряд курсов (в том числе получил диплом в одной из крупнейших школ на рынке онлайн-образования),
- изучил буквально сотни доступных видео и статей
- и на их основе создал обучающие материалы для себя.

Только благодаря этому мне удалось войти и закрепиться в новой сфере.
Сейчас я собрал самые эффективные практики и готов делиться своими знаниями.

🔍 *Тестирование - это реальный и доступный каждому порог входа в IT.*

*Что вас ждет?*
- Теория и практические занятия (онлайн)
- Поддержка на всех этапах обучения
- Подготовка к собеседованиям и успешное трудоустройство

🚀 *Ну а после:*
- новые возможности IT-компаний
- конкурентная ЗП, ДМС, льготы
- возможность удаленной работы
- крутые офисы с тренажерными залами, бесплатной едой, вечеринками, психологами
- и большие перспективы на будущее.

За подробностями пишите мне в Telegram: [@Dmitrii_Fursa8](https://t.me/Dmitrii_Fursa8)
"""
    
    await update.message.reply_text(
        about_text,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=main_menu_markup
    )

async def telegram_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram команда для проверки работоспособности"""
    await update.message.reply_text(
        f"✅ {BOT_NAME} работает нормально!",
        reply_markup=main_menu_markup
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.message.from_user
        logger.info(f"Command /start received from user {user.id}")
        
        # Очищаем предыдущие ответы
        context.user_data.clear()
        context.user_data['answers'] = []
        context.user_data['current_question_index'] = 0
        
        # Приветственное сообщение
        welcome_text = (
            f"Привет, {user.first_name}! Я {BOT_NAME}, помогу оценить твои качества для работы в тестировании.\n\n"
            "Ответь на 5 тезисов по шкале от 1 до 5, где:\n"
            "1 😞 - совсем не обо мне\n"
            "5 🤩 - это точно про меня\n"
        )
        
        # Отправляем приветствие
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
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
        await update.message.reply_text(
            "⚠️ Произошла ошибка при запуске. Попробуйте снова.",
            reply_markup=main_menu_markup
        )
        return ConversationHandler.END

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.message.from_user
        answer_text = update.message.text
        logger.info(f"User {user.id} answer: {answer_text}")
        
        # Извлекаем цифру из ответа (может быть с эмодзи)
        answer = answer_text.split()[0]  # Берем первую часть (цифру)
        
        # Получаем текущее состояние
        answers = context.user_data.get('answers', [])
        current_question_index = context.user_data.get('current_question_index', 0)
        
        # Проверка корректности ответа
        if not answer.isdigit() or int(answer) < 1 or int(answer) > 5:
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
        next_question_index = current_question_index + 1
        context.user_data['current_question_index'] = next_question_index
        
        # Проверяем, все ли вопросы отвечены
        if next_question_index < len(questions):
            await update.message.reply_text(
                questions[next_question_index],
                reply_markup=markup,
                parse_mode="Markdown"
            )
            return QUESTIONS
        
        # Все вопросы отвечены - показываем результат
        total = sum(answers)
        result = "🔍 *Ваши результаты* 🔍\n\n"
        
        if total >= 20:
            result += (
                "🚀 *Отличные задатки для тестировщика!*\n\n"
                "Твой результат показывает высокую склонность к тестированию. "
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
                "💡 *Тестирование может быть не твоим основным призванием, но это не значит, что IT не для тебя!*\n\n"
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
            reply_markup=main_menu_markup
        )
        
        logger.info(f"Test completed for user {user.id}. Score: {total}")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error handling answer: {str(e)}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка. Попробуйте начать заново командой /start",
            reply_markup=main_menu_markup
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        await update.message.reply_text(
            "Тест отменен",
            reply_markup=main_menu_markup
        )
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
                text="😢 Произошла непредвиденная ошибка. Пожалуйста, попробуйте снова.",
                reply_markup=main_menu_markup
            )
        except Exception:
            logger.error("Failed to send error notification to user")

def run_flask():
    """Запуск Flask сервера"""
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, threaded=True)

async def run_bot():
    """Запуск Telegram бота"""
    global application
    application = create_telegram_app()
    await application.initialize()
    await application.start()
    logger.info("Bot started")
    
    # Используем правильный метод для вебхуков
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="/webhook",
        webhook_url=f"{WEBHOOK_URL}/webhook",
        secret_token=SECRET_TOKEN
    )

async def shutdown():
    """Завершение работы бота"""
    global application
    if application:
        await application.stop()
        await application.shutdown()

def main():
    # Запускаем keep-alive в отдельном потоке
    if WEBHOOK_URL:
        threading.Thread(target=keep_alive, daemon=True).start()
    
    # Запускаем бот в асинхронном режиме
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        loop.run_until_complete(shutdown())
    finally:
        loop.close()

if __name__ == "__main__":
    logger.info(f"Starting {BOT_NAME}")
    logger.info(f"TOKEN: {TOKEN[:5]}...{TOKEN[-5:]}")
    logger.info(f"WEBHOOK_URL: {WEBHOOK_URL}")
    logger.info(f"PORT: {PORT}")
    logger.info(f"SECRET_TOKEN: {SECRET_TOKEN[:3]}...")
    logger.info(f"TG_LINK: {TG_LINK}")
    logger.info(f"VK_LINK: {VK_LINK}")
    
    main()
