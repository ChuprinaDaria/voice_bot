from __future__ import annotations

from typing import Optional, Tuple, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, timedelta
import json

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build  # type: ignore

from config import get_settings
from storage.database import SessionLocal
from storage.models import User, UserSecrets
from storage.secrets_manager import encrypt_token, decrypt_token


class GoogleCalendarManager:
    """Керування Google Calendar інтеграцією"""

    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

    def __init__(self) -> None:
        settings = get_settings()
        self.credentials_path = settings.google_credentials_path

    def get_auth_url(self, telegram_user_id: int) -> str:
        """Генерує URL для авторизації Google"""
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, 
                self.SCOPES,
                redirect_uri='http://localhost:8080'
            )
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=str(telegram_user_id)
            )
            return auth_url
        except Exception:
            return "https://accounts.google.com/o/oauth2/auth"

    def save_token_simple(self, telegram_user_id: int, access_token: str) -> Tuple[bool, str]:
        """
        Простий спосіб: зберігає тільки access token (без refresh)
        
        Отримати токен: https://developers.google.com/oauthplayground
        """
        try:
            # Створюємо мінімальний credentials JSON
            creds_dict = {
                'token': access_token,
                'scopes': self.SCOPES
            }
            credentials_json = json.dumps(creds_dict)
            
            # Шифруємо і зберігаємо
            encrypted = encrypt_token(credentials_json)
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
                if not user:
                    return False, "❌ Користувач не знайдений"

                secrets = db.query(UserSecrets).filter(UserSecrets.user_id == user.id).first()
                if secrets:
                    secrets.google_calendar_credentials = encrypted  # type: ignore
                else:
                    secrets = UserSecrets(
                        user_id=user.id,
                        google_calendar_credentials=encrypted  # type: ignore
                    )
                    db.add(secrets)

                db.commit()
                
                # Тестуємо токен
                test_creds = Credentials(token=access_token)
                service = build('calendar', 'v3', credentials=test_creds)
                service.calendarList().list(maxResults=1).execute()
                
                return True, "✅ Google Calendar підключено! (токен дійсний ~1 година)"
            finally:
                db.close()
                
        except Exception as e:
            return False, f"❌ Невірний токен: {str(e)}"
    
    def save_credentials(self, telegram_user_id: int, credentials_json: str) -> Tuple[bool, str]:
        """
        Зберігає Google Calendar credentials (повний JSON)
        
        Args:
            telegram_user_id: ID користувача
            credentials_json: JSON з токенами від Google
        """
        try:
            # Парсимо JSON
            creds_dict = json.loads(credentials_json)
            
            # Перевіряємо структуру
            if 'token' not in creds_dict and 'access_token' not in creds_dict:
                return False, "❌ Невірний формат токена"
            
            # Нормалізуємо ключі
            if 'access_token' in creds_dict and 'token' not in creds_dict:
                creds_dict['token'] = creds_dict['access_token']
            
            # Шифруємо і зберігаємо
            encrypted = encrypt_token(json.dumps(creds_dict))
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
                if not user:
                    return False, "❌ Користувач не знайдений"

                secrets = db.query(UserSecrets).filter(UserSecrets.user_id == user.id).first()
                if secrets:
                    secrets.google_calendar_credentials = encrypted  # type: ignore
                else:
                    secrets = UserSecrets(
                        user_id=user.id,
                        google_calendar_credentials=encrypted  # type: ignore
                    )
                    db.add(secrets)

                db.commit()
                return True, "✅ Google Calendar підключено!"
            finally:
                db.close()
                
        except json.JSONDecodeError:
            return False, "❌ Невірний JSON формат"
        except Exception as e:
            return False, f"❌ Помилка: {str(e)}"

    def get_credentials(self, telegram_user_id: int) -> Optional[Credentials]:
        """Отримує credentials користувача"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
            if not user:
                return None

            secrets = db.query(UserSecrets).filter(UserSecrets.user_id == user.id).first()
            if not secrets or not secrets.google_calendar_credentials:  # type: ignore
                return None

            # Розшифровуємо
            creds_json = decrypt_token(secrets.google_calendar_credentials)  # type: ignore
            if not creds_json:
                return None
                
            creds_dict = json.loads(creds_json)
            
            # Створюємо Credentials об'єкт
            creds = Credentials(
                token=creds_dict.get('token'),
                refresh_token=creds_dict.get('refresh_token'),
                token_uri=creds_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=creds_dict.get('client_id'),
                client_secret=creds_dict.get('client_secret'),
                scopes=creds_dict.get('scopes', self.SCOPES)
            )
            
            return creds
            
        finally:
            db.close()

    def is_connected(self, telegram_user_id: int) -> bool:
        """Чи підключений Google Calendar"""
        return self.get_credentials(telegram_user_id) is not None

    def get_upcoming_events(self, telegram_user_id: int, max_results: int = 5) -> Tuple[bool, str]:
        """Отримує найближчі події з календаря"""
        creds = self.get_credentials(telegram_user_id)
        if not creds:
            return False, "❌ Google Calendar не підключено"

        try:
            service = build('calendar', 'v3', credentials=creds)
            
            # Отримуємо події на найближчі 7 днів
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return True, "📅 Немає подій на найближчий час"
            
            # Форматуємо події
            result = "📅 Найближчі події:\n\n"
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', 'Без назви')
                
                # Парсимо дату
                try:
                    if 'T' in start:  # Datetime
                        dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        time_str = dt.strftime('%d.%m %H:%M')
                    else:  # Date only
                        dt = datetime.fromisoformat(start)
                        time_str = dt.strftime('%d.%m (весь день)')
                except Exception:
                    time_str = start
                
                result += f"• {time_str} - {summary}\n"
            
            return True, result
            
        except Exception as e:
            return False, f"❌ Помилка: {str(e)}"


google_calendar_manager = GoogleCalendarManager()


