"""
Text-to-Speech через OpenAI
"""

from typing import Optional, Literal
from openai import OpenAI
from core.api_manager import api_manager


def text_to_speech(
    telegram_user_id: int,
    text: str, 
    language: str = "uk",
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "alloy"
) -> bytes:
    """
    Генерує аудіо з тексту
    
    Args:
        telegram_user_id: ID користувача (для API ключа)
        text: Текст для озвучки
        language: uk або en
        voice: alloy, echo, fable, onyx, nova, shimmer
    
    Returns:
        bytes: MP3 аудіо
    """
    api_key = api_manager.get_openai_key(telegram_user_id)
    client = OpenAI(api_key=api_key)
    
    response = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        response_format="mp3"  # ← MP3 формат (підтримується OpenAI)
    )
    
    return response.content