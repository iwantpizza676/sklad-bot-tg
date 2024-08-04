import os
import dotenv
from db_interactions import DBInteraction
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler

# Загружем переменные среды
dotenv.load_dotenv(override=True)
TELEGRAM_HTTP_API_TOKEN = os.getenv('TELEGRAM_HTTP_API_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')

# Создаем объект взаимодействия с базой данных
DBInteraction = DBInteraction('sklad.db')
table_name = 'items'

# Состояния (states)
ADD_ITEM, TYPING_NAME, TYPING_QUANTITY, TYPING_PHOTO_URL, DELETE_ITEM, TYPING_ITEM_ID, CHANGE_QUANTITY, TYPING_NEW_QUANTITY = range(8)

# Папка для фотографий
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(BASE_DIR, 'photos')
os.makedirs(PHOTO_DIR, exist_ok=True)  # Создаем папку для фото, если ее нет


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Выберите действие:', reply_markup=await start_keyboard())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Добавить предмет":
        context.user_data.clear()
        await update.message.reply_text("Введите название предмета:", reply_markup=back_keyboard())
        return TYPING_NAME
    elif text == "Удалить предмет":
        await update.message.reply_text("Введите ID предмета для удаления:", reply_markup=back_keyboard())
        return TYPING_ITEM_ID
    elif text == "Показать все предметы":
        await get_all_items_command(update, context)
    elif text == "Изменить кол-во предмета":  # Новая кнопка
        await update.message.reply_text("Введите ID предмета:", reply_markup=back_keyboard())
        return CHANGE_QUANTITY  # Переходим в состояние изменения количества
    elif text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END


async def add_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":  # Проверяем, нажата ли кнопка "Назад"
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Введите количество:", reply_markup=back_keyboard())
    return TYPING_QUANTITY


async def add_item_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END
    context.user_data['quantity'] = update.message.text
    await update.message.reply_text("Загрузите фотографию:", reply_markup=back_keyboard())  # Изменено сообщение
    return TYPING_PHOTO_URL  # Переходим к ожиданию фотографии, не завершая состояние


async def add_item_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END

    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        filename = f"photo_{update.message.message_id}.jpg"
        photo_path = os.path.join(PHOTO_DIR, filename)
        await photo_file.download_to_drive(photo_path)

        # Генерируем относительную ссылку на фото
        photo_url = f"/photos/{filename}"

        context.user_data['photo'] = photo_url  # Сохраняем ссылку в user_data
        await add_item_command(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, загрузите фотографию.", reply_markup=back_keyboard())
        return TYPING_PHOTO_URL  # Остаемся в том же состоянии, если фото не загружено


async def delete_item_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END

    try:
        item_id = int(update.message.text)
        await remove_item_command(update, context, item_id)  # Передаем item_id в remove_item_command
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Неверный формат ID. Пожалуйста, введите число.", reply_markup=back_keyboard())
        return TYPING_ITEM_ID


async def change_item_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END

    try:
        item_id = int(update.message.text)
        context.user_data['item_id'] = item_id
        await update.message.reply_text("Введите новое количество:", reply_markup=back_keyboard())
        return TYPING_NEW_QUANTITY
    except ValueError:
        await update.message.reply_text("Неверный формат ID. Пожалуйста, введите число.", reply_markup=back_keyboard())
        return CHANGE_QUANTITY
    
    
async def add_item_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        DBInteraction.add_item(
            context.user_data['name'],
            context.user_data['quantity'],
            context.user_data['photo']
        )
        await update.message.reply_text("Предмет успешно добавлен", reply_markup=await start_keyboard())
    except Exception as e:
        await update.message.reply_text(f"Произошла непредвиденная ошибка: {e}", reply_markup=await start_keyboard())



async def start_keyboard():
    keyboard = [
        [KeyboardButton("Добавить предмет"), KeyboardButton("Изменить кол-во предмета")],  # Добавлена кнопка
        [KeyboardButton("Удалить предмет")],
        [KeyboardButton("Показать все предметы")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def back_keyboard():
    keyboard = [[KeyboardButton("Назад")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено", reply_markup=start_keyboard())
    return ConversationHandler.END


async def remove_item_command(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id):
    try:
        DBInteraction.remove_item(item_id)
        await update.message.reply_text(f"Предмет с ID {item_id} удален", reply_markup=await start_keyboard())
    except Exception as e:
        await update.message.reply_text(f"Ошибка при удалении предмета: {e}", reply_markup=await start_keyboard())


async def get_all_items_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = DBInteraction.get_all_items(table_name)
        await update.message.reply_text("Список всех предметов\n[id] название - кол-во: \n\n" + format_data(response))
    except Exception as e:
        await update.message.reply_text(f"Ошибка при попытке получить данные из таблицы: {e}")


async def change_item_quantity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_quantity = int(update.message.text)
        item_id = context.user_data['item_id']
        DBInteraction.change_quantity(new_quantity, item_id)
        await update.message.reply_text(f"Количество предмета с ID {item_id} изменено на {new_quantity}", reply_markup=await start_keyboard())
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Неверный формат количества. Пожалуйста, введите число.", reply_markup=back_keyboard())
        return TYPING_NEW_QUANTITY
    except Exception as e:
        await update.message.reply_text(f"Ошибка при изменении количества: {e}", reply_markup=await start_keyboard())
        return ConversationHandler.END


def format_data(data):
    formatted_data = [
        {'id': item[0], 'name': item[1], 'quantity': item[2]} for item in data
    ]

    formatted_strings = [
        f"[ {item['id']} ] {item['name']} - {item['quantity']} шт"
        for item in formatted_data
    ]

    return '\n'.join(formatted_strings)
    
    
if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TELEGRAM_HTTP_API_TOKEN).build()

    app.add_handler(CommandHandler('start', start))  # Добавляем обработчик команды /start

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            TYPING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_name)],
            TYPING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_quantity)],
            TYPING_PHOTO_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_photo),  # Обработчик текста
                MessageHandler(filters.PHOTO, add_item_photo)  # Обработчик фотографий
            ],
            TYPING_ITEM_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_item_id)],
            CHANGE_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_item_quantity)],
            TYPING_NEW_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_item_quantity_command)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)  # Добавляем обработчик диалога после обработчика команды /start

    print('Polling...')
    app.run_polling(poll_interval=3)
    
    