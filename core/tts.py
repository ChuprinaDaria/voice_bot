"""
Text-to-Speech через OpenAI або gTTS
"""

from typing import Optional
from openai import OpenAI
from core.api_manager import api_manager


def text_to_speech(
    telegram_user_id: int,
    text: str, 
    language: str = "uk",
    voice: str = "alloy"
) -> bytes:
    """
    Генерує аудіо з тексту
    
    Args:
        telegram_user_id: ID користувача (для API ключа)
        text: Текст для озвучки
        language: uk або en (поки німецьку не робимо)
        voice: alloy, echo, fable, onyx, nova, shimmer
    
    Returns:
        bytes: MP3 аудіо
    """
    api_key = api_manager.get_openai_key(telegram_user_id)
    client = OpenAI(api_key=api_key)
    
    response = client.audio.speech.create(
        model="tts-1",  # або tts-1-hd для якості
        voice=voice,
        input=text,
        speed=1.0
    )
    
    return response.content


