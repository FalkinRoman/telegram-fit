import os
import logging
from datetime import datetime, time, timedelta
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext, ConversationHandler, CallbackQueryHandler

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_BOT_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_USER_ID'))  # Конвертируем в число
MARATHON_DAYS = 90  # Длительность марафона в днях

# Состояния разговора
WAITING_NAME = 1
WAITING_MEAL_NUMBER = 2
WAITING_FOOD_PHOTO = 3
WAITING_ADMIN_REPLY = 4
WAITING_WEIGHT = 5
PHOTO_PROGRESS = 25

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Клавиатуры
meal_keyboard = ReplyKeyboardMarkup([
    ['1️⃣ Первый приём', '2️⃣ Второй приём'],
    ['3️⃣ Третий приём', '4️⃣ Четвёртый приём'],
    ['5️⃣ Пятый приём', '↩️ Назад']
], resize_keyboard=True)

# Создаем основную клавиатуру
main_keyboard = ReplyKeyboardMarkup([
    ['🍽 Приём пищи', '🏃‍♂️ Кардио'],
    ['💪 Силовая', '⚖️ Взвеситься'],
    ['📊 Статистика', '📋 Правила'],
    ['💪 Мотивация']
], resize_keyboard=True)

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало разговора и запрос имени"""
    await update.message.reply_text(
        'Привет! Как я могу к тебе обращаться? 😊',
        reply_markup=ForceReply(selective=True)
    )
    return WAITING_NAME

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, message: str, photo_file_id: str = None, reply_markup: InlineKeyboardMarkup = None):
    """Отправка уведомления админу через админ-бота"""
    try:
        admin_bot = Application.builder().token(ADMIN_BOT_TOKEN).build()
        async with admin_bot:
            if photo_file_id:
                # Получаем файл через основного бота
                file = await context.bot.get_file(photo_file_id)
                photo_bytes = await file.download_as_bytearray()
                
                # Отправляем фото через админ-бота
                from io import BytesIO
                photo_stream = BytesIO(photo_bytes)
                await admin_bot.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=photo_stream,
                    caption=message,
                    reply_markup=reply_markup
                )
            else:
                await admin_bot.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=message
                )
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления админу: {e}")
        raise

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение имени пользователя и начало работы"""
    user_name = update.message.text
    user_id = update.effective_user.id
    context.user_data['name'] = user_name
    context.user_data['start_date'] = datetime.now()  # Устанавливаем дату начала марафона
    
    # Уведомление админу о новом пользователе
    admin_message = (
        f'🆕 Новый участник марафона!\n\n'
        f'👤 Имя: {user_name}\n'
        f'🆔 ID: {user_id}\n'
        f'📅 Дата: {datetime.now().strftime("%d.%m.%Y %H:%M")}'
    )
    await notify_admin(context, admin_message)
    
    await update.message.reply_text(
        f'Привет, {user_name}! 👋\n\n'
        'Я — твой Telegram-бот и личный помощник в марафоне "Пора увидеть свой пресс".\n\n'
        'Вместе с тренером Романом я помогу тебе:\n'
        '🔹 следить за приёмами пищи\n'
        '🔹 подтверждать тренировки\n'
        '🔹 контролировать кардио\n'
        '🔹 фиксировать вес\n'
        '🔹 напоминать о правилах питания\n'
        '🔹 и мотивировать, когда будет тяжело\n\n'
        'Используй кнопки ниже для отметки своих достижений:\n\n'
        '🍽 Я поел - фиксируй каждый приём пищи\n'
        '🏃‍♂️ Кардио - отмечай утренние кардио\n'
        '💪 Силовая - после силовых тренировок\n'
        '⚖️ Взвеситься - замеряем прогресс по воскресеньям\n\n'
        'Готов? Погнали! 💪',
        reply_markup=main_keyboard
    )
    return ConversationHandler.END

async def handle_meal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки 'Я поел'"""
    await update.message.reply_text(
        'Выбери номер приёма пищи:',
        reply_markup=meal_keyboard
    )
    return WAITING_MEAL_NUMBER

async def handle_meal_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора номера приема пищи"""
    text = update.message.text
    
    if text == '↩️ Назад':
        await update.message.reply_text(
            'Вернулись в главное меню',
            reply_markup=main_keyboard
        )
        return ConversationHandler.END
        
    meal_number = text.split()[0]  # Получаем номер из текста (например, "1️⃣" из "1️⃣ Первый приём")
    context.user_data['current_meal'] = meal_number
    
    await update.message.reply_text(
        'Теперь пришли фото своей еды 📸\n'
        'Или нажми ↩️ Назад для возврата в меню',
        reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
    )
    return WAITING_FOOD_PHOTO

async def handle_food_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото еды"""
    user_name = context.user_data.get('name', 'друг')
    message = update.message
    meal_number = context.user_data.get('current_meal', '❓')

    if message.text and message.text == '↩️ Назад':
        await message.reply_text(
            'Вернулись в главное меню',
            reply_markup=main_keyboard
        )
        return ConversationHandler.END

    if not message.photo:
        await message.reply_text(
            'Пожалуйста, отправь фото своей еды 📸\n'
            'Или нажми ↩️ Назад для возврата в меню',
            reply_markup=ReplyKeyboardMarkup([['↩️ Назад']], resize_keyboard=True)
        )
        return WAITING_FOOD_PHOTO

    photo = message.photo[-1]
    
    # Создаем клавиатуру для админа
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{update.effective_user.id}_{meal_number}"),
         InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{update.effective_user.id}_{meal_number}")],
        [InlineKeyboardButton("💬 Комментировать", callback_data=f"comment_{update.effective_user.id}_{meal_number}")]
    ])

    # Отправляем фото админу
    admin_message = (
        f'🍽 Новый приём пищи\n\n'
        f'👤 {user_name}\n'
        f'#️⃣ Приём {meal_number}\n'
        f'⏰ {datetime.now().strftime("%H:%M")}'
    )
    
    try:
        await notify_admin(
            context=context,
            message=admin_message,
            photo_file_id=photo.file_id,
            reply_markup=admin_keyboard
        )
        
        # Увеличиваем счетчик приемов пищи
        context.user_data['meals'] = context.user_data.get('meals', 0) + 1
        
        # Отвечаем пользователю
        await message.reply_text(
            f'Отлично! Приём пищи {meal_number} зафиксирован ✅\n'
            'Фото отправлено тренеру на проверку 👨‍🏫',
            reply_markup=main_keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке фото админу: {e}")
        await message.reply_text(
            '❌ Произошла ошибка при отправке фото тренеру. Попробуй позже.',
            reply_markup=main_keyboard
        )
    
    return ConversationHandler.END

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий админа по фото еды"""
    query = update.callback_query
    action, user_id, meal_number = query.data.split('_')
    user_id = int(user_id)

    if action == 'comment':
        context.user_data['waiting_comment_for'] = user_id
        await query.message.reply_text(
            'Напиши комментарий для пользователя:',
            reply_markup=ForceReply(selective=True)
        )
        return WAITING_ADMIN_REPLY

    message = ''
    if action == 'approve':
        message = '✅ Тренер одобрил твой приём пищи!'
    elif action == 'reject':
        message = '❌ Тренер рекомендует пересмотреть состав приёма пищи.'

    await context.bot.send_message(chat_id=user_id, text=message)
    await query.answer('Ответ отправлен пользователю')

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка комментария админа пользователю"""
    user_id = context.user_data.get('waiting_comment_for')
    if not user_id:
        return ConversationHandler.END

    comment = update.message.text
    await context.bot.send_message(
        chat_id=user_id,
        text=f'💬 Комментарий от тренера:\n\n{comment}'
    )
    del context.user_data['waiting_comment_for']
    await update.message.reply_text('Комментарий отправлен пользователю ✅')
    return ConversationHandler.END

async def handle_cardio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = context.user_data.get('name', 'друг')
    user_id = update.effective_user.id
    
    # Уведомление админу о кардио
    admin_message = (
        f'🏃‍♂️ Кардио выполнено\n\n'
        f'👤 {user_name}\n'
        f'⏰ {datetime.now().strftime("%H:%M")}'
    )
    await notify_admin(context, admin_message)
    
    messages = [
        f'🏃‍♂️ Вау, {user_name}! Кардио засчитано!\n\n'
        '❤️ Твоё сердце говорит спасибо\n'
        '🎯 Жир тает, мышцы крепнут\n'
        '💪 Так держать!',

        f'🔥 Огонь, {user_name}! Кардио в копилку!\n\n'
        '🌟 Каждая тренировка приближает к цели\n'
        '💪 Ты становишься сильнее с каждым днём!',

        f'⚡️ Супер, {user_name}! Кардио выполнено!\n\n'
        '🎯 Пресс всё ближе\n'
        '💪 Продолжай в том же духе!'
    ]
    
    import random
    await update.message.reply_text(random.choice(messages))
    context.user_data['cardio_done'] = True

async def handle_strength(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = context.user_data.get('name', 'друг')
    user_id = update.effective_user.id
    
    # Уведомление админу о силовой тренировке
    admin_message = (
        f'💪 Силовая тренировка выполнена\n\n'
        f'👤 {user_name}\n'
        f'⏰ {datetime.now().strftime("%H:%M")}'
    )
    await notify_admin(context, admin_message)
    
    messages = [
        f'💪 Мощно, {user_name}! Силовая тренировка записана!\n\n'
        '🔥 Мышцы растут, жир уходит\n'
        '🎯 Ты на пути к своему лучшему телу!',

        f'🏋️‍♂️ Отлично поработал, {user_name}!\n\n'
        '💪 Каждая тренировка делает тебя сильнее\n'
        '🎯 Продолжай разносить жир по графику!',

        f'⚡️ Сила есть, {user_name}!\n\n'
        '💪 Тренировка засчитана\n'
        '🔥 Прогресс неизбежен!'
    ]
    
    import random
    await update.message.reply_text(random.choice(messages))
    context.user_data['strength_done'] = True

async def daily_rules(context: CallbackContext):
    """Отправка утренних правил"""
    user_name = context.user_data.get('name', 'друг')
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=(f'🌅 Доброе утро, {user_name}!\n\n'
              '📝 Твои правила на сегодня:\n\n'
              '🍽 Еда:\n'
              '• Простая, без наворотов\n'
              '• Не наедайся на ночь\n'
              '• Белки при голоде (курица, рыба, творог, яйца)\n\n'
              '💧 Вода: 2.5–3 литра в день\n'
              '🍚 Углеводы: только до 15:00\n\n'
              '💪 И помни: пресс куётся на кухне!')
    )

async def daily_report(context: CallbackContext):
    """Отправка вечернего отчета"""
    user_name = context.user_data.get('name', 'друг')
    meals = context.user_data.get('meals', 0)
    cardio = '✅' if context.user_data.get('cardio_done', False) else '❌'
    strength = '✅' if context.user_data.get('strength_done', False) else '❌'
    
    report = (
        f'🌙 {user_name}, подведём итоги дня:\n\n'
        f'🍽 Питание: {"✅" if meals >= 3 else "❌"} ({meals}/3)\n'
        f'🏃‍♂️ Кардио: {cardio}\n'
        f'💪 Силовая: {strength}\n'
        '💧 Вода: 💧💧💧/5\n\n'
        '😊 Как оценишь свой день?\n'
        '🟢 Отлично\n'
        '🟡 Нормально\n'
        '🔴 Можно лучше'
    )
    
    # Отправка отчета админу
    admin_report = (
        f'📊 Дневной отчет участника\n\n'
        f'👤 {user_name}\n'
        f'📅 {datetime.now().strftime("%d.%m.%Y")}\n\n'
        f'🍽 Приемы пищи: {meals}/3\n'
        f'🏃‍♂️ Кардио: {cardio}\n'
        f'💪 Силовая: {strength}\n'
        '💧 Вода: 3/5'
    )
    await notify_admin(context, admin_report)
    
    await context.bot.send_message(chat_id=context.job.chat_id, text=report)
    
    # Сброс счетчиков на следующий день
    context.user_data.clear()
    # Сохраняем имя пользователя
    context.user_data['name'] = user_name

async def get_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать прогресс марафона"""
    user_name = context.user_data.get('name', 'друг')
    start_date = context.user_data.get('start_date')
    
    if not start_date:
        start_date = datetime.now()
        context.user_data['start_date'] = start_date

    current_day = (datetime.now() - start_date).days + 1
    days_left = MARATHON_DAYS - current_day

    if current_day <= MARATHON_DAYS:
        progress = (
            f'📊 Твой прогресс в марафоне:\n\n'
            f'📅 День марафона: {current_day}/{MARATHON_DAYS}\n'
            f'⏳ Осталось дней: {days_left}\n\n'
            f'Сегодня:\n'
            f'🍽 Приёмы пищи: {context.user_data.get("meals", 0)}/3\n'
            f'🏃‍♂️ Кардио: {"✅" if context.user_data.get("cardio_done") else "❌"}\n'
            f'💪 Силовая: {"✅" if context.user_data.get("strength_done") else "❌"}\n\n'
            f'💪 Ты молодец! Продолжай в том же духе!'
        )
    else:
        progress = '🎉 Поздравляем! Ты успешно завершил марафон! 🎉'

    await update.message.reply_text(progress)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику и прогресс пользователя"""
    user_name = context.user_data.get('name', 'друг')
    
    if 'start_date' not in context.user_data:
        context.user_data['start_date'] = datetime.now()
        
    start_date = context.user_data['start_date']
    current_day = (datetime.now() - start_date).days + 1
    days_left = MARATHON_DAYS - current_day

    # Статистика по весу
    weight_history = context.user_data.get('weight_history', [])
    weight_stats = ''
    if weight_history:
        initial_weight = weight_history[0]['weight']
        current_weight = weight_history[-1]['weight']
        total_loss = current_weight - initial_weight
        weight_stats = (
            f'⚖️ Твой путь к прессу:\n'
            f'Стартовый вес: {initial_weight} кг\n'
            f'Текущий вес: {current_weight} кг\n'
            f'Прогресс: {total_loss:+.1f} кг\n'
            f'{"🔥 Жир горит!" if total_loss < 0 else "💪 Время поднажать!"}\n\n'
        )

    # Прогресс марафона
    progress_bar = "🟢" * (current_day // 10) + "⚪️" * ((MARATHON_DAYS - current_day) // 10)
    
    # Статистика за сегодня
    today_meals = context.user_data.get('meals', 0)
    today_cardio = '✅' if context.user_data.get('cardio_done') else '❌'
    today_strength = '✅' if context.user_data.get('strength_done') else '❌'

    stats = (
        f'📊 День {current_day} из {MARATHON_DAYS}\n'
        f'{progress_bar}\n'
        f'⏳ Осталось: {days_left} дней\n\n'
        f'{weight_stats}'
        f'Сегодняшние подвиги:\n'
        f'🍽 Приёмы пищи: {today_meals}/5 {"🎯" if today_meals >= 5 else ""}\n'
        f'🏃‍♂️ Кардио: {today_cardio} {"🔥" if today_cardio == "✅" else ""}\n'
        f'💪 Силовая: {today_strength} {"💪" if today_strength == "✅" else ""}\n\n'
        f'{"🦸‍♂️ Супергерой дня!" if today_meals >= 5 and today_cardio == "✅" and today_strength == "✅" else "💪 Ещё чуть-чуть и будет идеально!"}'
    )

    await update.message.reply_text(stats, reply_markup=main_keyboard)

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать правила марафона"""
    rules_text = (
        "📋 План на 3 месяца:\n\n"
        "🏋️‍♂️ Тренировки:\n"
        "• Силовые 2-3 раза в неделю\n"
        "• Кардио 5-6 раз в неделю (ЧСС 130-150)\n"
        "• HIIT 1-2 раза в неделю\n\n"
        "🍽 Питание:\n"
        "• 4-5 приёмов пищи в день\n"
        "• Углеводы до 15:00\n"
        "• Белок в каждый приём\n"
        "• Ужин лёгкий и за 2-3 часа до сна\n\n"
        "💡 Главные правила:\n"
        "• Голод = ешь белок (курица, рыба, творог)\n"
        "• Вечером только белок + клетчатка\n"
        "• Еда простая, как таблица умножения\n"
        "• Каждый приём пищи через бота\n\n"
        "🎯 Цель: через 3 месяца увидеть пресс!\n"
        "Пресс есть у всех — пора его освободить! 💪"
    )
    await update.message.reply_text(rules_text, reply_markup=main_keyboard)

async def show_motivation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать мотивационное сообщение"""
    motivational_messages = [
        "🔥 Знаешь, почему качать пресс лёжа труднее?\n"
        "Потому что диван оказывает сопротивление! 😅\n\n"
        "Но ты сильнее дивана! Вперёд! 💪",

        "🍕 Пицца спросила, почему я её не ем?\n"
        "А я такой: 'Извини, детка, у меня уже есть кубики!' 😎\n\n"
        "Держим курс на пресс! 🎯",

        "🏃‍♂️ Мой диван по мне скучает...\n"
        "Но пресс сам себя не сделает!\n"
        "Может, стоит их познакомить? 😏\n\n"
        "Планка на диване - тоже планка! 💪",

        "⚖️ Весы сказали, что я потерял 2 кг...\n"
        "Искал везде, но, похоже, они мне больше не нужны! 😅\n\n"
        "Продолжаем терять! 🎯",

        "🍗 Курица спросила: 'Почему я?'\n"
        "А я ответил: 'Потому что ты - путь к прессу!'\n"
        "Теперь она гордится своей миссией 😌\n\n"
        "Ешь белок - будь героем! 💪"
    ]
    import random
    await update.message.reply_text(random.choice(motivational_messages), reply_markup=main_keyboard)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений"""
    text = update.message.text
    
    if text == '🍽 Приём пищи':
        await update.message.reply_text(
            'Выбери номер приёма пищи:',
            reply_markup=meal_keyboard
        )
        return WAITING_MEAL_NUMBER
    elif text == '🏃‍♂️ Кардио':
        await handle_cardio(update, context)
        return ConversationHandler.END
    elif text == '💪 Силовая':
        await handle_strength(update, context)
        return ConversationHandler.END
    elif text == '⚖️ Взвеситься':
        await update.message.reply_text(
            'Пожалуйста, введи свой текущий вес в килограммах (например: 70.5):',
            reply_markup=ForceReply(selective=True)
        )
        return WAITING_WEIGHT
    elif text == '📊 Статистика':
        await show_stats(update, context)
        return ConversationHandler.END
    elif text == '📋 Правила':
        await show_rules(update, context)
        return ConversationHandler.END
    elif text == '💪 Мотивация':
        await show_motivation(update, context)
        return ConversationHandler.END

async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода веса"""
    try:
        weight = float(update.message.text)
        user_name = context.user_data.get('name', 'друг')
        
        # Сохраняем вес в данных пользователя
        if 'weight_history' not in context.user_data:
            context.user_data['weight_history'] = []
        context.user_data['weight_history'].append({
            'date': datetime.now(),
            'weight': weight
        })
        
        # Уведомление админу о новом весе
        admin_message = (
            f'⚖️ Новый замер веса\n\n'
            f'👤 {user_name}\n'
            f'📊 Вес: {weight} кг\n'
            f'📅 {datetime.now().strftime("%d.%m.%Y %H:%M")}'
        )
        await notify_admin(context, admin_message)
        
        await update.message.reply_text(
            f'✅ Отлично! Твой вес {weight} кг записан.\n'
            'Продолжай в том же духе! 💪',
            reply_markup=main_keyboard
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            'Пожалуйста, введи корректное числовое значение веса (например: 70.5):',
            reply_markup=ForceReply(selective=True)
        )
        return WAITING_WEIGHT

def main():
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики разговора
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.Regex('^🍽 Приём пищи$'), handle_meal),
            MessageHandler(filters.Regex('^⚖️ Взвеситься$'), lambda u, c: message_handler(u, c)),
            MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
        ],
        states={
            WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
            WAITING_MEAL_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_meal_number)],
            WAITING_FOOD_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT, handle_food_photo)],
            WAITING_ADMIN_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_reply)],
            WAITING_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight)]
        },
        fallbacks=[
            MessageHandler(filters.Regex('^↩️ Назад$'), lambda u, c: message_handler(u, c))
        ],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_admin_callback))
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main() 