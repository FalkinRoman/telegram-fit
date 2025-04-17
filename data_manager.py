import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import logging

class DataManager:
    def __init__(self):
        """Инициализация менеджера данных"""
        self.users_dir = os.path.join(os.path.dirname(__file__), 'data', 'users')
        os.makedirs(self.users_dir, exist_ok=True)
        
        # Настройка логирования
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def get_user_data_file(self, user_id: str) -> str:
        """Возвращает путь к файлу с данными пользователя"""
        return os.path.join(self.users_dir, f"{user_id}.json")

    def load_user_data(self, user_id: str) -> Dict:
        """Загружает данные пользователя"""
        try:
            file_path = self.get_user_data_file(user_id)
            if not os.path.exists(file_path):
                return {
                    'user_id': user_id,
                    'name': None,
                    'start_date': None,
                    'weight_history': [],
                    'meals': [],
                    'cardio': [],
                    'strength': []
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке данных пользователя {user_id}: {e}")
            return {
                'user_id': user_id,
                'name': None,
                'start_date': None,
                'weight_history': [],
                'meals': [],
                'cardio': [],
                'strength': []
            }

    def save_user_data(self, user_id: str, data: Dict) -> bool:
        """Сохраняет данные пользователя"""
        try:
            # Создаем директорию, если её нет
            os.makedirs(self.users_dir, exist_ok=True)
            
            # Путь к файлу пользователя
            file_path = os.path.join(self.users_dir, f"{user_id}.json")
            
            # Сохраняем данные в файл
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении данных пользователя {user_id}: {e}")
            return False

    def get_all_users(self) -> List[Dict]:
        """Возвращает список всех пользователей"""
        users = []
        try:
            for filename in os.listdir(self.users_dir):
                if filename.endswith('.json'):
                    user_id = filename[:-5]  # Убираем .json
                    user_data = self.load_user_data(user_id)
                    if user_data['name']:  # Добавляем только пользователей с именами
                        users.append({
                            'user_id': user_id,
                            'name': user_data['name'],
                            'start_date': user_data['start_date']
                        })
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка пользователей: {e}")
        return users

    def get_user_stats(self, user_id: str) -> dict:
        """Получение статистики пользователя"""
        user_data = self.load_user_data(user_id)
        if not user_data:
            return {}
            
        # Получаем дату начала марафона
        start_date = datetime.strptime(user_data['start_date'], '%Y-%m-%d')
        today = datetime.now()
        
        # Считаем прогресс марафона (день 1 = первый день)
        days_passed = (today - start_date).days + 1  # +1 потому что первый день тоже считается
        marathon_progress = min(days_passed, 90)  # Не больше 90 дней
        days_left = max(90 - days_passed, 0)  # Не меньше 0 дней
        
        # Получаем текущий вес и разницу
        weight_history = user_data.get('weight_history', [])
        current_weight = weight_history[-1]['weight'] if weight_history else None
        start_weight = weight_history[0]['weight'] if weight_history else None
        weight_diff = current_weight - start_weight if current_weight and start_weight else 0
        
        # Проверяем активности за сегодня
        today_str = today.strftime('%Y-%m-%d')
        today_meals = len([m for m in user_data.get('meals', []) if m['date'].startswith(today_str)])
        today_cardio = any(c['date'].startswith(today_str) for c in user_data.get('cardio', []))
        today_strength = any(s['date'].startswith(today_str) for s in user_data.get('strength', []))
        
        return {
            'marathon_progress': marathon_progress,
            'days_left': days_left,
            'current_weight': current_weight,
            'start_weight': start_weight,
            'weight_diff': weight_diff,
            'today_meals': today_meals,
            'today_cardio': today_cardio,
            'today_strength': today_strength
        }

    def save_name(self, user_id: str, name: str) -> bool:
        """Сохраняет имя пользователя"""
        try:
            if not name or len(name) > 50:
                return False
            data = self.load_user_data(user_id)
            data['name'] = name
            return self.save_user_data(user_id, data)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении имени пользователя {user_id}: {e}")
            return False

    def save_weight(self, user_id: str, weight: float) -> bool:
        """Сохраняет вес пользователя"""
        try:
            self.logger.info(f"Начало сохранения веса {weight} для пользователя {user_id}")
            user_data = self.load_user_data(user_id)
            self.logger.info(f"Загружены данные пользователя: {user_data}")
            
            if 'weight_history' not in user_data:
                self.logger.info("Создаем новую историю веса")
                user_data['weight_history'] = []
            
            weight_entry = {
                'weight': weight,
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            self.logger.info(f"Добавляем запись о весе: {weight_entry}")
            user_data['weight_history'].append(weight_entry)
            
            save_result = self.save_user_data(user_id, user_data)
            self.logger.info(f"Результат сохранения: {save_result}")
            return save_result
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении веса пользователя {user_id}: {e}")
            return False

    def save_meal(self, user_id: str, photo_id: str) -> bool:
        """Сохраняет прием пищи"""
        try:
            if not photo_id:
                return False
            data = self.load_user_data(user_id)
            data['meals'].append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'photo_id': photo_id
            })
            return self.save_user_data(user_id, data)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении приема пищи пользователя {user_id}: {e}")
            return False

    def save_cardio(self, user_id: str, duration: int) -> bool:
        """Сохраняет кардио тренировку"""
        try:
            if not isinstance(duration, int) or duration <= 0 or duration > 300:
                return False
            data = self.load_user_data(user_id)
            data['cardio'].append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'duration': duration
            })
            return self.save_user_data(user_id, data)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении кардио пользователя {user_id}: {e}")
            return False

    def save_strength(self, user_id: str, exercises: str) -> bool:
        """Сохраняет силовую тренировку"""
        try:
            if not exercises or len(exercises) > 1000:
                return False
            data = self.load_user_data(user_id)
            data['strength'].append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'exercises': exercises
            })
            return self.save_user_data(user_id, data)
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении силовой тренировки пользователя {user_id}: {e}")
            return False

# Создаем глобальный экземпляр менеджера данных
data_manager = DataManager() 