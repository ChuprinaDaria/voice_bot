"""
Клас для роботи зі звуком на Raspberry Pi
- USB мікрофон для запису
- 3.5mm аудіо вихід для відтворення
"""

import pyaudio
import wave
import audioop
from io import BytesIO
from typing import Optional
import time


class AudioManager:
    """Керування аудіо записом і відтворенням"""
    
    def __init__(self):
        self.sample_rate = 16000  # 16kHz для Whisper
        self.channels = 1  # mono
        self.chunk = 1024
        self.format = pyaudio.paInt16
        
        self.pa = pyaudio.PyAudio()
        
        # Автоматичне визначення USB мікрофона
        self.input_device_index = self._find_usb_microphone()
        
        if self.input_device_index is None:
            print("⚠️  USB мікрофон не знайдено! Використовую дефолтний.")
        else:
            print(f"✅ USB мікрофон знайдено: device {self.input_device_index}")
        
    def _find_usb_microphone(self) -> Optional[int]:
        """Шукає USB мікрофон серед аудіо пристроїв"""
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            name = str(info.get('name', '')).lower()
            
            # Шукаємо USB в назві і перевіряємо що це INPUT пристрій
            max_input_channels = int(info.get('maxInputChannels', 0))
            if 'usb' in name and max_input_channels > 0:
                return i
                
        return None
        
    def record_audio(self, duration: int = 5) -> bytes:
        """Записує N секунд аудіо з мікрофона"""
        print(f"🎤 Запис {duration} секунд...")
        
        stream = self.pa.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.input_device_index,
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
        print("🎤 Запис до тиші...")
        
        stream = self.pa.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.input_device_index,
            frames_per_buffer=self.chunk
        )
        
        frames = []
        silent_chunks = 0
        chunks_per_silence = int(self.sample_rate / self.chunk * silence_duration)
        max_chunks = int(self.sample_rate / self.chunk * max_duration)
        
        start_time = time.time()
        
        while len(frames) < max_chunks:
            data = stream.read(self.chunk, exception_on_overflow=False)
            frames.append(data)
            
            # Перевіряємо рівень звуку (RMS)
            rms = audioop.rms(data, 2)  # 2 bytes per sample (paInt16)
            
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
        
    def _frames_to_wav(self, frames: list) -> bytes:
        """Конвертує список фреймів в WAV bytes"""
        buffer = BytesIO()
        
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
        """
        try:
            # Спроба відтворити як WAV
            buffer = BytesIO(audio_data)
            
            with wave.open(buffer, 'rb') as wf:
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
                
        except wave.Error:
            # Якщо не WAV - пробуємо через pydub (MP3)
            try:
                from pydub import AudioSegment  # type: ignore[import-not-found]
                from pydub.playback import play  # type: ignore[import-not-found]
                
                audio = AudioSegment.from_file(BytesIO(audio_data))
                play(audio)
                
            except Exception as e:
                print(f"❌ Помилка відтворення: {e}")
                
    def list_devices(self):
        """Виводить список всіх аудіо пристроїв (для дебагу)"""
        print("\n" + "=" * 60)
        print("📡 AUDIO DEVICES")
        print("=" * 60)
        
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            print(f"\nDevice {i}:")
            print(f"  Name: {info.get('name')}")
            print(f"  Input channels: {info.get('maxInputChannels')}")
            print(f"  Output channels: {info.get('maxOutputChannels')}")
            print(f"  Sample rate: {info.get('defaultSampleRate')}")
            
        print("=" * 60 + "\n")
        
    def cleanup(self):
        """Звільнення ресурсів"""
        self.pa.terminate()


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
