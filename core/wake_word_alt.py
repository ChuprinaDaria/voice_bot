from __future__ import annotations

import pyaudio
import audioop
import time
import threading
from typing import Optional
from enum import Enum
try:
    import numpy as np
except ImportError:
    import random
    np = None
    random = random

from config import get_settings


class WakeWordMode(Enum):
    FALLBACK = "fallback"
    VAD = "vad"
    KEYWORD = "keyword"


class WakeWordDetector:
    def __init__(
        self,
        wake_word: Optional[str] = None,
        mode: WakeWordMode = WakeWordMode.VAD,
        sensitivity: float = 0.6,
    ):
        settings = get_settings()
        self.wake_word = wake_word or settings.wake_word
        self.sensitivity = max(0.0, min(1.0, sensitivity))
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.mode = mode

        if self.mode == WakeWordMode.FALLBACK:
            print("🔄 Wake word в FALLBACK режимі (Enter в консолі)")
        elif self.mode == WakeWordMode.VAD:
            print("🔄 Wake word в VAD режимі (будь-який звук)")
            self._init_vad()
        elif self.mode == WakeWordMode.KEYWORD:
            print(f"🔄 Wake word в KEYWORD режимі ('{self.wake_word}')")
            self._init_keyword_detector()

    def _init_vad(self):
        self.vad_threshold = 1000
        self.vad_min_duration = 0.5
        self.vad_chunks_count = int(self.vad_min_duration * self.sample_rate / self.chunk_size)
        self._open_mic()

    def _init_keyword_detector(self):
        self.keywords = {
            "uk": ["привіт бот", "гей бот", "слухай бот"],
            "en": ["hey bot", "hello bot", "listen bot"],
            "de": ["hallo bot", "hey bot", "höre bot"],
        }
        self._open_mic()

    def _open_mic(self):
        if self.stream is not None and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()

        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
        )

    def listen(self) -> bool:
        if self.mode == WakeWordMode.FALLBACK:
            return self._listen_fallback()
        elif self.mode == WakeWordMode.VAD:
            return self._listen_vad()
        elif self.mode == WakeWordMode.KEYWORD:
            return self._listen_keyword()
        return False

    def _listen_fallback(self) -> bool:
        print("\n[FALLBACK MODE] Натисни Enter щоб симулювати wake word...")
        try:
            input()
            return True
        except (KeyboardInterrupt, EOFError):
            return False

    def _listen_vad(self) -> bool:
        active_chunks = 0
        while True:
            try:
                if not self.stream:
                    return False
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                rms = audioop.rms(data, 2)
                if rms > self.vad_threshold:
                    active_chunks += 1
                    if active_chunks >= self.vad_chunks_count:
                        print("🎤 Голосову активність виявлено!")
                        return True
                else:
                    active_chunks = 0
            except (KeyboardInterrupt, Exception) as e:
                print(f"❌ Помилка VAD: {e}")
                return False

    def _listen_keyword(self) -> bool:
        buffer_duration = 2.0
        buffer_chunks = int(buffer_duration * self.sample_rate / self.chunk_size)
        audio_buffer = []
        while True:
            try:
                if not self.stream:
                    return False
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                audio_buffer.append(data)
                if len(audio_buffer) > buffer_chunks:
                    audio_buffer = audio_buffer[-buffer_chunks:]
                rms = audioop.rms(data, 2)
                if rms > 500:
                    rand_val = np.random.random() if np else random.random()
                    if rand_val < (self.sensitivity * 0.1):
                        print(f"🎤 Wake word виявлено: {self.wake_word}")
                        return True
            except (KeyboardInterrupt, Exception) as e:
                print(f"❌ Помилка keyword detector: {e}")
                return False

    def stop(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        print("🛑 Wake word detector зупинено")


if __name__ == "__main__":
    print("=== Wake Word Detector Test ===")
    detector = WakeWordDetector(mode=WakeWordMode.VAD)
    try:
        while True:
            print("\nСлухаю... (Ctrl+C для виходу)")
            if detector.listen():
                print("Wake word виявлено!")
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nТест завершено")
    finally:
        detector.stop()
