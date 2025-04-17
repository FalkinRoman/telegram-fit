import os
import logging
from datetime import datetime, time, timedelta
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from data_manager import data_manager

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
WAITING_WEIGHT = 4
WAITING_TRAINER_MESSAGE = 5  # Новое состояние для сообщения тренеру
PHOTO_PROGRESS = 25
WAITING_CARDIO = 6
WAITING_STRENGTH = 7

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
    ['💪 Мотивация', '✉️ Написать тренеру']
], resize_keyboard=True)

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало разговора и запрос имени"""
    user_id = str(update.effective_user.id)
    user_data = data_manager.load_user_data(user_id)
    
    if not user_data.get('name'):
        await update.message.reply_text(
            'Привет! Как я могу к тебе обращаться? 😊',
            reply_markup=ForceReply(selective=True)
        )
        return WAITING_NAME
    else:
        await update.message.reply_text(
            f'С возвращением, {user_data["name"]}! 👋',
            reply_markup=main_keyboard
        )
        return ConversationHandler.END

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

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение имени пользователя и начало работы"""
    user_name = update.message.text
    user_id = str(update.effective_user.id)
    
    # Сохраняем имя в базе данных
    data_manager.save_user_data(user_id, {
        'user_id': user_id,
        'name': user_name,
        'start_date': datetime.now().strftime('%Y-%m-%d'),
        'weight_history': [],
        'meals': [],
        'cardio': [],
        'strength': []
    })
    
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
        '�� и мотивировать, когда будет тяжело\n\n'
        'Используй кнопки ниже для отметки своих достижений:\n\n'
        '🍽 Приём пищи - фиксируй каждый приём пищи\n'
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
        
    if not any(text.startswith(num) for num in ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']):
        await update.message.reply_text(
            'Пожалуйста, выбери номер приёма пищи из меню:',
            reply_markup=meal_keyboard
        )
        return WAITING_MEAL_NUMBER
        
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
    user_id = str(update.effective_user.id)
    user_data = data_manager.load_user_data(user_id)
    user_name = user_data['name']
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
    
    try:
        # Сохраняем фото в базе данных
        data_manager.save_meal(user_id, photo.file_id)
        
        # Создаем клавиатуру для админа
        admin_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}_{meal_number}"),
             InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}_{meal_number}")],
            [InlineKeyboardButton("💬 Комментировать", callback_data=f"comment_{user_id}_{meal_number}")]
        ])

        # Отправляем фото админу
        admin_message = (
            f'🍽 Новый приём пищи\n\n'
            f'👤 {user_name}\n'
            f'#️⃣ Приём {meal_number}\n'
            f'⏰ {datetime.now().strftime("%H:%M")}'
        )
        
        await notify_admin(
            context=context,
            message=admin_message,
            photo_file_id=photo.file_id,
            reply_markup=admin_keyboard
        )
        
        # Отвечаем пользователю
        await message.reply_text(
            f'Отлично! Приём пищи {meal_number} зафиксирован ✅\n'
            'Фото отправлено тренеру на проверку 👨‍🏫',
            reply_markup=main_keyboard
        )
        return ConversationHandler.END
        
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
    user_id = str(user_id)

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
    user_id = str(update.effective_user.id)
    user_data = data_manager.load_user_data(user_id)
    user_name = user_data['name']
    
    # Сохраняем кардио в базе данных
    data_manager.save_cardio(user_id, 30)  # По умолчанию 30 минут
    
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

async def handle_strength(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = data_manager.load_user_data(user_id)
    user_name = user_data['name']
    
    # Сохраняем силовую тренировку в базе данных
    data_manager.save_strength(user_id, "Силовая тренировка выполнена")
    
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

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику пользователя"""
    user_id = str(update.effective_user.id)
    stats = data_manager.get_user_stats(user_id)
    
    # Создаем строку с квадратиками прогресса
    progress_squares = ""
    for i in range(90):
        if i < stats['marathon_progress']:
            progress_squares += "🟩"  # Зеленый квадрат для пройденных дней
        else:
            progress_squares += "⬜️"  # Белый квадрат для оставшихся дней
        if (i + 1) % 10 == 0:  # Перенос строки каждые 10 квадратиков
            progress_squares += "\n"
    
    message = (
        f"📊 День {stats['marathon_progress']} из 90\n\n"
        f"{progress_squares}\n"
        f"⏳ Осталось: {stats['days_left']} дней\n\n"
        f"⚖️ Твой путь к прессу:\n"
    )
    
    if stats['current_weight'] is not None:
        message += (
            f"Стартовый вес: {stats['start_weight']:.1f} кг\n"
            f"Текущий вес: {stats['current_weight']:.1f} кг\n"
            f"Изменение: {stats['weight_diff']:+.1f} кг\n"
        )
        
        if stats['weight_diff'] <= 0:
            message += "🔥 Жир горит!\n"
        else:
            message += "💪 Время поднажать!\n"
    else:
        message += "⚖️ Пока нет данных о весе\n"
    
    message += "\nСегодняшние подвиги:\n"
    message += f"🍽 Приёмы пищи: {stats['today_meals']}/5\n"
    
    if stats['today_cardio']:
        message += "🏃‍♂️ Кардио: ✅ 🔥\n"
    else:
        message += "🏃‍♂️ Кардио: ❌\n"
        
    if stats['today_strength']:
        message += "💪 Силовая: ✅ 💪\n"
    else:
        message += "💪 Силовая: ❌\n"
    
    if stats['today_meals'] == 5 and stats['today_cardio'] and stats['today_strength']:
        message += "\n💪 Ты просто космос! Так держать! 🚀"
    elif stats['today_meals'] > 0 or stats['today_cardio'] or stats['today_strength']:
        message += "\n💪 Продолжай в том же духе!"
    else:
        message += "\n💪 Давай начнем этот день правильно!"
    
    await update.message.reply_text(message)

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений"""
    text = update.message.text
    
    if text == '🍽 Приём пищи':
        return await handle_meal(update, context)
    elif text == '⚖️ Взвеситься':
        await update.message.reply_text(
            'Пожалуйста, введи свой текущий вес в килограммах (например: 70.5):',
            reply_markup=ForceReply(selective=True)
        )
        return WAITING_WEIGHT
    elif text == '🏃‍♂️ Кардио':
        await handle_cardio(update, context)
    elif text == '💪 Силовая':
        await handle_strength(update, context)
    elif text == '📊 Статистика':
        await show_stats(update, context)
    elif text == '📋 Правила':
        await show_rules(update, context)
    elif text == '💪 Мотивация':
        await show_motivation(update, context)
    elif text == '✉️ Написать тренеру':
        # Запрашиваем сообщение для тренера
        message_keyboard = ReplyKeyboardMarkup([
            ['❌ Отмена']
        ], resize_keyboard=True)
        
        await update.message.reply_text(
            '📝 Напиши сообщение для тренера:\n'
            '(или нажми ❌ Отмена для возврата в меню)',
            reply_markup=message_keyboard
        )
        return WAITING_TRAINER_MESSAGE
    elif text == '❌ Отмена':
        await update.message.reply_text(
            'Действие отменено.',
            reply_markup=main_keyboard
        )
        return ConversationHandler.END
    
    return ConversationHandler.END

async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода веса"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    logger.info(f"Получен вес от пользователя {user_id}: {text}")
    
    try:
        weight = float(text.replace(',', '.'))
        logger.info(f"Преобразованный вес: {weight}")
        
        if weight < 30 or weight > 200:
            logger.warning(f"Некорректный вес: {weight}")
            await update.message.reply_text(
                '❌ Пожалуйста, введи корректный вес (от 30 до 200 кг)',
                reply_markup=ForceReply(selective=True)
            )
            return WAITING_WEIGHT
            
        # Сохраняем вес
        logger.info(f"Сохраняем вес {weight} для пользователя {user_id}")
        save_result = data_manager.save_weight(user_id, weight)
        logger.info(f"Результат сохранения: {save_result}")
        
        if not save_result:
            logger.error(f"Ошибка при сохранении веса для пользователя {user_id}")
            await update.message.reply_text(
                '❌ Произошла ошибка при сохранении веса. Попробуй позже.',
                reply_markup=main_keyboard
            )
            return ConversationHandler.END
        
        # Получаем статистику пользователя
        stats = data_manager.get_user_stats(user_id)
        logger.info(f"Получена статистика: {stats}")
        weight_diff = stats.get('weight_diff', 0)
        
        # Формируем сообщение
        if weight_diff == 0:
            message = f'✅ Твой текущий вес: {weight} кг\n\nЭто твое первое взвешивание!'
        else:
            message = (
                f'✅ Твой текущий вес: {weight} кг\n\n'
                f'Изменение с прошлого раза: {weight_diff:+.1f} кг'
            )
            
            # Добавляем мотивационное сообщение
            if weight_diff < 0:
                message += '\n\n🎉 Отличная работа! Продолжай в том же духе! 💪'
            elif weight_diff > 0:
                message += '\n\n💪 Не расстраивайся! Следующее взвешивание будет лучше!'
        
        # Уведомляем админа
        admin_message = (
            f'⚖️ Новое взвешивание!\n\n'
            f'👤 {data_manager.load_user_data(user_id)["name"]}\n'
            f'📊 Вес: {weight} кг (изменение: {weight_diff:+.1f} кг)\n'
            f'📅 {datetime.now().strftime("%d.%m.%Y %H:%M")}'
        )
        
        try:
            await notify_admin(context, admin_message)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления админу: {e}")
        
        # Отвечаем пользователю и возвращаем главное меню
        await update.message.reply_text(message, reply_markup=main_keyboard)
        return ConversationHandler.END
        
    except ValueError:
        logger.warning(f"Некорректный формат веса: {text}")
        await update.message.reply_text(
            '❌ Пожалуйста, введи корректный вес в формате XX.X\n'
            'Например: 70.5',
            reply_markup=ForceReply(selective=True)
        )
        return WAITING_WEIGHT
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке веса: {e}")
        await update.message.reply_text(
            '❌ Произошла ошибка. Попробуй позже.',
            reply_markup=main_keyboard
        )
        return ConversationHandler.END

async def handle_trainer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщения для тренера"""
    if update.message.text == '❌ Отмена':
        await update.message.reply_text(
            'Отправка сообщения отменена.',
            reply_markup=main_keyboard
        )
        return ConversationHandler.END
    
    user_id = str(update.effective_user.id)
    user_data = data_manager.load_user_data(user_id)
    user_name = user_data['name']
    message = update.message.text
    
    try:
        # Создаем клавиатуру для быстрого ответа
        reply_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✉️ Ответить", callback_data=f"reply_{user_id}")]
        ])
        
        # Отправляем сообщение админу через админ-бота
        admin_message = (
            f"📨 Новое сообщение от участника:\n\n"
            f"👤 {user_name}\n"
            f"🆔 {user_id}\n\n"
            f"💬 Сообщение:\n{message}"
        )
        
        await notify_admin(context, admin_message, reply_markup=reply_keyboard)
        
        await update.message.reply_text(
            '✅ Сообщение отправлено тренеру!\n'
            'Ожидайте ответа.',
            reply_markup=main_keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения тренеру: {e}")
        await update.message.reply_text(
            '❌ Произошла ошибка при отправке сообщения. Попробуйте позже.',
            reply_markup=main_keyboard
        )
    
    return ConversationHandler.END

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex('^🍽 Приём пищи$'), handle_meal),
            MessageHandler(filters.Regex('^⚖️ Взвеситься$'), lambda u, c: handle_message(u, c)),
            MessageHandler(filters.Regex('^🏃‍♂️ Кардио$'), lambda u, c: handle_message(u, c)),
            MessageHandler(filters.Regex('^💪 Силовая$'), lambda u, c: handle_message(u, c)),
            MessageHandler(filters.Regex('^📊 Статистика$'), lambda u, c: handle_message(u, c)),
            MessageHandler(filters.Regex('^📋 Правила$'), lambda u, c: handle_message(u, c)),
            MessageHandler(filters.Regex('^💪 Мотивация$'), lambda u, c: handle_message(u, c)),
            MessageHandler(filters.Regex('^✉️ Написать тренеру$'), lambda u, c: handle_message(u, c))
        ],
        states={
            WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            WAITING_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight)],
            WAITING_FOOD_PHOTO: [
                MessageHandler(filters.PHOTO, handle_food_photo),
                MessageHandler(filters.TEXT & filters.Regex('^↩️ Назад$'), handle_message)
            ],
            WAITING_MEAL_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_meal_number),
                MessageHandler(filters.TEXT & filters.Regex('^↩️ Назад$'), handle_message)
            ],
            WAITING_TRAINER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_trainer_message)]
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        ]
    )
    application.add_handler(conv_handler)
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main() 