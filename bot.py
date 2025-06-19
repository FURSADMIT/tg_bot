import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or "ВАШ_ТОКЕН_БОТА"
BOT_NAME = "@QaPollsBot"

# Меню и вопросы
main_menu = [
    [KeyboardButton("Начать тест 🚀"), KeyboardButton("О курсе ✨")],
    [KeyboardButton("Помощь ❓")]
]
main_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)

questions = [
    "1. Замечаю опечатки в текстах",
    "2. Люблю решать головоломки",
    "3. Многократно проверяю одно и то же",
    "4. Изучаю все функции новых приложений",
    "5. Интересуюсь IT и технологиями"
]
answers_markup = ReplyKeyboardMarkup([["1 😞", "2 😐", "3 😊", "4 😃", "5 🤩"]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я {BOT_NAME}.\nВыберите действие:",
        reply_markup=main_markup
    )

async def about_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ *Курс по тестированию* ✨\n\n"
        "Профессиональное обучение с нуля до трудоустройства.\n\n"
        "Подробнее: @Dmitrii_Fursa8",
        parse_mode="Markdown",
        reply_markup=main_markup
    )

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['answers'] = []
    context.user_data['question'] = 0
    await ask_question(update, context)
    return 1

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q_num = context.user_data['question']
    await update.message.reply_text(
        questions[q_num],
        reply_markup=answers_markup
    )

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        answer = update.message.text.split()[0]
        if not answer.isdigit() or not 1 <= int(answer) <= 5:
            await update.message.reply_text("Пожалуйста, выберите вариант от 1 до 5")
            return 1
        
        context.user_data['answers'].append(int(answer))
        context.user_data['question'] += 1
        
        if context.user_data['question'] < len(questions):
            await ask_question(update, context)
            return 1
        
        total = sum(context.user_data['answers'])
        await update.message.reply_text(
            f"🔍 Ваш результат: {total}/25\n\n" +
            ("Отлично! 🚀" if total >= 20 else
             "Хорошо! 👍" if total >= 15 else
             "Есть куда расти! 💪"),
            reply_markup=main_markup
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте снова.",
            reply_markup=main_markup
        )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Тест отменён", reply_markup=main_markup)
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^Начать тест 🚀$"), start_test),
            CommandHandler("start", start_test)
        ],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("about", about_course))
    app.add_handler(MessageHandler(filters.Regex("^О курсе ✨$"), about_course))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(MessageHandler(filters.Regex("^Помощь ❓$"), start))
    
    app.run_polling()

if __name__ == "__main__":
    logger.info("Starting bot...")
    main()
