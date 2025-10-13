from __future__ import annotations

from typing import Optional, Tuple

from storage.database import SessionLocal
from storage.models import User, UserSecrets
from storage.secrets_manager import encrypt_token, decrypt_token


class APIManager:
    """Керування API ключами користувача"""

    def get_openai_key(self, telegram_user_id: int) -> Optional[str]:
        """Отримує OpenAI ключ користувача (або дефолтний)"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
            if not user:
                return None

            user_secrets = (
                db.query(UserSecrets).filter(UserSecrets.user_id == user.id).first()
            )

            if user_secrets and user_secrets.openai_api_key:
                # Розшифровуємо і повертаємо користувацький ключ
                return decrypt_token(user_secrets.openai_api_key)

            # Якщо немає - повертаємо дефолтний з .env
            from config import settings

            return settings.openai_api_key
        finally:
            db.close()

    def set_openai_key(self, telegram_user_id: int, api_key: str) -> bool:
        """Зберігає OpenAI ключ користувача"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
            if not user:
                return False

            # Шифруємо ключ
            encrypted_key = encrypt_token(api_key)

            # Шукаємо існуючий запис або створюємо новий
            user_secrets = (
                db.query(UserSecrets).filter(UserSecrets.user_id == user.id).first()
            )

            if user_secrets:
                user_secrets.openai_api_key = encrypted_key
            else:
                user_secrets = UserSecrets(user_id=user.id, openai_api_key=encrypted_key)
                db.add(user_secrets)

            db.commit()
            return True
        finally:
            db.close()

    def validate_openai_key(self, api_key: str) -> Tuple[bool, str]:
        """Перевіряє валідність OpenAI ключа"""
        import openai
        from openai import OpenAI

        try:
            # Простий тест - список моделей
            client = OpenAI(api_key=api_key)
            client.models.list()
            return True, "✅ Ключ валідний!"
        except openai.AuthenticationError:
            return False, "❌ Невірний ключ API"
        except Exception as e:  # noqa: BLE001 - повідомляємо користувачу текст помилки
            return False, f"❌ Помилка: {str(e)}"


# Глобальний об'єкт
api_manager = APIManager()


