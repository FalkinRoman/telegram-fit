import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import Dict, List

class DataManager:
    def __init__(self):
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'credentials.json', scope)
        self.client = gspread.authorize(creds)
        
    def save_weight(self, user_id: int, weight: float) -> None:
        """Сохранение веса пользователя"""
        sheet = self.client.open('FitnessTracking').sheet1
        date = datetime.now().strftime('%Y-%m-%d')
        sheet.append_row([date, user_id, weight])
        
    def get_weight_history(self, user_id: int) -> List[Dict]:
        """Получение истории веса пользователя"""
        sheet = self.client.open('FitnessTracking').sheet1
        data = sheet.get_all_records()
        return [
            {'date': row['date'], 'weight': row['weight']}
            for row in data
            if row['user_id'] == user_id
        ]
        
    def save_daily_report(self, user_id: int, report_data: Dict) -> None:
        """Сохранение дневного отчета"""
        sheet = self.client.open('FitnessTracking').worksheet('DailyReports')
        date = datetime.now().strftime('%Y-%m-%d')
        row = [
            date,
            user_id,
            report_data.get('meals', 0),
            report_data.get('cardio', False),
            report_data.get('strength', False),
            report_data.get('water', 0),
            report_data.get('mood', '')
        ]
        sheet.append_row(row)

class AdminPanel:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        
    def get_user_stats(self, user_id: int) -> Dict:
        """Получение статистики пользователя"""
        weight_history = self.data_manager.get_weight_history(user_id)
        if not weight_history:
            return {}
            
        latest_weight = weight_history[-1]['weight']
        initial_weight = weight_history[0]['weight']
        weight_diff = latest_weight - initial_weight
        
        return {
            'current_weight': latest_weight,
            'total_loss': abs(weight_diff) if weight_diff < 0 else 0,
            'total_gain': weight_diff if weight_diff > 0 else 0,
            'weight_history': weight_history
        }
        
    def get_daily_summary(self) -> List[Dict]:
        """Получение сводки за день по всем пользователям"""
        sheet = self.client.open('FitnessTracking').worksheet('DailyReports')
        today = datetime.now().strftime('%Y-%m-%d')
        data = sheet.get_all_records()
        
        return [
            row for row in data
            if row['date'] == today
        ] 