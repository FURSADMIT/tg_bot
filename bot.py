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

# Глобальная переменная для хранения приложения Telegram
application = None

@app.route('/health')
def health():
    return jsonify({"status": "ok", "bot": BOT_NAME}), 200

@app.route('/')
def home():
    return jsonify({"message": "QA Polls Bot is running"}), 200

@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != SECRET_TOKEN:
        return jsonify({"status": "forbidden"}), 403
    
    json_data = request.get_json()
    update = Update.de_json(json_data, application.bot)
    await application.update_queue.put(update)
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

# Клавиатуры
reply_keyboard = [["1 😞", "2 😐", "3 😊", "4 😃", "5 🤩"]]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

main_menu_keyboard = [
    [KeyboardButton("Начать тест 🚀"), KeyboardButton("О курсе ℹ️")],
    [KeyboardButton("Проверить бота ✅")]
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)

def keep_alive():
    """Поддержание активности приложения"""
    time.sleep(15)
    logger.info("Starting keep-alive service")
    while True:
        try:
            if WEBHOOK_URL:
                requests.get(f"{WEBHOOK_URL}/health", timeout=10)
        except Exception as e:
            logger.error(f"Keep-alive error: {str(e)}")
        time.sleep(300)

async def post_init(application: Application) -> None:
    """Инициализация вебхука"""
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        secret_token=SECRET_TOKEN,
        drop_pending_updates=True
    )
    await application.bot.set_my_commands([
        ("start", "Начать тест"),
        ("about", "О курсе"),
        ("health", "Проверить бота")
    ])

def create_telegram_app():
    """Создание приложения Telegram"""
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
    application.add_handler(CommandHandler("about", about_course))
    application.add_handler(MessageHandler(filters.Regex("^О курсе ℹ️$"), about_course))
    application.add_handler(CommandHandler("health", check_health))
    application.add_handler(MessageHandler(filters.Regex("^Проверить бота ✅$"), check_health))
    application.add_error_handler(error_handler)
    
    return application

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.message.from_user
        context.user_data.clear()
        context.user_data['answers'] = []
        context.user_data['current_question'] = 0
        
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
        
        await ask_question(update, context)
        return QUESTIONS
        
    except Exception as e:
        logger.error(f"Start error: {str(e)}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при запуске. Попробуйте снова.",
            reply_markup=main_menu_markup
        )
        return ConversationHandler.END

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = context.user_data['current_question']
    await update.message.reply_text(
        questions[current],
        reply_markup=markup,
        parse_mode="Markdown"
    )

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        answer = update.message.text.split()[0]
        if not answer.isdigit() or int(answer) < 1 or int(answer) > 5:
            await update.message.reply_text("Пожалуйста, выберите от 1 до 5")
            await ask_question(update, context)
            return QUESTIONS
        
        context.user_data['answers'].append(int(answer))
        context.user_data['current_question'] += 1
        
        if context.user_data['current_question'] < len(questions):
            await ask_question(update, context)
            return QUESTIONS
        
        await show_results(update, context)
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Handle answer error: {str(e)}")
        await update.message.reply_text(
            "⚠️ Ошибка обработки ответа. Начните тест заново.",
            reply_markup=main_menu_markup
        )
        return ConversationHandler.END

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = sum(context.user_data['answers'])
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

async def about_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = """
🌟 *О курсе* 🌟

Я прошел путь от директора магазина (Adidas/Reebok) до тестировщика в одной из лучших IT-компаний!

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

async def check_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"✅ {BOT_NAME} работает нормально!",
        reply_markup=main_menu_markup
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Тест отменён",
        reply_markup=main_menu_markup
    )
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Error:", exc_info=context.error)
    if update and update.effective_message:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="😢 Произошла ошибка. Попробуйте позже.",
            reply_markup=main_menu_markup
        )

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

async def run_bot():
    global application
    application = create_telegram_app()
    await application.initialize()
    await application.start()
    logger.info("Bot started")

async def shutdown():
    global application
    if application:
        await application.stop()
        await application.shutdown()

def main():
    if WEBHOOK_URL:
        threading.Thread(target=keep_alive, daemon=True).start()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_bot())
        run_flask()
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown())
    finally:
        loop.close()

if __name__ == "__main__":
    import asyncio
    logger.info(f"Starting {BOT_NAME}")
    main()
