"""
Міграція БД: додає таблицю conversations (історія розмов)
Запуск: python migrate_db.py
"""

from storage.database import Base, engine
from storage.models import Conversation

def migrate():
    """Створює нові таблиці в БД"""
    print("🔄 Створюю нові таблиці...")
    Base.metadata.create_all(bind=engine)
    print("✅ Міграцію завершено!")
    print("📊 Таблиця 'conversations' створена")

if __name__ == "__main__":
    migrate()

