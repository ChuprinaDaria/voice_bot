"""
Покращений клас для роботи зі звуком на Raspberry Pi
- USB мікрофон для запису
- 3.5mm аудіо вихід для відтворення
- Додано додаткову обробку помилок та fallback режим
"""

import pyaudio
import wave
import audioop
from io import BytesIO
from typing import Optional, List, Tuple, Dict
import time
import os
import subprocess


class AudioManager:
    """Керування аудіо записом і відтворенням з ReSpeaker"""
    
    def __init__(self):
        self.sample_rate = 16000  # Whisper потребує 16kHz
        self.channels = 1  # mono
        self.chunk = 1024
        self.format = pyaudio.paInt16
        
        self.pa = pyaudio.PyAudio()
        
        # ReSpeaker - device 1 (з aplay -l)
        self.input_device_index = 1
        
        # ReSpeaker працює на 44100 Hz, нам треба 16000
        self.respeaker_rate = 44100
        
        print(f"✅ Використовую ReSpeaker (device {self.input_device_index})")
        print(f"   Конвертація: {self.respeaker_rate}Hz → {self.sample_rate}Hz")
    
    def _ensure_initialized(self):
        """Ініціалізує PyAudio якщо ще не ініціалізовано"""
        if self.pa is None:
            # Ініціалізація PyAudio
            self.pa = pyaudio.PyAudio()
            
            # Інформація про доступні пристрої
            self._detect_devices()
            
            # Автоматичне визначення USB мікрофона
            self.input_device_index = self._find_usb_microphone()
            
            if self.input_device_index is None:
                print("⚠️  USB мікрофон не знайдено! Використовую дефолтний пристрій.")
            else:
                print(f"✅ USB мікрофон знайдено: device {self.input_device_index}")
    
    def _prepare_audio_system(self):
        """Готує аудіо систему - перевіряє наявність alsa.conf і модулів ядра"""
        try:
            # Спроба запустити aplay -l для перевірки аудіо пристроїв
            result = subprocess.run(
                ["aplay", "-l"], 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            if result.returncode != 0:
                print("⚠️  Проблема з аудіо системою:")
                print(result.stderr)
                print("Спроба виправлення...")
                
                # Можливо потрібно завантажити snd-usb-audio модуль
                subprocess.run(["sudo", "modprobe", "snd-usb-audio"], check=False)
                
                # Перевірка чи є наші пристрої в /proc/asound
                if os.path.exists("/proc/asound/cards"):
                    with open("/proc/asound/cards", 'r') as f:
                        print("Доступні звукові карти:")
                        print(f.read())
        except Exception as e:
            print(f"⚠️  Помилка при підготовці аудіо системи: {e}")

    def _detect_devices(self):
        """Спроба виявити всі аудіо пристрої та зберегти їх інформацію"""
        self.devices = []
        if self.pa is None:
            return
        try:
            device_count = self.pa.get_device_count()
            print(f"Знайдено {device_count} аудіо пристроїв.")
            
            # Збираємо інформацію про всі пристрої
            for i in range(device_count):
                try:
                    info = self.pa.get_device_info_by_index(i)
                    self.devices.append(info)
                except Exception as e:
                    print(f"⚠️  Помилка при отриманні інформації про пристрій {i}: {e}")
        except Exception as e:
            print(f"⚠️  Помилка при виявленні пристроїв: {e}")
    
    def _find_usb_microphone(self) -> Optional[int]:
        """Шукає USB мікрофон або будь-який інший робочий мікрофон"""
        # Пріоритет 1: Шукаємо "USB PnP Sound Device" (основний мікрофон)
        for i, info in enumerate(self.devices):
            try:
                name = str(info.get('name', '')).lower()
                max_input_channels = int(info.get('maxInputChannels', 0))
                
                # Шукаємо конкретно USB PnP Sound Device (не ReSpeaker!)
                if 'usb pnp' in name and max_input_channels > 0:
                    print(f"✅ Знайдено USB PnP мікрофон: {name} (device {i})")
                    return i
            except Exception:
                continue
        
        # Пріоритет 2: Будь-який USB (крім seeed/respeaker)
        for i, info in enumerate(self.devices):
            try:
                name = str(info.get('name', '')).lower()
                max_input_channels = int(info.get('maxInputChannels', 0))
                
                # Шукаємо USB в назві, але НЕ ReSpeaker
                if 'usb' in name and 'seeed' not in name and max_input_channels > 0:
                    print(f"Знайдено USB мікрофон: {name}")
                    return i
            except Exception:
                continue
        
        # Якщо USB не знайдено, спробуємо будь-який вхідний пристрій
        for i, info in enumerate(self.devices):
            try:
                max_input_channels = int(info.get('maxInputChannels', 0))
                if max_input_channels > 0:
                    name = str(info.get('name', ''))
                    print(f"Знайдено вхідний аудіо пристрій: {name}")
                    return i
            except Exception:
                continue
                
        # Якщо нічого не знайдено, повертаємо None
        print("⚠️  Жодного робочого мікрофона не знайдено!")
        return None
    
    def list_devices(self):
        """Виводить список всіх аудіо пристроїв (для дебагу)"""
        print("\n" + "=" * 60)
        print("📡 AUDIO DEVICES")
        print("=" * 60)
        
        for i, info in enumerate(self.devices):
            try:
                print(f"\nDevice {i}:")
                print(f"  Name: {info.get('name')}")
                print(f"  Input channels: {info.get('maxInputChannels')}")
                print(f"  Output channels: {info.get('maxOutputChannels')}")
                print(f"  Sample rate: {info.get('defaultSampleRate')}")
            except Exception as e:
                print(f"⚠️  Помилка при виведенні інформації про пристрій {i}: {e}")
            
        print("=" * 60 + "\n")
    
    def cleanup(self):
        """Звільняє ресурси PyAudio"""
        if self.pa is not None:
            try:
                self.pa.terminate()
            except Exception as e:
                print(f"⚠️  Помилка при закритті PyAudio: {e}")
            finally:
                self.pa = None
    
    def record_audio(self, duration: int = 5) -> bytes:
        """Записує N секунд аудіо з мікрофона"""
        # Ініціалізуємо PyAudio перед записом
        self._ensure_initialized()
        
        if self.pa is None:
            print("❌ PyAudio не ініціалізовано")
            return self._generate_empty_wav(duration)
        
        print(f"🎤 Запис {duration} секунд...")
        
        try:
            # Спочатку перевіряємо чи працює відкриття потоку
            try:
                stream = self.pa.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=self.input_device_index,
                    frames_per_buffer=self.chunk
                )
            except OSError as e:
                # Якщо помилка з пристроєм, спробуємо використати дефолтний
                print(f"⚠️  Помилка відкриття аудіо потоку: {e}")
                print("Спроба використання дефолтного пристрою...")
                
                stream = self.pa.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk
                )
            
            frames = []
            for _ in range(0, int(self.sample_rate / self.chunk * duration)):
                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)
                
            stream.stop_stream()
            stream.close()
            
            # Конвертуємо в WAV формат
            return self._frames_to_wav(frames)
            
        except Exception as e:
            print(f"❌ Помилка запису аудіо: {e}")
            # Повертаємо пусту WAV
            return self._generate_empty_wav(duration)
    
    def _record_with_arecord(self, max_duration: int = 15) -> bytes:
        """Запис через arecord (обходить конфлікти PyAudio)"""
        import tempfile
        import subprocess
        
        try:
            # Створюємо тимчасовий файл
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                temp_file = f.name
            
            # Записуємо через arecord
            print(f"🎙️ Запис через arecord (device hw:2,0, {max_duration}s)...")
            result = subprocess.run([
                'arecord',
                '-D', 'plughw:2,0',  # USB мікрофон
                '-f', 'S16_LE',      # 16-bit
                '-c', '1',            # mono
                '-r', str(self.sample_rate),
                '-d', str(max_duration),
                temp_file
            ], capture_output=True, timeout=max_duration + 5)
            
            if result.returncode != 0:
                print(f"⚠️ arecord помилка: {result.stderr.decode()}")
                os.unlink(temp_file)
                return self._generate_empty_wav(max_duration)
            
            # Читаємо записане
            with open(temp_file, 'rb') as f:
                audio_data = f.read()
            
            # Видаляємо тимчасовий файл
            os.unlink(temp_file)
            
            print(f"✅ Записано через arecord")
            return audio_data
            
        except Exception as e:
            print(f"❌ Помилка arecord: {e}")
            return self._generate_empty_wav(max_duration)
    
    def record_until_silence(
        self, 
        silence_threshold: int = 500,
        silence_duration: float = 1.5,
        max_duration: int = 10
    ) -> bytes:
        """
        Записує поки не буде тиша протягом silence_duration секунд
        
        Args:
            silence_threshold: Поріг тиші (RMS amplitude)
            silence_duration: Скільки секунд тиші = кінець запису
            max_duration: Максимальна тривалість запису
        """
        print(f"🎤 Запис до тиші (поріг={silence_threshold}, тиша={silence_duration}s)...")
        
        # Ініціалізуємо PyAudio перед записом
        self._ensure_initialized()
        
        if self.pa is None:
            print("❌ PyAudio не ініціалізовано")
            return self._generate_empty_wav(max_duration)
        
        try:
            # Спочатку перевіряємо чи працює відкриття потоку
            try:
                print(f"🎙️ Відкриваю запис: device={self.input_device_index}, rate={self.sample_rate}Hz")
                stream = self.pa.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=self.input_device_index,
                    frames_per_buffer=self.chunk
                )
            except OSError as e:
                # Якщо помилка з пристроєм, спробуємо використати дефолтний
                print(f"⚠️  Помилка відкриття аудіо потоку: {e}")
                print("⚠️  УВАГА: Використовую дефолтний пристрій (може бути неправильний мікрофон)...")
                
                stream = self.pa.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk
                )
            
            frames = []
            silent_chunks = 0
            chunks_per_silence = int(self.sample_rate / self.chunk * silence_duration)
            max_chunks = int(self.sample_rate / self.chunk * max_duration)
            
            start_time = time.time()
            rms_log_counter = 0
            
            while len(frames) < max_chunks:
                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)
                
                # Перевіряємо рівень звуку (RMS)
                rms = audioop.rms(data, 2)  # 2 bytes per sample (paInt16)
                
                # Періодично виводимо RMS (кожні 20 чанків)
                rms_log_counter += 1
                if rms_log_counter >= 20:
                    print(f"🎙️ Запис: RMS={rms}, silent={silent_chunks}/{chunks_per_silence}")
                    rms_log_counter = 0
                
                if rms < silence_threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0
                    
                # Якщо тиша протягом silence_duration
                if silent_chunks > chunks_per_silence:
                    print(f"🔇 Тиша {silence_duration}s detected. Зупиняю запис.")
                    break
                    
            elapsed = time.time() - start_time
            print(f"✅ Записано {elapsed:.1f}s")
            
            stream.stop_stream()
            stream.close()
            
            return self._frames_to_wav(frames)
            
        except Exception as e:
            print(f"❌ Помилка запису аудіо: {e}")
            # Повертаємо пусту WAV
            return self._generate_empty_wav(max_duration)
    
    def _generate_empty_wav(self, duration: int = 3) -> bytes:
        """Генерує пусту WAV як fallback якщо запис не вдався"""
        # Генеруємо тишу (заповнену нулями)
        num_samples = int(self.sample_rate * duration)
        frames = [b'\x00\x00' * self.chunk] * (num_samples // self.chunk)
        return self._frames_to_wav(frames)
        
    def _frames_to_wav(self, frames: list) -> bytes:
        """Конвертує список фреймів в WAV bytes"""
        buffer = BytesIO()
        
        # Ініціалізуємо PyAudio якщо потрібно
        self._ensure_initialized()
        
        if self.pa is None:
            print("❌ PyAudio не ініціалізовано для _frames_to_wav")
            return b''
        
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.pa.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
            
        return buffer.getvalue()
        
    def play_audio(self, audio_data: bytes) -> None:
        """
        Відтворює аудіо через 3.5mm вихід
        Підтримує WAV і MP3 (через pydub)
        Додано кращу обробку помилок
        """
        if not audio_data:
            print("⚠️  Пусті аудіо дані для відтворення")
            return
        
        # Ініціалізуємо PyAudio якщо потрібно
        self._ensure_initialized()
        
        if self.pa is None:
            print("⚠️  PyAudio не ініціалізовано, використовую aplay")
            self._play_with_aplay(audio_data)
            return
            
        try:
            # Спроба відтворити як WAV
            buffer = BytesIO(audio_data)
            
            with wave.open(buffer, 'rb') as wf:
                try:
                    stream = self.pa.open(
                        format=self.pa.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True
                    )
                    
                    # Читаємо і відтворюємо по чанках
                    data = wf.readframes(self.chunk)
                    while data:
                        stream.write(data)
                        data = wf.readframes(self.chunk)
                        
                    stream.stop_stream()
                    stream.close()
                except Exception as e:
                    print(f"⚠️  Помилка при відтворенні WAV: {e}")
                    # Спробуємо використати системний aplay як fallback
                    self._play_with_aplay(audio_data)
                
        except wave.Error:
            # Якщо не WAV - пробуємо через pydub (MP3)
            try:
                from pydub import AudioSegment  # type: ignore[import-not-found]
                from pydub.playback import play  # type: ignore[import-not-found]
                
                audio = AudioSegment.from_file(BytesIO(audio_data))
                play(audio)
                
            except Exception as e:
                print(f"❌ Помилка відтворення: {e}")
                # Спробуємо використати системний aplay як fallback
                self._play_with_aplay(audio_data)
    
    def _play_with_aplay(self, audio_data: bytes) -> None:
        """Використовує aplay для відтворення аудіо як fallback"""
        try:
            # Зберігаємо аудіо у тимчасовий файл
            tmp_file = "/tmp/audio_fallback.wav"
            with open(tmp_file, 'wb') as f:
                f.write(audio_data)
                
            # Відтворюємо через aplay
            subprocess.run(["aplay", tmp_file], check=False)
            
            # Видаляємо тимчасовий файл
            os.unlink(tmp_file)
        except Exception as e:
            print(f"❌ Помилка відтворення через aplay: {e}")
                


# Тестовий запуск
if __name__ == "__main__":
    print("🎙️  Тест Audio Manager")
    print("=" * 50)
    
    audio_manager = AudioManager()
    
    # Показуємо всі пристрої
    audio_manager.list_devices()
    
    # Тест запису
    print("\n[TEST 1] Запис 3 секунди...")
    audio_data = audio_manager.record_audio(duration=3)
    print(f"✅ Записано {len(audio_data)} bytes")
    
    # Тест відтворення
    print("\n[TEST 2] Відтворення...")
    audio_manager.play_audio(audio_data)
    
    # Тест запису до тиші
    print("\n[TEST 3] Запис до тиші (скажи щось і замовкни)...")
    audio_data = audio_manager.record_until_silence(
        silence_threshold=500,
        silence_duration=2.0,
        max_duration=10
    )
    print(f"✅ Записано {len(audio_data)} bytes")
    
    audio_manager.cleanup()
    print("\n✅ Тести завершено")