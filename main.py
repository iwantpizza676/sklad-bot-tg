import os
import dotenv
from db_interactions import DBInteraction
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Загружем переменные среды
dotenv.load_dotenv(override=True)
TELEGRAM_HTTP_API_TOKEN = os.getenv('TELEGRAM_HTTP_API_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')

# Создаем объект взаимодействия с базой данных
DBInteraction = DBInteraction('sklad.db')
table_name = 'items'

# Состояния (states)
ADD_ITEM, TYPING_NAME, TYPING_QUANTITY, TYPING_PHOTO_URL = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Добавить предмет")],
        [KeyboardButton("Удалить предмет")],
        [KeyboardButton("Показать все предметы")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Выберите действие:', reply_markup=reply_markup)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Добавить предмет":
        await add_item_command(update, context)
    elif text == "Удалить предмет":
        await remove_item_command(update, context)
    elif text == "Показать все предметы":
        await get_all_items_command(update, context)


async def add_item_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        DBInteraction.add_item('bam', '111', 'Фото3')
        await update.message.reply_text("Предмет успешно добавлен")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при добавлении предмета: {e}") 


async def remove_item_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        DBInteraction.remove_item(5)
        await update.message.reply_text("Предмет удален")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при удалении предмета: {e}")


async def get_all_items_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = DBInteraction.get_all_items(table_name)
        await update.message.reply_text("Список всех предметов: \n" + str(response))
    except Exception as e:
        await update.message.reply_text(f"Ошибка при попытке получить данные из таблицы: {e}")


if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TELEGRAM_HTTP_API_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print('Polling...')
    app.run_polling(poll_interval=3)
    
    