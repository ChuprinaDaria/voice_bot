"""
Покращений клас для роботи зі звуком на Raspberry Pi з ReSpeaker
- ReSpeaker для запису (з конвертацією sample rate)
- ReSpeaker для відтворення
"""

from typing import Optional
import pyaudio
import wave
import audioop
from io import BytesIO
import time
import subprocess
import os


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
    
    def record_audio(self, duration: int = 5) -> bytes:
        """Записує N секунд аудіо з мікрофона"""
        print(f"🎤 Запис {duration} секунд...")
        
        if self.pa is None:
            raise RuntimeError("AudioManager не ініціалізований. Викличте __init__ або перезапустіть.")
        
        stream = self.pa.open(
            format=self.format,
            channels=1,  # Беремо тільки 1 канал з ReSpeaker
            rate=self.respeaker_rate,  # ReSpeaker працює на 44100
            input=True,
            input_device_index=self.input_device_index,
            frames_per_buffer=self.chunk
        )
        
        frames = []
        for _ in range(0, int(self.respeaker_rate / self.chunk * duration)):
            data = stream.read(self.chunk, exception_on_overflow=False)
            frames.append(data)
            
        stream.stop_stream()
        stream.close()
        
        # Об'єднуємо всі фрейми
        raw_audio = b''.join(frames)
        
        # Конвертуємо sample rate: 44100 → 16000
        resampled = audioop.ratecv(
            raw_audio,
            2,  # 2 bytes per sample (paInt16)
            1,  # mono
            self.respeaker_rate,  # from 44100
            self.sample_rate,  # to 16000
            None
        )[0]
        
        # Конвертуємо в WAV формат
        return self._bytes_to_wav(resampled)
    
    def record_until_silence(
        self, 
        silence_threshold: int = 500,
        silence_duration: float = 1.5,
        max_duration: int = 10
    ) -> bytes:
        """Записує поки не буде тиша"""
        print("🎤 Запис до тиші...")
        print(f"  📋 Параметри: поріг={silence_threshold}, тривалість_тиші={silence_duration}s, макс={max_duration}s")
        
        if self.pa is None:
            raise RuntimeError("AudioManager не ініціалізований. Викличте __init__ або перезапустіть.")
        
        stream = self.pa.open(
            format=self.format,
            channels=1,
            rate=self.respeaker_rate,  # ReSpeaker працює на 44100
            input=True,
            input_device_index=self.input_device_index,
            frames_per_buffer=self.chunk
        )
        
        frames = []
        silent_chunks = 0
        chunks_per_silence = int(self.respeaker_rate / self.chunk * silence_duration)
        max_chunks = int(self.respeaker_rate / self.chunk * max_duration)
        
        start_time = time.time()
        
        while len(frames) < max_chunks:
            data = stream.read(self.chunk, exception_on_overflow=False)
            frames.append(data)
            
            # Перевіряємо рівень звуку
            rms = audioop.rms(data, 2)
            
            # ДОДАЙ ЦЕ - показуємо RMS кожні 20 chunks
            if len(frames) % 20 == 0:
                print(f"  📊 RMS: {rms}, Тиша: {silent_chunks}/{chunks_per_silence}, Поріг: {silence_threshold}")
            
            if rms < silence_threshold:
                silent_chunks += 1
            else:
                silent_chunks = 0
                
            if silent_chunks > chunks_per_silence:
                print(f"🔇 Тиша {silence_duration}s detected.")
                break
                
        elapsed = time.time() - start_time
        print(f"✅ Записано {elapsed:.1f}s")
        
        # Отримуємо останній RMS значення
        last_rms = 0
        if frames:
            try:
                last_rms = audioop.rms(frames[-1], 2)
            except:
                last_rms = 0
        
        print(f"  📊 Підсумок: {len(frames)} chunks, останній RMS: {last_rms}")
        
        stream.stop_stream()
        stream.close()
        
        # Об'єднуємо і конвертуємо
        raw_audio = b''.join(frames)
        
        # Resample: 44100 → 16000
        resampled = audioop.ratecv(
            raw_audio,
            2,
            1,
            self.respeaker_rate,
            self.sample_rate,
            None
        )[0]
        
        return self._bytes_to_wav(resampled)
    
    def _bytes_to_wav(self, audio_bytes: bytes) -> bytes:
        """Конвертує raw audio bytes в WAV"""
        if self.pa is None:
            raise RuntimeError("AudioManager не ініціалізований. Викличте __init__ або перезапустіть.")
        
        buffer = BytesIO()
        
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.pa.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)  # 16000 Hz
            wf.writeframes(audio_bytes)
            
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

    def cleanup(self):
        """Звільняє ресурси"""
        if self.pa:
            self.pa.terminate()
            self.pa = None
