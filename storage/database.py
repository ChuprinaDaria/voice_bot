from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def init_db() -> None:
    """Ініціалізує базу даних і створює всі таблиці, якщо їх ще немає.

    Важливо: імпортуємо моделі всередині функції, щоб зареєструвати всі таблиці
    на метаданих бази перед викликом create_all.
    """
    # Локальний імпорт, щоб уникнути циклічних залежностей на рівні модуля
    from . import models  # noqa: F401  # реєструє таблиці в Base.metadata

    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


