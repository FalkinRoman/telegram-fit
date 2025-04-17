import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from data_manager import data_manager
import os
from dotenv import load_dotenv
from telegram.error import Forbidden

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен и ID админа из переменных окружения
ADMIN_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_USER_ID'))
BOT_TOKEN = os.getenv('BOT_TOKEN')  # Токен основного бота для отправки сообщений

# Состояния
WAITING_MESSAGE = 1
WAITING_COMMENT = 2
SELECTING_USER = 3  # Новое состояние для выбора пользователя
ENTERING_MESSAGE = 4  # Новое состояние для ввода сообщения

# Создаем основную клавиатуру админа
admin_keyboard = ReplyKeyboardMarkup([
    ['📊 Общая статистика', '👥 Список участников'],
    ['📈 Прогресс за день', '📤 Экспорт'],
    ['✉️ Отправить сообщение']
], resize_keyboard=True)

# Создаем клавиатуру для отмены
cancel_keyboard = ReplyKeyboardMarkup([['❌ Отмена']], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало работы с админ-ботом"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Извините, у вас нет доступа к админ-панели.")
        return
    
    await update.message.reply_text(
        "Админ панель FitTracking Bot",
        reply_markup=admin_keyboard
    )

async def show_general_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает общую статистику марафона"""
    if update.effective_user.id != ADMIN_ID:
        return
        
    users = data_manager.get_all_users()
    
    if not users:
        await update.message.reply_text(
            "Пока нет активных участников.",
            reply_markup=admin_keyboard
        )
        return
    
    total_users = len(users)
    active_today = 0
    total_meals = 0
    total_cardio = 0
    total_strength = 0
    weight_progress = 0
    
    message = "📊 Общая статистика марафона:\n\n"
    
    for user in users:
        stats = data_manager.get_user_stats(user['user_id'])
        user_data = data_manager.load_user_data(user['user_id'])
        
        # Считаем активность за сегодня
        if stats['today_meals'] > 0 or stats['today_cardio'] or stats['today_strength']:
            active_today += 1
            
        # Общая статистика
        total_meals += len(user_data.get('meals', []))
        total_cardio += len(user_data.get('cardio', []))
        total_strength += len(user_data.get('strength', []))
        
        # Считаем прогресс по весу
        if stats['weight_diff'] < 0:
            weight_progress += 1
    
    message += (
        f"👥 Всего участников: {total_users}\n"
        f"📱 Активны сегодня: {active_today}\n\n"
        f"📊 Общие показатели:\n"
        f"🍽 Приемов пищи: {total_meals}\n"
        f"🏃‍♂️ Кардио тренировок: {total_cardio}\n"
        f"💪 Силовых тренировок: {total_strength}\n"
        f"⚖️ Снижают вес: {weight_progress} из {total_users}\n\n"
        f"💯 Средняя активность: {(active_today/total_users*100):.1f}%\n"
    )
    
    await update.message.reply_text(message, reply_markup=admin_keyboard)

async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список всех пользователей"""
    if update.effective_user.id != ADMIN_ID:
        return
        
    users = data_manager.get_all_users()
    
    if not users:
        await update.message.reply_text(
            "Пока нет активных участников.",
            reply_markup=admin_keyboard
        )
        return
    
    message = "👥 Список участников:\n\n"
    for user in users:
        stats = data_manager.get_user_stats(user['user_id'])
        message += (
            f"• {user['name']}\n"
            f"  ID: {user['user_id']}\n"
            f"  Прогресс: {stats['marathon_progress']}/90 дней\n"
            f"  Вес: {stats['weight_diff']:+.1f} кг\n\n"
        )
    
    await update.message.reply_text(message, reply_markup=admin_keyboard)

async def show_daily_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает прогресс за день"""
    if update.effective_user.id != ADMIN_ID:
        return
        
    users = data_manager.get_all_users()
    
    if not users:
        await update.message.reply_text(
            "Пока нет активных участников.",
            reply_markup=admin_keyboard
        )
        return
    
    today = datetime.now()
    is_friday = today.weekday() == 4  # 4 = пятница
    
    message = f"📈 Прогресс за {today.strftime('%d.%m.%Y')}:\n\n"
    
    for user in users:
        stats = data_manager.get_user_stats(user['user_id'])
        
        meals_status = "✅" if stats['today_meals'] >= 3 else "❌"
        cardio_status = "✅" if stats['today_cardio'] else "❌"
        strength_status = "✅" if stats['today_strength'] else "❌"
        weight_status = "✅" if is_friday and stats['current_weight'] else "❌" if is_friday else "➖"
        
        all_done = (
            stats['today_meals'] >= 3 and 
            stats['today_cardio'] and 
            stats['today_strength'] and 
            (not is_friday or (is_friday and stats['current_weight']))
        )
        
        status_emoji = "🌟" if all_done else "⚠️"
        
        message += (
            f"{status_emoji} {user['name']}:\n"
            f"🍽 Питание (3+): {meals_status} ({stats['today_meals']})\n"
            f"🏃‍♂️ Кардио: {cardio_status}\n"
            f"💪 Силовая: {strength_status}\n"
        )
        
        if is_friday:
            message += f"⚖️ Взвешивание: {weight_status}\n"
        
        message += "\n"
    
    await update.message.reply_text(message, reply_markup=admin_keyboard)

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспортирует данные всех пользователей"""
    if update.effective_user.id != ADMIN_ID:
        return
        
    users = data_manager.get_all_users()
    
    if not users:
        await update.message.reply_text(
            "Пока нет активных участников.",
            reply_markup=admin_keyboard
        )
        return
    
    message = "📤 Экспорт данных:\n\n"
    
    for user in users:
        user_data = data_manager.load_user_data(user['user_id'])
        stats = data_manager.get_user_stats(user['user_id'])
        
        message += (
            f"👤 {user['name']} (ID: {user['user_id']}):\n"
            f"Старт: {user['start_date']}\n"
            f"Прогресс: {stats['marathon_progress']}/90 дней\n"
            f"Всего активностей:\n"
            f"- Приемов пищи: {len(user_data.get('meals', []))}\n"
            f"- Кардио: {len(user_data.get('cardio', []))}\n"
            f"- Силовых: {len(user_data.get('strength', []))}\n"
        )
        
        if stats['current_weight']:
            message += (
                f"Вес: {stats['current_weight']:.1f} кг "
                f"(изменение: {stats['weight_diff']:+.1f} кг)\n"
            )
        
        message += "\n"
    
    await update.message.reply_text(message, reply_markup=admin_keyboard)

async def start_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс отправки сообщения"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    users = data_manager.get_all_users()
    if not users:
        await update.message.reply_text(
            "Пока нет активных участников.",
            reply_markup=admin_keyboard
        )
        return ConversationHandler.END
    
    # Создаем клавиатуру со списком пользователей и кнопкой отмены
    user_buttons = [[f"👤 {user['name']} (ID: {user['user_id']})"] for user in users]
    user_buttons.append(['❌ Отмена'])
    user_keyboard = ReplyKeyboardMarkup(user_buttons, resize_keyboard=True)
    
    await update.message.reply_text(
        "Выберите пользователя для отправки сообщения:",
        reply_markup=user_keyboard
    )
    return SELECTING_USER

async def handle_user_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор пользователя"""
    if update.message.text == '❌ Отмена':
        await update.message.reply_text(
            "Отправка сообщения отменена.",
            reply_markup=admin_keyboard
        )
        return ConversationHandler.END
    
    # Извлекаем ID пользователя из текста кнопки
    try:
        user_id = update.message.text.split('ID: ')[1].strip(')')
        user_name = update.message.text.split('👤 ')[1].split(' (ID:')[0]
        
        # Сохраняем данные в контексте
        context.user_data['selected_user'] = {
            'id': user_id,
            'name': user_name
        }
        
        # Создаем клавиатуру для ввода сообщения
        message_keyboard = ReplyKeyboardMarkup([
            ['❌ Отмена', '↩️ Назад']
        ], resize_keyboard=True)
        
        await update.message.reply_text(
            f"Введите сообщение для пользователя {user_name}:",
            reply_markup=message_keyboard
        )
        return ENTERING_MESSAGE
    except Exception as e:
        logger.error(f"Ошибка при выборе пользователя: {e}")
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте еще раз.",
            reply_markup=admin_keyboard
        )
        return ConversationHandler.END

async def handle_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод сообщения"""
    if update.message.text == '❌ Отмена':
        await update.message.reply_text(
            "Отправка сообщения отменена.",
            reply_markup=admin_keyboard
        )
        return ConversationHandler.END
    
    if update.message.text == '↩️ Назад':
        return await start_send_message(update, context)
    
    selected_user = context.user_data.get('selected_user')
    if not selected_user:
        await update.message.reply_text(
            "Ошибка: пользователь не выбран.",
            reply_markup=admin_keyboard
        )
        return ConversationHandler.END
    
    message_text = update.message.text
    
    try:
        # Создаем новый экземпляр бота для отправки сообщения
        main_bot = Application.builder().token(BOT_TOKEN).build()
        async with main_bot:
            await main_bot.bot.send_message(
                chat_id=selected_user['id'],
                text=f"👨‍🏫 Сообщение от тренера FitTracking Bot:\n\n{message_text}"
            )
            await update.message.reply_text(
                f"✅ Сообщение отправлено пользователю {selected_user['name']}",
                reply_markup=admin_keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при отправке сообщения: {str(e)}",
            reply_markup=admin_keyboard
        )
    
    # Очищаем данные пользователя
    if 'selected_user' in context.user_data:
        del context.user_data['selected_user']
    
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений"""
    if update.effective_user.id != ADMIN_ID:
        return
        
    text = update.message.text
    
    if text == '📊 Общая статистика':
        await show_general_stats(update, context)
    elif text == '👥 Список участников':
        await show_users_list(update, context)
    elif text == '📈 Прогресс за день':
        await show_daily_progress(update, context)
    elif text == '📤 Экспорт':
        await export_data(update, context)
    elif text == '✉️ Отправить сообщение':
        return await start_send_message(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logging.error(f"Exception while handling an update: {context.error}")
    
    if isinstance(context.error, Forbidden):
        if "bot was blocked by the user" in str(context.error):
            logging.warning(f"Бот был заблокирован пользователем")
            return
    
    # Для других ошибок можно отправить сообщение админу
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка при обработке запроса."
        )

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки админом"""
    query = update.callback_query
    await query.answer()
    
    action, user_id, meal_number = query.data.split('_')
    user_id = str(user_id)
    logger.info(f"Получен callback: action={action}, user_id={user_id}, meal_number={meal_number}")
    
    if action == 'comment':
        # Сохраняем данные в контексте
        context.user_data['waiting_comment_for'] = {
            'user_id': user_id,
            'meal_number': meal_number
        }
        logger.info(f"Сохранены данные для комментария: {context.user_data['waiting_comment_for']}")
        
        # Отправляем сообщение с просьбой ввести комментарий
        await query.message.reply_text(
            '💬 Напиши комментарий для пользователя:',
            reply_markup=ForceReply(selective=True)
        )
        return WAITING_COMMENT
    
    message = ''
    if action == 'approve':
        message = '✅ Тренер одобрил твой приём пищи!'
    elif action == 'reject':
        message = '❌ Тренер рекомендует пересмотреть состав приёма пищи.'
    
    try:
        # Создаем экземпляр основного бота для отправки сообщений
        main_bot = Application.builder().token(BOT_TOKEN).build()
        async with main_bot:
            await main_bot.bot.send_message(chat_id=user_id, text=message)
            await query.message.reply_text('Ответ отправлен пользователю ✅')
    except Exception as e:
        logger.error(f"Ошибка при отправке ответа пользователю: {e}")
        await query.message.reply_text('❌ Ошибка при отправке ответа пользователю')

async def handle_admin_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка комментария от админа"""
    comment_data = context.user_data.get('waiting_comment_for')
    if not comment_data:
        logger.error("Не найдены данные для комментария в контексте")
        await update.message.reply_text(
            '❌ Ошибка: данные комментария не найдены',
            reply_markup=admin_keyboard
        )
        return ConversationHandler.END
    
    user_id = comment_data['user_id']
    meal_number = comment_data['meal_number']
    comment = update.message.text
    
    logger.info(f"Отправка комментария пользователю {user_id} для приема пищи {meal_number}")
    
    try:
        # Создаем экземпляр основного бота для отправки сообщений
        main_bot = Application.builder().token(BOT_TOKEN).build()
        async with main_bot:
            message = (
                f'👨‍🏫 Комментарий от тренера FitTracking Bot к приему пищи #{meal_number}:\n\n'
                f'{comment}'
            )
            
            # Отправляем сообщение пользователю без кнопки ответа
            sent_message = await main_bot.bot.send_message(
                chat_id=user_id,
                text=message
            )
            
            if sent_message:
                logger.info(f"Комментарий успешно отправлен пользователю {user_id}")
                await update.message.reply_text(
                    '✅ Комментарий отправлен пользователю',
                    reply_markup=admin_keyboard
                )
            else:
                logger.error("Не удалось отправить комментарий")
                await update.message.reply_text(
                    '❌ Ошибка при отправке комментария',
                    reply_markup=admin_keyboard
                )
    except Exception as e:
        logger.error(f"Ошибка при отправке комментария: {e}")
        await update.message.reply_text(
            '❌ Ошибка при отправке комментария',
            reply_markup=admin_keyboard
        )
    finally:
        # Очищаем данные из контекста
        del context.user_data['waiting_comment_for']
    
    return ConversationHandler.END

def main():
    """Запуск бота"""
    application = Application.builder().token(ADMIN_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    
    # Обработчик отправки сообщений
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^✉️ Отправить сообщение$'), start_send_message)],
        states={
            SELECTING_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_selection)],
            ENTERING_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_input)]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    application.add_handler(conv_handler)
    
    # Обработчик комментариев
    comment_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_admin_callback, pattern='^comment_')],
        states={
            WAITING_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_comment)]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    application.add_handler(comment_handler)
    
    # Обработчик остальных callback-кнопок (одобрить/отклонить)
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern='^(approve|reject)_'))
    
    # Обработчик остальных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main() 