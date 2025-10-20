"""
Wake word detection через Porcupine (Picovoice)
З fallback режимом для тестування без API ключа
"""

import pyaudio
import struct
import time
from typing import Optional, Any, cast

from config import get_settings

# Спроба імпорту Porcupine
pvporcupine: Any | None = None
try:
    import pvporcupine as _pvporcupine  # type: ignore
    pvporcupine = _pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False
    print("⚠️  pvporcupine не встановлено. Wake word detection недоступний.")


class WakeWordDetector:
    """Детектор wake word з підтримкою Porcupine і fallback"""
    
    def __init__(self, wake_word: Optional[str] = None):
        settings = get_settings()
        self.wake_word = wake_word or settings.wake_word
        self.access_key = settings.picovoice_access_key
        
        self.porcupine = None
        self.audio_stream = None
        self.pa = None
        
        # Режим роботи
        self.use_porcupine = PORCUPINE_AVAILABLE and self.access_key
        
        if self.use_porcupine:
            self._init_porcupine()
        else:
            print("⚠️  Працюю в FALLBACK режимі (без wake word detection)")
            print("    Для тестування - просто натисни Enter в консолі")
        
    def _init_porcupine(self):
        """Ініціалізація Porcupine"""
        try:
            keywords = []
            if self.wake_word.lower() in ["hey google", "ok google", "alexa", "computer", "jarvis"]:
                keywords = [self.wake_word.lower()]
            else:
                print(f"⚠️  Wake word '{self.wake_word}' не підтримується.")
                print("    Використовую 'hey google' замість.")
                keywords = ["hey google"]
            
            porcupine_mod = cast(Any, pvporcupine)
            self.porcupine = porcupine_mod.create(
                access_key=self.access_key,
                keywords=keywords
            )
            
            self.pa = pyaudio.PyAudio()
            self.audio_stream = self.pa.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            
            print(f"✅ Porcupine ініціалізовано. Wake word: {keywords[0]}")
            
        except Exception as e:
            print(f"❌ Помилка ініціалізації Porcupine: {e}")
            self.use_porcupine = False
            
    def listen(self) -> bool:
        """
        Слухає wake word
        Returns True коли почув
        """
        if self.use_porcupine:
            return self._listen_porcupine()
        else:
            return self._listen_fallback()
            
    def _listen_porcupine(self) -> bool:
        """Прослуховування через Porcupine"""
        if not self.audio_stream or not self.porcupine:
            return False
            
        try:
            pcm = self.audio_stream.read(
                self.porcupine.frame_length,
                exception_on_overflow=False
            )
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
            
            keyword_index = self.porcupine.process(pcm)
            
            if keyword_index >= 0:
                print(f"🎤 Wake word detected: {self.wake_word}")
                return True
                
        except Exception as e:
            print(f"❌ Помилка прослуховування: {e}")
            
        return False
        
    def _listen_fallback(self) -> bool:
        """Fallback режим - чекаємо Enter в консолі"""
        print("\n[FALLBACK MODE] Натисни Enter щоб симулювати wake word...")
        try:
            input()
            return True
        except (KeyboardInterrupt, EOFError):
            return False
            
    def stop(self):
        """Зупиняє прослуховування і звільняє ресурси"""
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            
        if self.pa:
            self.pa.terminate()
            
        if self.porcupine:
            self.porcupine.delete()
            
        print("🛑 Wake word detector зупинено")

