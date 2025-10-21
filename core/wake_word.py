"""
Wake word detection через Porcupine (Picovoice)
З fallback режимом для тестування без API ключа
"""

import pyaudio
import struct
import time
from typing import Optional, Any, cast

from config import get_settings

# Використовуємо альтернативний детектор замість Porcupine
from .wake_word_alt import WakeWordDetector as AltWakeWordDetector, WakeWordMode


class WakeWordDetector:
    def __init__(self, wake_word: Optional[str] = None):
        settings = get_settings()
        self.wake_word = wake_word or settings.wake_word
        self.detector = AltWakeWordDetector(
            wake_word=self.wake_word,
            mode=WakeWordMode.VAD,
            sensitivity=0.6
        )

    def listen(self) -> bool:
        return self.detector.listen()

    def stop(self):
        self.detector.stop()

