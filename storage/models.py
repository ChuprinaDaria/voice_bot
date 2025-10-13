from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Integer, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ActivationCode(Base):
    """Коди активації пристроїв"""
    __tablename__ = "activation_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)  # VBOT-A3K9-L2M7-X8Q4
    device_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # MAC/serial
    telegram_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL до активації
    is_activated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class User(Base):
    """Користувач після активації"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    device_id: Mapped[str] = mapped_column(String(50), nullable=False)

    # Налаштування користувача
    language: Mapped[str] = mapped_column(String(5), default="uk", nullable=False)
    wake_word: Mapped[str] = mapped_column(String(100), default="Привіт Бот", nullable=False)
    personality_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )



class UserSecrets(Base):
    """Зашифровані токени користувача"""
    __tablename__ = "user_secrets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)

    # OpenAI API Key (encrypted)
    openai_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Spotify tokens (encrypted)
    spotify_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    spotify_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Google tokens (encrypted)
    google_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

