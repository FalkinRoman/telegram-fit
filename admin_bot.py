import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен админ-бота
ADMIN_BOT_TOKEN = "7309333364:AAEtFe6dumrnmkuhE_X-XdwfsY27nC6YbHE"

# Состояния
WAITING_COMMENT = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        'Привет! Я админ-бот для FitTracking.\n'
        'Через меня ты будешь получать уведомления о действиях пользователей и управлять их активностью.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        'Доступные команды:\n'
        '/start - Начать работу с ботом\n'
        '/help - Показать это сообщение\n'
        '/status - Проверить статус бота'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    await update.message.reply_text(
        '✅ Бот активен и готов к работе\n'
        f'⏰ Текущее время: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()  # Отвечаем на callback, чтобы убрать часики

    action, user_id, meal_number = query.data.split('_')
    user_id = int(user_id)

    main_bot = Application.builder().token("8059566571:AAHBiyib0-MNkXauZjotBPajo8LzI7O203Q").build()

    try:
        if action == "approve":
            await main_bot.bot.send_message(
                chat_id=user_id,
                text=f'✅ Тренер одобрил твой {meal_number} приём пищи!'
            )
            await query.edit_message_caption(
                caption=f'{query.message.caption}\n\n✅ Одобрено',
                reply_markup=None
            )
        
        elif action == "reject":
            await main_bot.bot.send_message(
                chat_id=user_id,
                text=f'❌ Тренер рекомендует пересмотреть состав {meal_number} приёма пищи.'
            )
            await query.edit_message_caption(
                caption=f'{query.message.caption}\n\n❌ Отклонено',
                reply_markup=None
            )
        
        elif action == "comment":
            context.user_data['comment_for'] = {
                'user_id': user_id,
                'meal_number': meal_number
            }
            await query.message.reply_text(
                'Напиши комментарий для пользователя:',
            )
            return WAITING_COMMENT

    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        await query.message.reply_text(f"Произошла ошибка: {e}")
    finally:
        await main_bot.shutdown()

async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка комментария пользователю"""
    comment_data = context.user_data.get('comment_for')
    if not comment_data:
        return ConversationHandler.END

    user_id = comment_data['user_id']
    meal_number = comment_data['meal_number']
    comment = update.message.text

    main_bot = Application.builder().token("8059566571:AAHBiyib0-MNkXauZjotBPajo8LzI7O203Q").build()

    try:
        await main_bot.bot.send_message(
            chat_id=user_id,
            text=f'💬 Комментарий тренера к {meal_number} приёму пищи:\n\n{comment}'
        )
        await update.message.reply_text('✅ Комментарий отправлен пользователю')
    except Exception as e:
        logger.error(f"Ошибка при отправке комментария: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")
    finally:
        await main_bot.shutdown()
        del context.user_data['comment_for']

    return ConversationHandler.END

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(ADMIN_BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))

    # Обработчик callback-кнопок
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback)],
        states={
            WAITING_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_comment)]
        },
        fallbacks=[]
    )
    application.add_handler(conv_handler)

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main() 