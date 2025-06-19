import os
import logging
import asyncio
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

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
application = None

# Состояния и вопросы
QUESTIONS = 1
questions = [
    "1. Замечаю опечатки в текстах",
    "2. Люблю решать головоломки",
    "3. Многократно проверяю одно и то же",
    "4. Изучаю все функции новых приложений",
    "5. Интересуюсь IT и технологиями"
]

# Клавиатуры
reply_keyboard = [["1 😞", "2 😐", "3 😊", "4 😃", "5 🤩"]]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

main_menu_keyboard = [
    [KeyboardButton("Начать тест 🚀"), KeyboardButton("О курсе ✨")],
    [KeyboardButton("Помощь ❓")]
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)

@app.route('/')
def home():
    return jsonify({"status": "ok"}), 200

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != SECRET_TOKEN:
        return jsonify({"status": "forbidden"}), 403
    
    json_data = request.get_json()
    update = Update.de_json(json_data, application.bot)
    await application.update_queue.put(update)
    return jsonify({"status": "ok"}), 200

async def post_init(app):
    await app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook",
        secret_token=SECRET_TOKEN,
        drop_pending_updates=True
    )
    await app.bot.set_my_commands([
        ("start", "Начать тест"),
        ("about", "О курсе"),
        ("help", "Помощь")
    ])

def create_app():
    global application
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.Regex("^Начать тест 🚀$"), start)],
        states={
            QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("about", about_course))
    application.add_handler(MessageHandler(filters.Regex("^О курсе ✨$"), about_course))
    application.add_handler(CommandHandler("help", help_command))
    application.add_error_handler(error_handler)
    
    return application

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data.clear()
        context.user_data['answers'] = []
        context.user_data['current_question'] = 0
        
        await update.message.reply_text(
            f"Привет! Я {BOT_NAME}, помогу оценить твои качества для работы в тестировании.\n\n"
            "Ответь на 5 вопросов по шкале от 1 до 5:\n"
            "1 😞 - совсем не обо мне\n"
            "5 🤩 - это точно про меня",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await ask_question(update, context)
        return QUESTIONS
    except Exception as e:
        logger.error(f"Start error: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка при запуске. Попробуйте позже.")
        return ConversationHandler.END

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = context.user_data['current_question']
    await update.message.reply_text(questions[current], reply_markup=markup)

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
        await update.message.reply_text("⚠️ Ошибка обработки ответа.")
        return ConversationHandler.END

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = sum(context.user_data['answers'])
    result = f"🔍 Ваш результат: {total}/25\n\n"
    result += "🚀 Отличный результат!" if total >= 20 else "👍 Хороший потенциал!" if total >=15 else "💡 Есть куда расти!"
    await update.message.reply_text(result, reply_markup=main_menu_markup)

async def about_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ О курсе:\n\n"
        "Профессиональное обучение тестированию с нуля.\n\n"
        "Подробнее: @Dmitrii_Fursa8",
        reply_markup=main_menu_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Помощь:\n\n"
        "• Начать тест - /start\n"
        "• О курсе - /about\n"
        "• Отмена теста - /cancel",
        reply_markup=main_menu_markup
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Тест отменён", reply_markup=main_menu_markup)
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Error:", exc_info=context.error)
    if update and update.effective_message:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="😢 Произошла ошибка. Попробуйте позже.",
            reply_markup=main_menu_markup
        )

async def run_bot():
    global application
    application = create_app()
    await application.initialize()
    await application.start()
    logger.info("Bot started")

async def shutdown():
    global application
    if application:
        await application.stop()
        await application.shutdown()

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_bot())
        run_flask()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        loop.run_until_complete(shutdown())
    finally:
        loop.close()

if __name__ == "__main__":
    logger.info(f"Starting {BOT_NAME}")
    main()
