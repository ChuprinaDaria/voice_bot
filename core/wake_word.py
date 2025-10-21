"""
Покращений модуль wake_word.py для Raspberry Pi 5
Використовує Voice Activity Detection замість Porcupine
"""

import pyaudio
import struct
import time
import wave
import numpy as np
import threading
from typing import Optional, Any, List, Callable
import os
import audioop
from enum import Enum

from config import get_settings


class WakeWordMode(Enum):
    """Режими роботи детектора wake word"""
    FALLBACK = "fallback"  # Режим натискання Enter в консолі
    VAD = "vad"  # Режим детекції голосової активності
    ALWAYS_ON = "always_on"  # Завжди активний режим (для тестування)


class WakeWordDetector:
    """Детектор wake word з підтримкою різних режимів"""
    
    def __init__(self, 
                 wake_word: Optional[str] = None,
                 mode: WakeWordMode = WakeWordMode.VAD,
                 sensitivity: float = 0.6):
        """
        Ініціалізація детектора
        
        Args:
            wake_word: Ключове слово (наприклад, "привіт бот")
            mode: Режим роботи
            sensitivity: Чутливість детекції (0-1)
        """
        self.settings = get_settings()
        self.wake_word = wake_word or self.settings.wake_word
        self.sensitivity = max(0.0, min(1.0, sensitivity))
        
        # Аудіо параметри
        self.sample_rate = 16000
        self.chunk_size = 1024
        
        # Ініціалізуємо аудіо-поля ДО будь-яких операцій із мікрофоном
        self.audio = None
        self.stream = None
        self.is_running = True

        # Вибір режиму (для Pi 5 рекомендовано VAD)
        if mode == WakeWordMode.ALWAYS_ON:
            self.mode = mode
            print("🔄 Wake word в режимі ALWAYS_ON (автоматична активація)")
        elif mode == WakeWordMode.VAD:
            self.mode = mode
            self._init_vad()
        else:
            # Fallback режим
            self.mode = WakeWordMode.FALLBACK
            print("🔄 Wake word в режимі FALLBACK (натисни Enter)")
    
    def _init_vad(self):
        """Ініціалізація Voice Activity Detection"""
        print(f"🔄 Wake word в режимі VAD (детекція голосу)")
        
        # VAD параметри
        self.vad_threshold = 1000  # Поріг гучності (коригується залежно від чутливості)
        self.vad_min_duration = 0.3  # Мінімальна тривалість звуку (секунди)
        
        # Розрахунок кількості чанків для мінімальної тривалості звуку
        self.vad_chunks_count = int(self.vad_min_duration * self.sample_rate / self.chunk_size)
        
        # Коригуємо поріг залежно від чутливості
        self.vad_threshold = int(1500 * (1.0 - self.sensitivity) + 500)
        
        # Відкриваємо мікрофон
        self._open_microphone()
    
    def _open_microphone(self):
        """Відкриває мікрофон для запису з підбором sample rate"""
        try:
            self.audio = pyaudio.PyAudio()

            # Знаходимо USB мікрофон
            device_index = self._find_usb_microphone()

            # Підбираємо sample rate, якщо поточний не підтримується
            candidate_rates = []
            try:
                if device_index is not None:
                    info = self.audio.get_device_info_by_index(device_index)
                    default_rate = int(float(info.get("defaultSampleRate", self.sample_rate)))
                    candidate_rates.append(default_rate)
            except Exception:
                pass
            # Додаємо стандартні частоти та поточну
            candidate_rates.extend([self.sample_rate, 48000, 44100, 22050, 16000])
            # Унікальні, зберігаючи порядок
            seen = set()
            candidate_rates = [r for r in candidate_rates if (r not in seen and not seen.add(r))]

            last_error: Optional[Exception] = None
            for rate in candidate_rates:
                try:
                    stream = self.audio.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=rate,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=self.chunk_size,
                    )
                    # Успіх: фіксуємо обраний rate і потік
                    self.sample_rate = rate
                    self.stream = stream
                    print(
                        f"✅ Мікрофон відкрито"
                        + (f" (device {device_index})" if device_index is not None else "")
                        + f" @ {rate} Hz"
                    )
                    break
                except Exception as e:
                    last_error = e
                    continue

            if self.stream is None:
                # Не вдалося відкрити жоден режим
                raise last_error or OSError("Не вдалося відкрити мікрофон ані з одним sample rate")

        except Exception as e:
            print(f"⚠️ Помилка при відкритті мікрофона: {e}")
            # Закриваємо все, що вже відкрили
            self._cleanup_audio()
            
    def _find_usb_microphone(self) -> Optional[int]:
        """Знаходить індекс USB мікрофона"""
        if self.audio is None:
            return None
            
        try:
            # Перебираємо всі пристрої
            for i in range(self.audio.get_device_count()):
                try:
                    info = self.audio.get_device_info_by_index(i)
                    name = str(info.get('name', '')).lower()
                    
                    # Шукаємо USB мікрофон
                    max_input_channels = int(info.get('maxInputChannels', 0))
                    if 'usb' in name and max_input_channels > 0:
                        print(f"✅ Знайдено USB мікрофон: {name}")
                        return i
                except Exception:
                    continue
                    
            # Якщо USB не знайдено - будь-який вхідний пристрій
            for i in range(self.audio.get_device_count()):
                try:
                    info = self.audio.get_device_info_by_index(i)
                    max_input_channels = int(info.get('maxInputChannels', 0))
                    
                    if max_input_channels > 0:
                        name = str(info.get('name', ''))
                        print(f"✅ Знайдено вхідний пристрій: {name}")
                        return i
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"⚠️ Помилка при пошуку мікрофона: {e}")
            
        return None
        
    def listen(self) -> bool:
        """
        Слухає wake word
        
        Returns:
            True якщо wake word виявлено
        """
        if self.mode == WakeWordMode.FALLBACK:
            return self._listen_fallback()
        elif self.mode == WakeWordMode.VAD:
            return self._listen_vad()
        elif self.mode == WakeWordMode.ALWAYS_ON:
            return self._listen_always_on()
        
        # Якщо невідомий режим
        return False
    
    def _listen_fallback(self) -> bool:
        """Fallback режим - натискання Enter в консолі"""
        print("\n[FALLBACK MODE] Натисни Enter щоб симулювати wake word...")
        try:
            input()
            return True
        except (KeyboardInterrupt, EOFError):
            return False
    
    def _listen_vad(self) -> bool:
        """Voice Activity Detection - виявлення звуку"""
        if self.stream is None:
            # Спроба відкрити знову
            self._open_microphone()
            
            # Якщо не вдалося
            if self.stream is None:
                return False
        
        try:
            active_chunks = 0
            
            # Виводимо очікування тільки раз на початку циклу
            print("🎤 Очікування звуку...")
            
            while True:
                try:
                    # Читаємо аудіо
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Аналізуємо гучність
                    rms = audioop.rms(data, 2)  # 2 bytes per sample (16 bit)
                    
                    # Порівнюємо з порогом
                    if rms > self.vad_threshold:
                        active_chunks += 1
                        if active_chunks >= self.vad_chunks_count:
                            print("🎤 Голосову активність виявлено!")
                            return True
                    else:
                        # Скидаємо лічильник якщо тиша
                        active_chunks = 0
                        
                except IOError:
                    # Помилка читання - перевідкриваємо потік
                    self._cleanup_audio()
                    self._open_microphone()
                    if self.stream is None:
                        return False
                
                # Перевірка на переривання
                if not self.is_running:
                    return False
                
        except Exception as e:
            print(f"⚠️ Помилка в режимі VAD: {e}")
            return False
    
    def _listen_always_on(self) -> bool:
        """Режим без wake word - відразу повертає True"""
        # Маленька затримка для імітації детекції
        time.sleep(0.5)
        return True
    
    def _cleanup_audio(self):
        """Звільнення аудіо ресурсів"""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
            
        if self.audio:
            try:
                self.audio.terminate()
            except Exception:
                pass
            self.audio = None
    
    def stop(self):
        """Зупиняє детектор і звільняє ресурси"""
        self.is_running = False
        self._cleanup_audio()
        print("🛑 Wake word detector зупинено")


# Тест
if __name__ == "__main__":
    print("=== Test Wake Word Detector ===")
    
    detector = WakeWordDetector(mode=WakeWordMode.VAD)
    
    try:
        detector.is_running = True
        count = 0
        while count < 3:
            print(f"\nТест {count+1}/3...")
            if detector.listen():
                print("✅ Wake word виявлено!")
                count += 1
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n⚠️ Тест перервано")
    finally:
        detector.stop()
        print("✅ Тест завершено")