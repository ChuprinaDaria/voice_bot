from __future__ import annotations

from typing import BinaryIO

from openai import OpenAI

from core.api_manager import api_manager


def transcribe_audio(telegram_user_id: int, audio_file: str | BinaryIO) -> str:
    """Розпізнавання голосу з використанням OpenAI Whisper."""
    api_key = api_manager.get_openai_key(telegram_user_id)
    client = OpenAI(api_key=api_key)

    if isinstance(audio_file, str):
        with open(audio_file, "rb") as f:
            response = client.audio.transcriptions.create(model="whisper-1", file=f)
    else:
        response = client.audio.transcriptions.create(model="whisper-1", file=audio_file)

    return getattr(response, "text", "")


