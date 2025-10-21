from __future__ import annotations

from typing import Optional

from storage.database import SessionLocal
from storage.models import User


def get_personality_prompt(telegram_user_id: int) -> Optional[str]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        return user.personality_prompt if user else None
    finally:
        db.close()


def set_personality_prompt(telegram_user_id: int, prompt: Optional[str]) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        if not user:
            return False
        user.personality_prompt = prompt
        db.commit()
        db.refresh(user)
        return user.personality_prompt == prompt
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def format_prompt_for_llm(base_prompt: str, user_prompt: Optional[str]) -> str:
    if not user_prompt:
        return base_prompt
    return f"{base_prompt}\n\nДодаткові інструкції щодо особистості:\n{user_prompt}"


