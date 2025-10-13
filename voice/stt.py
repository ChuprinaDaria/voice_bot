from __future__ import annotations

from typing import BinaryIO
from io import BytesIO

from openai import OpenAI

from core.api_manager import api_manager


class NamedBytesIO(BytesIO):
    """In-memory bytes buffer з іменем файлу для сумісності з OpenAI SDK."""
    def __init__(self, initial_bytes: bytes, name: str):
        super().__init__(initial_bytes)
        self.name = name  # деякі SDK очікують атрибут .name


def transcribe_audio(telegram_user_id: int, audio_file: str | bytes | BinaryIO) -> str:
    """Розпізнавання голосу з використанням OpenAI Whisper без запису на диск."""
    api_key = api_manager.get_openai_key(telegram_user_id)
    client = OpenAI(api_key=api_key)

    if isinstance(audio_file, str):
        with open(audio_file, "rb") as f:
            response = client.audio.transcriptions.create(model="whisper-1", file=f)
    elif isinstance(audio_file, bytes):
        # Обробка in-memory bytes без файлової системи
        buffer = NamedBytesIO(audio_file, name="audio.wav")
        response = client.audio.transcriptions.create(model="whisper-1", file=buffer)
    else:
        # BinaryIO (наприклад, вже відкритий файл/буфер)
        response = client.audio.transcriptions.create(model="whisper-1", file=audio_file)

    return getattr(response, "text", "")


