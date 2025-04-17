import os
from datetime import datetime
import pandas as pd
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_ID')  # ID таблицы из .env

class SheetsManager:
    def __init__(self):
        self.creds = service_account.Credentials.from_service_account_file(
            'credentials.json', scopes=SCOPES)
        self.service = build('sheets', 'v4', credentials=self.creds)
        self.sheet = self.service.spreadsheets()
        self.setup_sheets()

    def setup_sheets(self):
        """Создает структуру таблиц если она еще не создана"""
        try:
            # Заголовки для основной таблицы
            main_headers = [
                ['ID пользователя', 'Имя', 'Дата начала', 'Начальный вес', 
                 'Текущий вес', 'Прогресс', 'День марафона', 'Статус']
            ]
            
            # Заголовки для ежедневных отчетов
            daily_headers = [
                ['Дата', 'ID пользователя', 'Имя', 
                 'Прием пищи 1', 'Прием пищи 2', 'Прием пищи 3',
                 'Прием пищи 4', 'Прием пищи 5', 'Прием пищи 6',
                 'Кардио', 'Силовая', 'Вес', 'Прогресс', 'Комментарии']
            ]

            # Проверяем и обновляем заголовки основной таблицы
            self.sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range='Sheet1!A1:H1',
                valueInputOption='RAW',
                body={'values': main_headers}
            ).execute()

            # Проверяем и обновляем заголовки таблицы отчетов
            self.sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range='Daily Reports!A1:N1',
                valueInputOption='RAW',
                body={'values': daily_headers}
            ).execute()

            # Форматирование таблиц
            requests = [
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': 0,  # Sheet1
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                                'textFormat': {'bold': True}
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                    }
                },
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': 1,  # Daily Reports
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                                'textFormat': {'bold': True}
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                    }
                }
            ]
            
            self.sheet.batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'requests': requests}
            ).execute()

        except HttpError as error:
            print(f"An error occurred: {error}")

    async def update_user_data(self, user_data):
        """Обновляет данные пользователя в основной таблице"""
        try:
            # Подготовка данных
            row = [
                user_data['user_id'],
                user_data['name'],
                user_data.get('start_date', ''),
                user_data.get('initial_weight', ''),
                user_data.get('current_weight', ''),
                user_data.get('weight_progress', ''),
                user_data.get('marathon_day', ''),
                'активен'
            ]

            # Поиск существующей строки или добавление новой
            result = self.sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='Sheet1!A:A'
            ).execute()
            
            values = result.get('values', [])
            user_row = None
            for i, value in enumerate(values):
                if value and value[0] == str(user_data['user_id']):
                    user_row = i + 1
                    break

            if user_row:
                range_name = f'Sheet1!A{user_row}:H{user_row}'
                self.sheet.values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=range_name,
                    valueInputOption='RAW',
                    body={'values': [row]}
                ).execute()
            else:
                self.sheet.values().append(
                    spreadsheetId=SPREADSHEET_ID,
                    range='Sheet1!A:H',
                    valueInputOption='RAW',
                    body={'values': [row]}
                ).execute()

        except HttpError as error:
            print(f"An error occurred: {error}")

    async def add_daily_report(self, user_data, activities):
        """Добавляет ежедневный отчет"""
        try:
            today = datetime.now().strftime("%d.%m.%Y")
            row = [
                today,
                user_data['user_id'],
                user_data['name'],
                activities.get('meal_1', '❌'),
                activities.get('meal_2', '❌'),
                activities.get('meal_3', '❌'),
                activities.get('meal_4', '❌'),
                activities.get('meal_5', '❌'),
                activities.get('meal_6', '❌'),
                activities.get('cardio', '❌'),
                activities.get('strength', '❌'),
                activities.get('weight', ''),
                activities.get('progress', ''),
                activities.get('comments', '')
            ]

            self.sheet.values().append(
                spreadsheetId=SPREADSHEET_ID,
                range='Daily Reports!A:N',
                valueInputOption='RAW',
                body={'values': [row]}
            ).execute()

        except HttpError as error:
            print(f"An error occurred: {error}")

    async def get_all_users(self):
        """Получает список всех пользователей"""
        try:
            result = self.sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='Sheet1!A2:H'
            ).execute()
            
            values = result.get('values', [])
            users = []
            for row in values:
                if len(row) >= 8:
                    users.append({
                        'user_id': row[0],
                        'name': row[1],
                        'start_date': row[2],
                        'initial_weight': row[3],
                        'current_weight': row[4],
                        'weight_progress': row[5],
                        'marathon_day': row[6],
                        'status': row[7]
                    })
            return users
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    async def get_user_stats(self, user_id):
        """Получает статистику пользователя"""
        try:
            # Получаем данные из основной таблицы
            result = self.sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='Sheet1!A:H'
            ).execute()
            
            values = result.get('values', [])
            user_data = None
            for row in values:
                if row[0] == str(user_id):
                    user_data = {
                        'name': row[1],
                        'start_date': row[2],
                        'initial_weight': row[3],
                        'current_weight': row[4],
                        'weight_progress': row[5],
                        'marathon_day': row[6],
                        'status': row[7]
                    }
                    break

            # Получаем последние активности
            result = self.sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range='Daily Reports!A:N'
            ).execute()
            
            values = result.get('values', [])
            activities = []
            for row in values:
                if row[1] == str(user_id):
                    activities.append({
                        'date': row[0],
                        'meals': row[3:9],
                        'cardio': row[9],
                        'strength': row[10],
                        'weight': row[11],
                        'progress': row[12],
                        'comments': row[13]
                    })

            return {
                'user_data': user_data,
                'activities': activities[-7:] if activities else []  # Последние 7 дней
            }

        except HttpError as error:
            print(f"An error occurred: {error}")
            return None 