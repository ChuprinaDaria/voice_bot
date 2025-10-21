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
import subprocess
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
        self.vad_threshold = 400  # Початковий поріг (буде перезаписаний після калібрування)
        self.vad_min_duration = 0.3  # Мінімальна тривалість звуку (секунди) - зменшено для чутливості
        
        # Розрахунок кількості чанків для мінімальної тривалості звуку
        self.vad_chunks_count = max(3, int(self.vad_min_duration * self.sample_rate / self.chunk_size))

        # Відкриваємо мікрофон
        self._open_microphone()

        # Автокалібрування порогу від реального фонового шуму
        self._auto_calibrate_threshold()
        
        # Фінальний вивід після калібрування
        print(f"✅ VAD готовий: поріг={self.vad_threshold}, min_chunks={self.vad_chunks_count}, sr={self.sample_rate}")
    
    def _open_microphone(self):
        """Відкриває мікрофон для запису з підбором sample rate та ретраями."""
        import time as _t
        attempts = 3
        backoff = 0.4
        last_error: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            try:
                # Завжди створюємо свіжий контекст PyAudio на спробу
                self._cleanup_audio()
                self.audio = pyaudio.PyAudio()

                # Визначаємо індекс пристрою захоплення (USB мікрофон пріоритетно)
                device_index = self._resolve_preferred_input_device()

                # Кандидати пристрою: спочатку знайдений, потім дефолтний (None)
                device_candidates: List[Optional[int]] = [device_index, None]

                # Підбираємо sample rate, якщо поточний не підтримується
                candidate_rates: List[int] = []
                try:
                    if device_index is not None:
                        info = self.audio.get_device_info_by_index(device_index)
                        default_rate = int(float(info.get("defaultSampleRate", self.sample_rate)))
                        candidate_rates.append(default_rate)
                except Exception:
                    pass
                # Випробовуємо частоти у порядку пріоритету (16k для STT, далі типові)
                candidate_rates.extend([16000, 44100, 48000, 22050, self.sample_rate])
                # Унікальні, зберігаючи порядок
                seen = set()
                candidate_rates = [r for r in candidate_rates if (r not in seen and not seen.add(r))]

                opened = False
                for dev in device_candidates:
                    for rate in candidate_rates:
                        try:
                            stream = self.audio.open(
                                format=pyaudio.paInt16,
                                channels=1,
                                rate=rate,
                                input=True,
                                input_device_index=dev,
                                frames_per_buffer=self.chunk_size,
                            )
                            self.sample_rate = rate
                            self.stream = stream
                            print(
                                "✅ Мікрофон відкрито"
                                + (f" (device {dev})" if dev is not None else " (default device)")
                                + f" @ {rate} Hz"
                            )
                            opened = True
                            break
                        except Exception as e:
                            last_error = e
                            continue
                    if opened:
                        break

                if opened:
                    return

                # Якщо не відкрився — кидати помилку для цього раунду
                raise last_error or OSError("Не вдалося відкрити мікрофон")

            except Exception as e:
                print(f"⚠️ Помилка при відкритті мікрофона (спроба {attempt}/{attempts}): {e}")
                last_error = e
                # Невеликий бекоф перед повтором
                _t.sleep(backoff)
                continue

        # Після всіх спроб — віддати останню помилку та прибрати ресурси
        self._cleanup_audio()
        if last_error:
            print(f"⚠️ Помилка при відкритті мікрофона (остаточно): {last_error}")

    def _check_wake_word(self) -> bool:
        """
        Перевіряє чи було сказано wake word "Орест"
        Записує коротке аудіо і розпізнає через Whisper
        """
        try:
            print("👂 Перевіряю чи це 'Орест'...")
            
            # Записуємо 2 секунди аудіо
            frames = []
            for _ in range(int(self.sample_rate / self.chunk_size * 2)):  # 2 секунди
                if self.stream:
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    frames.append(data)
            
            # Зберігаємо в WAV
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_file = f.name
            
            wf = wave.open(temp_file, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            # Розпізнаємо через Whisper (потрібен user_id - використовуємо 0 для wake word)
            from voice.stt import transcribe_audio
            text = transcribe_audio(0, temp_file, language="uk").lower()
            
            # Видаляємо тимчасовий файл
            os.unlink(temp_file)
            
            print(f"🎧 Почув: '{text}'")
            
            # Перевіряємо чи є "орест" в розпізнаному тексті
            wake_words = ["орест", "orest", "арест", "рест"]  # Варіанти розпізнавання
            if any(word in text for word in wake_words):
                print("✅ Wake word 'Орест' розпізнано!")
                return True
            else:
                print("❌ Не wake word, продовжую слухати...")
                return False
                
        except Exception as e:
            print(f"⚠️  Помилка перевірки wake word: {e}")
            # При помилці пропускаємо (працюємо як звичайний VAD)
            return True
    
    def _auto_calibrate_threshold(self) -> None:
        """Вимірює фоновий шум і уточнює поріг VAD."""
        if not self.stream:
            return
        try:
            # Беремо ~0.5 секунди для оцінки шуму
            measure_seconds = 0.5
            chunks_to_measure = max(1, int(self.sample_rate * measure_seconds / self.chunk_size))
            values = []
            for _ in range(chunks_to_measure):
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                rms = audioop.rms(data, 2)
                values.append(rms)
            if values:
                noise = sum(values) / len(values)
                # Спрощена формула: шум * коефіцієнт залежно від чутливості
                # При sensitivity=0.8 → множник ~1.5, при sensitivity=0.5 → множник ~2.0
                multiplier = 3.0 - (self.sensitivity * 2.0)  # 0.8→1.4, 0.5→2.0, 0.3→2.4
                adaptive = int(noise * multiplier)
                # Мінімум 200, максимум 800 для запобігання занадто високих порогів
                self.vad_threshold = max(min(adaptive, 800), 200)
                print(f"🔧 Калібровано: шум={int(noise)}, поріг={self.vad_threshold}")
        except Exception:
            # Безпечний фолбек — залишаємо попередній поріг
            pass
            
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

    def _resolve_preferred_input_device(self) -> Optional[int]:
        """Повертає індекс бажаного вхідного пристрою.

        Логіка:
        1) Якщо задано змінну оточення MIC_ALSA_HW (наприклад, "2,0" або "hw:2,0") —
           шукаємо PyAudio-пристрій, у якого назва містить відповідний (hw:X,Y).
        2) Інакше — шукаємо USB мікрофон.
        3) Якщо не знайдено — None (дефолтний).
        """
        if self.audio is None:
            return None
        try:
            hw_hint = os.environ.get("MIC_ALSA_HW")
            if hw_hint:
                normalized = hw_hint
                if "," in normalized and not normalized.startswith("hw:"):
                    normalized = f"hw:{normalized}"
                # Пошук збігу у назві PyAudio пристрою
                for i in range(self.audio.get_device_count()):
                    try:
                        info = self.audio.get_device_info_by_index(i)
                        name = str(info.get('name', '')).lower()
                        max_in = int(info.get('maxInputChannels', 0))
                        if max_in > 0 and normalized.lower() in name:
                            print(f"✅ Обрано пристрій за MIC_ALSA_HW={normalized}: {name}")
                            return i
                    except Exception:
                        continue
                print(f"⚠️ MIC_ALSA_HW задано ({normalized}), але відповідний пристрій не знайдено")

            # За замовчуванням — USB мікрофон
            return self._find_usb_microphone()
        except Exception as e:
            print(f"⚠️ Помилка визначення пріоритетного пристрою: {e}")
            return None

    def debug_audio_system(self) -> None:
        """Виводить базову діагностику аудіосистеми (за наявності утиліт)."""
        try:
            print("=== Діагностика аудіо ===")
            os.system("ps aux | grep -E 'pulse|alsa|audio' | grep -v grep")
            os.system("ls -la /dev/snd/")
            os.system("aplay -l")
            os.system("arecord -l")
            print("=========================")
        except Exception:
            pass

    def record_quick_test(self, hw: str = "plughw:2,0") -> None:
        """Швидкий запис/відтворення через ALSA утиліти (діагностика поза PyAudio)."""
        try:
            subprocess.run(["arecord", "-D", hw, "-f", "S16_LE", "-r", "16000", "-d", "3", "/tmp/test.wav"], check=False)
            subprocess.run(["aplay", "/tmp/test.wav"], check=False)
        except Exception as e:
            print(f"⚠️ arecord/aplay тест не вдався: {e}")
    
    def _find_respeaker_device(self) -> Optional[int]:
        """Знаходить ReSpeaker серед аудіо пристроїв (Seeed/ReSpeaker), з фолбеком на USB."""
        if self.audio is None:
            return None
        try:
            for i in range(self.audio.get_device_count()):
                try:
                    info = self.audio.get_device_info_by_index(i)
                    name = str(info.get('name', '')).lower()
                    max_in = int(info.get('maxInputChannels', 0))
                    if max_in > 0 and ('seeed' in name or 'respeaker' in name):
                        print(f"✅ ReSpeaker знайдено: {name}")
                        return i
                except Exception:
                    continue
            # Фолбек
            return self._find_usb_microphone()
        except Exception as e:
            print(f"⚠️ Помилка пошуку ReSpeaker: {e}")
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
            silence_chunks = 0
            
            # Виводимо очікування тільки раз на початку циклу
            print(f"🎤 Очікування звуку (поріг: {self.vad_threshold})...")
            
            # Лічильник для періодичного виводу RMS
            rms_log_counter = 0
            
            while True:
                try:
                    # Читаємо аудіо
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Аналізуємо гучність
                    rms = audioop.rms(data, 2)  # 2 bytes per sample (16 bit)
                    
                    # Періодично виводимо RMS для діагностики (кожні 50 чанків = ~1сек)
                    rms_log_counter += 1
                    if rms_log_counter >= 50:
                        print(f"🔊 RMS: {rms} (поріг: {self.vad_threshold})")
                        rms_log_counter = 0
                    
                    # Порівнюємо з порогом
                    if rms > self.vad_threshold:
                        active_chunks += 1
                        silence_chunks = 0  # Скидаємо лічильник тиші
                        print(f"✓ Звук: RMS={rms} ({active_chunks}/{self.vad_chunks_count})")
                        if active_chunks >= self.vad_chunks_count:
                            print("🎤 Голосову активність виявлено!")
                            # Перевіряємо чи це wake word "Орест"
                            if self._check_wake_word():
                                return True
                            else:
                                # Не wake word - продовжуємо слухати
                                active_chunks = 0
                                silence_chunks = 0
                    else:
                        # Дозволяємо 2 тихих чанки перед скиданням
                        silence_chunks += 1
                        if silence_chunks > 2:
                            active_chunks = 0
                            silence_chunks = 0
                        
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

    def pause_listen(self) -> None:
        """Тимчасово зупиняє прослуховування (звільняє пристрій захоплення)."""
        self._cleanup_audio()

    def resume_listen(self) -> None:
        """Відновлює прослуховування після паузи (лише для VAD/ALWAYS_ON)."""
        if self.mode == WakeWordMode.VAD and self.is_running:
            self._open_microphone()


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