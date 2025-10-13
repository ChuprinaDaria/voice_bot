from __future__ import annotations

from typing import Optional


class GoogleCalendarManager:
    """Мінімальна заглушка для інтеграції Google Calendar"""

    def is_connected(self, telegram_user_id: int) -> bool:
        # Поки що повертаємо False, доки не буде реалізовано OAuth
        return False

    def get_auth_url(self, telegram_user_id: int) -> str:
        # Плейсхолдер посилання для майбутнього OAuth
        return "https://accounts.google.com/o/oauth2/auth"


google_calendar_manager = GoogleCalendarManager()


