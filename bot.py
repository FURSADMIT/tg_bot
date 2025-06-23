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
SECRET_TOKEN = os.getenv('SECRET_TOKEN', 'your_secret_token_here')
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

# Основной эндпоинт для вебхука
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info(f"Received webhook request: {request.method} {request.url}")
    
    # Проверка секретного токена
    secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if secret_token != SECRET_TOKEN:
        logger.warning(f"Invalid secret token received: {secret_token} (expected: {SECRET_TOKEN})")
        return jsonify({"status": "forbidden"}), 403
    
    try:
        json_data = request.get_json()
        logger.debug(f"Webhook JSON data: {json_data}")
        
        if not json_data:
            logger.warning("Empty JSON data received")
            return jsonify({"status": "bad request"}), 400
            
        update = Update.de_json(json_data, application.bot)
        
        if update.message:
            logger.info(f"Received message from {update.message.from_user.id}: {update.message.text}")
        elif update.callback_query:
            logger.info(f"Received callback from {update.callback_query.from_user.id}")
        else:
            logger.info(f"Received update of type: {update.update_id}")
        
        # Обработка обновления в асинхронном режиме
        asyncio.run_coroutine_threadsafe(process_update(update), application.create_task)
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

async def process_update(update):
    try:
        logger.info(f"Processing update: {update.update_id}")
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)

# Состояния разговора
QUESTIONS = 1

questions = [
    "*1.* *Замечаю опечатки в текстах*",
    "*2.* *Люблю решать головоломки и логические задачи*",
    "*3.* *Могу многократно проверять одно и то же*",
    "*4.* *Изучая новое приложение, стараюсь разобраться во всех его функциях*",
    "*5.* *Насколько вам интересны новые технологии и IT-сфера?*"
]

reply_keyboard = [["1 😞", "2 😐", "3 😊", "4 😃", "5 🤩"]]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

main_menu_keyboard = [
    [KeyboardButton("Начать тест 🚀"), KeyboardButton("О курсе ℹ️")],
    [KeyboardButton("Проверить бота ✅")]
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)

def keep_alive():
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

async def setup_webhook():
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            webhook_url = f"{WEBHOOK_URL}/webhook"
            logger.info(f"Setting webhook (attempt {attempt+1}/{max_attempts}): {webhook_url}")
            
            # Устанавливаем новый вебхук
            await application.bot.set_webhook(
                url=webhook_url,
                secret_token=SECRET_TOKEN,
                drop_pending_updates=True
            )
            logger.info("Webhook set successfully")
            
            # Проверяем установку
            webhook_info = await application.bot.get_webhook_info()
            logger.info(f"Webhook info: URL={webhook_info.url}, Pending updates={webhook_info.pending_update_count}")
            
            return True
        except Exception as e:
            logger.error(f"Error setting webhook: {str(e)}", exc_info=True)
            if attempt < max_attempts - 1:
                wait_time = 5 * (attempt + 1)
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
    
    logger.error("Failed to set webhook after multiple attempts")
    return False

async def post_init(application: Application) -> None:
    logger.info("Running post-initialization")
    
    webhook_success = await setup_webhook()
    
    if not webhook_success:
        logger.critical("Webhook setup failed, bot may not receive updates")
    
    try:
        await application.bot.set_my_commands([
            ("start", "Начать тест"),
            ("about", "О курсе"),
            ("health", "Проверить работу бота"),
            ("menu", "Показать меню"),
            ("status", "Статус бота")
        ])
        logger.info("Bot commands set successfully")
    except Exception as e:
        logger.error(f"Error setting bot commands: {str(e)}", exc_info=True)

def create_telegram_app():
    global application
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^Начать тест 🚀$"), start)
        ],
        states={
            QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("health", telegram_health))
    application.add_handler(CommandHandler("about", about_course))
    application.add_handler(CommandHandler("status", bot_status))
    application.add_handler(MessageHandler(filters.Regex("^О курсе ℹ️$"), about_course))
    application.add_handler(MessageHandler(filters.Regex("^Проверить бота ✅$"), telegram_health))
    application.add_handler(CommandHandler("menu", show_menu))
    application.add_error_handler(error_handler)
    
    return application

async def bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        me = await context.bot.get_me()
        webhook_info = await context.bot.get_webhook_info()
        
        status_text = (
            f"🤖 *Статус бота:*\n"
            f"• Имя: {me.full_name}\n"
            f"• Username: @{me.username}\n"
            f"• ID: {me.id}\n\n"
            f"🌐 *Вебхук:*\n"
            f"• URL: {webhook_info.url}\n"
            f"• Ожидает обновлений: {webhook_info.pending_update_count}\n"
            f"• Ошибки: {webhook_info.last_error_message or 'Нет'}\n\n"
            f"🔐 *Секретный токен:* `{SECRET_TOKEN[:3]}...{SECRET_TOKEN[-3:]}`"
        )
        
        await update.message.reply_text(
            status_text,
            parse_mode="Markdown",
            reply_markup=main_menu_markup
        )
    except Exception as e:
        logger.error(f"Error in bot_status: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Ошибка при получении статуса бота",
            reply_markup=main_menu_markup
        )

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🏠 *Главное меню* 🏠\n\nВыберите действие:",
        reply_markup=main_menu_markup,
        parse_mode="Markdown"
    )

async def about_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await update.message.reply_text(
        f"✅ {BOT_NAME} работает нормально!",
        reply_markup=main_menu_markup
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.message.from_user
        logger.info(f"Command /start received from user {user.id}")
        
        context.user_data.clear()
        context.user_data['answers'] = []
        context.user_data['current_question_index'] = 0
        
        welcome_text = (
            f"Привет, {user.first_name}! Я {BOT_NAME}, помогу оценить твои качества для работы в тестировании.\n\n"
            "Ответь на 5 тезисов по шкале от 1 до 5, где:\n"
            "1 😞 - совсем не обо мне\n"
            "5 🤩 - это точно про меня\n"
        )
        
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await update.message.reply_text(
            questions[0],
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        return QUESTIONS
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}", exc_info=True)
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
        
        answer = answer_text.split()[0]
        
        answers = context.user_data.get('answers', [])
        current_question_index = context.user_data.get('current_question_index', 0)
        
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
        
        answers.append(int(answer))
        context.user_data['answers'] = answers
        
        next_question_index = current_question_index + 1
        context.user_data['current_question_index'] = next_question_index
        
        if next_question_index < len(questions):
            await update.message.reply_text(
                questions[next_question_index],
                reply_markup=markup,
                parse_mode="Markdown"
            )
            return QUESTIONS
        
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
        logger.error(f"Error handling answer: {str(e)}", exc_info=True)
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
        logger.error(f"Error in cancel command: {str(e)}", exc_info=True)
        return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling Telegram update:", exc_info=context.error)
    
    if update and update.effective_message:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="😢 Произошла непредвиденная ошибка. Пожалуйста, попробуйте снова.",
                reply_markup=main_menu_markup
            )
        except Exception as e:
            logger.error(f"Failed to send error notification: {str(e)}")

def run_flask():
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, threaded=True)

async def run_bot():
    global application
    application = create_telegram_app()
    await application.initialize()
    await application.start()
    logger.info("Bot initialized and started")
    
    me = await application.bot.get_me()
    logger.info(f"Bot info: {me.full_name} (@{me.username})")
    
    try:
        webhook_info = await application.bot.get_webhook_info()
        logger.info(f"Webhook info: URL={webhook_info.url}, Pending updates={webhook_info.pending_update_count}")
    except Exception as e:
        logger.error(f"Error getting webhook info: {str(e)}")
    
    await asyncio.Event().wait()

def main():
    if WEBHOOK_URL:
        keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        keep_alive_thread.start()
        logger.info(f"Starting keep-alive service for {WEBHOOK_URL}")
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}", exc_info=True)
    finally:
        loop.close()
        logger.info("Event loop closed")

if __name__ == "__main__":
    logger.info(f"Starting {BOT_NAME}")
    logger.info(f"TOKEN: {TOKEN[:5]}...{TOKEN[-5:]}")
    logger.info(f"WEBHOOK_URL: {WEBHOOK_URL}")
    logger.info(f"PORT: {PORT}")
    logger.info(f"SECRET_TOKEN: {SECRET_TOKEN[:3]}...")
    logger.info(f"TG_LINK: {TG_LINK}")
    logger.info(f"VK_LINK: {VK_LINK}")
    
    main()
