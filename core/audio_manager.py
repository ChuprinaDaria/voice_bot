"""
Клас для роботи зі звуком на Raspberry Pi
Поки пишемо з заглушками, тестувати будемо на Pi
"""

import pyaudio
import wave
from io import BytesIO


class AudioManager:
    def __init__(self):
        self.sample_rate = 16000  # 16kHz для Whisper
        self.channels = 1  # mono
        self.chunk = 1024
        
    def record_audio(self, duration: int = 5) -> bytes:
        """Записує N секунд аудіо з мікрофона"""
        # TODO: Тестувати на Pi
        return b""
        
    def record_until_silence(self, silence_threshold: int = 500, 
                            silence_duration: float = 1.5) -> bytes:
        """Записує поки не буде тиша 1.5 сек"""
        # TODO: Тестувати на Pi
        return b""
        
    def play_audio(self, audio_data: bytes) -> None:
        """Відтворює аудіо через динаміки"""
        # TODO: Тестувати на Pi
        pass


