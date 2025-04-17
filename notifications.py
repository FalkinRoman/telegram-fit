import logging
from datetime import datetime, timedelta
from telegram.ext import ContextTypes
from data_manager import data_manager
import random
from telegram import Bot
from telegram.error import Forbidden

# Мотивационные сообщения для утра
MORNING_MESSAGES = [
    "🌟 Новый день - новые возможности!",
    "🌅 Сегодня отличный день для тренировки!",
    "💪 Каждый день приближает тебя к цели!",
    "🎯 Маленькие шаги к большой цели!",
    "✨ Ты на верном пути! Продолжай в том же духе!"
]

async def send_message_safely(bot, chat_id: str, text: str) -> bool:
    """Безопасная отправка сообщения с обработкой ошибок"""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except Forbidden as e:
        if "bot was blocked by the user" in str(e):
            logging.warning(f"Пользователь {chat_id} заблокировал бота")
        return False
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения пользователю {chat_id}: {e}")
        return False

async def send_morning_message(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет утреннее мотивационное сообщение"""
    users = data_manager.get_all_users()
    today = datetime.now()
    
    for user in users:
        user_id = user['user_id']
        stats = data_manager.get_user_stats(user_id)
        
        message = (
            f"🌅 Доброе утро, {user['name']}!\n\n"
            f"День {stats['marathon_progress']} из 90\n"
            f"{random.choice(MORNING_MESSAGES)}\n\n"
            f"💪 Не забывай про тренировку (кардио или силовая)\n"
            f"📝 Вноси данные для отслеживания прогресса!"
        )
        
        await send_message_safely(context.bot, user_id, message)

async def send_evening_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет вечерние напоминания о невыполненных задачах"""
    users = data_manager.get_all_users()
    today = datetime.now()
    is_friday = today.weekday() == 4
    
    for user in users:
        user_id = user['user_id']
        stats = data_manager.get_user_stats(user_id)
        reminders = []
        
        # Проверяем приемы пищи (обязательно минимум 3)
        if stats['today_meals'] < 3:
            reminders.append(
                f"🍽 Не забудь внести приемы пищи (минимум 3, сейчас {stats['today_meals']})"
            )
        
        # Проверяем тренировки (нужна хотя бы одна - кардио ИЛИ силовая)
        if not stats['today_cardio'] and not stats['today_strength']:
            reminders.append(
                "💪 Не забудь выполнить тренировку (кардио или силовую)"
            )
        
        # Проверяем вес только по пятницам
        if is_friday:
            # Проверяем, был ли внесен вес за последние 7 дней
            user_data = data_manager.load_user_data(user_id)
            weight_history = user_data.get('weight_history', [])
            
            # Получаем дату последнего взвешивания
            last_weight_date = None
            if weight_history:
                last_weight = weight_history[-1]
                last_weight_date = datetime.strptime(last_weight['date'], '%Y-%m-%d')
            
            # Проверяем, было ли взвешивание на этой неделе
            start_of_week = today - timedelta(days=today.weekday())
            if not last_weight_date or last_weight_date < start_of_week:
                reminders.append("⚖️ Не забудь внести свой вес за эту неделю")
        
        # Если есть напоминания, отправляем сообщение
        if reminders:
            message = (
                f"👋 Привет, {user['name']}!\n\n"
                f"Напоминаю о важных задачах:\n"
                + "\n".join(reminders) + "\n\n"
                f"💡 План тренировок на неделю:\n"
                f"• Кардио: 5-6 раз\n"
                f"• Силовая: 2-3 раза\n"
                f"• HIIT: 1-2 раза\n\n"
                f"💪 Ты сможешь! Действуй!"
            )
            
            await send_message_safely(context.bot, user_id, message)

def setup_notifications(application):
    """Настраивает расписание уведомлений"""
    # Утреннее сообщение в 9:00
    application.job_queue.run_daily(
        send_morning_message,
        time=datetime.strptime("09:00", "%H:%M").time()
    )
    
    # Вечерние напоминания в 20:00
    application.job_queue.run_daily(
        send_evening_reminders,
        time=datetime.strptime("20:00", "%H:%M").time()
    ) 