import os
import dotenv
from db_interactions import DBInteraction
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

# Load api keys
dotenv.load_dotenv(override=True)
TELEGRAM_HTTP_API_TOKEN = os.getenv('TELEGRAM_HTTP_API_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')

# Database interaction object
DBInteraction = DBInteraction('sklad.db')
table_name = 'items'

# States
ADD_ITEM, TYPING_NAME, TYPING_QUANTITY, TYPING_PHOTO_URL, DELETE_ITEM, TYPING_ITEM_ID, CHANGE_QUANTITY, TYPING_NEW_QUANTITY, SHOW_ALL_ITEMS, GET_ITEM_DETAILS, ISSUE_ITEM, TYPING_ISSUE_ITEM_ID, CHOOSE_ISSUE_QUANTITY = range(13)

# Create a photo folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(BASE_DIR, 'photos')
os.makedirs(PHOTO_DIR, exist_ok=True)


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
        return SHOW_ALL_ITEMS 
    elif text == "Изменить кол-во предмета":
        await update.message.reply_text("Введите ID предмета:", reply_markup=back_keyboard())
        return CHANGE_QUANTITY 
    elif text == "Выдать товар":  # Новая кнопка
        await update.message.reply_text("Введите ID предмета:", reply_markup=back_keyboard())
        return ISSUE_ITEM
    elif text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END


async def add_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":
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
    await update.message.reply_text("Загрузите фотографию:", reply_markup=back_keyboard())
    return TYPING_PHOTO_URL  # Go to waiting for photo without closing the state


async def add_item_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END

    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        filename = f"photo_{update.message.message_id}.jpg"
        photo_path = os.path.join(PHOTO_DIR, filename)
        await photo_file.download_to_drive(photo_path)

        # Create relative link to the photo
        photo_url = f"photos/{filename}"

        context.user_data['photo'] = photo_url  # Save url to user_data
        await add_item_command(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, загрузите фотографию.", reply_markup=back_keyboard())
        return TYPING_PHOTO_URL  # Remain in the same state if no photo is uploaded


async def delete_item_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END

    try:
        item_id = int(update.message.text)
        # item_id -> remove_item_command
        await remove_item_command(update, context, item_id)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Неверный формат ID. Пожалуйста, введите число.", reply_markup=back_keyboard())
        return TYPING_ITEM_ID


async def issue_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END

    try:
        item_id = int(update.message.text)
        item_details = DBInteraction.get_item_by_id(item_id)
        if item_details:
            item = item_details[0]

            # Format output (photo with caption)
            caption = f"""
Id - {item[0]}
{item[1]}
Кол-во - {item[2]}
"""
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=open(os.path.join(BASE_DIR, item[3]), 'rb'),
                caption=caption
            )

            context.user_data['item_id'] = item_id
            await update.message.reply_text("Выберите количество для выдачи:", reply_markup=await issue_quantity_keyboard())
            return CHOOSE_ISSUE_QUANTITY
        else:
            await update.message.reply_text("Предмет с таким ID не найден.", reply_markup=back_keyboard())
            return ISSUE_ITEM  # Remain in the ID entry state if the item is not found
    except ValueError:
        await update.message.reply_text("Неверный формат ID. Пожалуйста, введите число.", reply_markup=back_keyboard())
        return ISSUE_ITEM


async def handle_choose_issue_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    item_id = context.user_data['item_id']

    if text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END
    elif text == "Свое кол-во":
        await update.message.reply_text("Введите количество для выдачи:", reply_markup=back_keyboard())
        return TYPING_NEW_QUANTITY
    else:
        try:
            quantity_to_issue = int(text)
            item_details = DBInteraction.get_item_by_id(item_id)[0]
            current_quantity = item_details[2]

            if current_quantity >= quantity_to_issue:
                new_quantity = current_quantity - quantity_to_issue
                await change_item_quantity_command(update, context, new_quantity)
            else:
                await update.message.reply_text(
                    f"Недостаточно товара на складе. Текущее количество: {current_quantity}",
                    reply_markup=await start_keyboard()
                )
            return ConversationHandler.END # To end dialogue after error 
        except ValueError:
            await update.message.reply_text("Неверный формат количества. Пожалуйста, введите число.", reply_markup=back_keyboard())
            return CHOOSE_ISSUE_QUANTITY
        

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
        [KeyboardButton("Добавить предмет"), KeyboardButton("Изменить кол-во предмета")],
        [KeyboardButton("Удалить предмет"), KeyboardButton("Выдать товар")],  # Добавлена кнопка
        [KeyboardButton("Показать все предметы")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def back_keyboard():
    keyboard = [[KeyboardButton("Назад")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def details_keyboard():
    keyboard = [
        [KeyboardButton("Подробнее")],
        [KeyboardButton("Назад")]
    ]
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
        await update.message.reply_text(
            "Список всех предметов\n[id] название - кол-во: \n\n" + format_data(response),
            reply_markup=await details_keyboard()
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка при попытке получить данные из таблицы: {e}")


async def handle_show_all_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Подробнее":
        await update.message.reply_text("Введите ID предмета:", reply_markup=back_keyboard())
        return GET_ITEM_DETAILS
    elif text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END


async def get_item_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Назад":
        await update.message.reply_text("Действие отменено", reply_markup=await start_keyboard())
        return ConversationHandler.END

    try:
        item_id = int(update.message.text)
        item_details = DBInteraction.get_item_by_id(item_id)
        if item_details:
            item = item_details[0]

            caption = f"""
Id - {item[0]}
{item[1]}
Кол-во - {item[2]}
"""

            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=open(os.path.join(item[3]), 'rb'),
                caption=caption,
                reply_markup=await start_keyboard()
            )
        else:
            await update.message.reply_text("Предмет с таким ID не найден.", reply_markup=await start_keyboard())
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Неверный формат ID. Пожалуйста, введите число.", reply_markup=back_keyboard())
        return GET_ITEM_DETAILS


async def change_item_quantity_command(update: Update, context: ContextTypes.DEFAULT_TYPE, new_quantity=None):
    try:
        if new_quantity is None:
            new_quantity = int(update.message.text)
        item_id = context.user_data['item_id']
        DBInteraction.change_quantity(new_quantity, item_id)
        await update.message.reply_text(
            f"Количество предмета с ID {item_id} изменено на {new_quantity}",
            reply_markup=await start_keyboard()
        )
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


async def issue_quantity_keyboard():
    keyboard = [
        [KeyboardButton("1"), KeyboardButton("2"), KeyboardButton("3")],
        [KeyboardButton("5"), KeyboardButton("Свое кол-во")],
        [KeyboardButton("Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TELEGRAM_HTTP_API_TOKEN).build()

    # Start command handler
    app.add_handler(CommandHandler('start', start))

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            TYPING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_name)],
            TYPING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_quantity)],
            TYPING_PHOTO_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_photo),
                MessageHandler(filters.PHOTO, add_item_photo) 
            ],
            TYPING_ITEM_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_item_id)],
            CHANGE_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_item_quantity)],
            TYPING_NEW_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, change_item_quantity_command)],
            SHOW_ALL_ITEMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_show_all_items)],
            GET_ITEM_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_details)],
            ISSUE_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, issue_item)],
            CHOOSE_ISSUE_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choose_issue_quantity)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(conv_handler)

    print('Polling...')
    app.run_polling(poll_interval=1)
    
    