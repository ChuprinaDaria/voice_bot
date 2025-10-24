"""
Покращений клас для роботи зі звуком на Raspberry Pi з ReSpeaker
- ReSpeaker для запису (з конвертацією sample rate)
- ReSpeaker для відтворення
"""

import os
os.environ['JACK_NO_START_SERVER'] = '1'  # Заткнути Jack spam

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
        
        # INPUT: USB мікрофон (device 0)
        self.input_device_index = 0
        self.device_rate = 44100  # USB мікрофон працює на 44100
        
        # OUTPUT: ReSpeaker (device 1) - 2 канали для стерео
        self.output_device_index = 1
        
        print(f"✅ INPUT: USB мікрофон (device {self.input_device_index}) @ {self.device_rate}Hz")
        print(f"✅ OUTPUT: ReSpeaker (device {self.output_device_index})")
        print(f"✅ Whisper sample rate: {self.sample_rate}Hz")
        
        # Дебаг output device
        self.debug_output_device()
    
    def debug_output_device(self):
        """Показує параметри output пристрою"""
        if self.output_device_index is None or self.pa is None:
            print("❌ Output device не знайдено")
            return
        
        try:
            info = self.pa.get_device_info_by_index(self.output_device_index)
            print(f"\n📊 OUTPUT DEVICE INFO:")
            print(f"   Назва: {info['name']}")
            print(f"   Channels: {info['maxOutputChannels']}")
            print(f"   Default SR: {info['defaultSampleRate']}")
            
            # Тестуємо різні sample rates
            test_rates = [8000, 16000, 22050, 24000, 44100, 48000]
            print(f"\n🧪 Підтримувані sample rates:")
            for rate in test_rates:
                try:
                    self.pa.is_format_supported(
                        rate,
                        output_device=self.output_device_index,
                        output_channels=2,
                        output_format=pyaudio.paInt16
                    )
                    print(f"   ✅ {rate}Hz")
                except ValueError:
                    print(f"   ❌ {rate}Hz")
        except Exception as e:
            print(f"⚠️  Помилка дебагу output device: {e}")
    
    def record_audio(self, duration: int = 5) -> bytes:
        """Записує N секунд аудіо з мікрофона"""
        print(f"🎤 Запис {duration} секунд...")
        
        if self.pa is None:
            raise RuntimeError("AudioManager не ініціалізований. Викличте __init__ або перезапустіть.")
        
        stream = self.pa.open(
            format=self.format,
            channels=1,  # USB мікрофон mono
            rate=self.device_rate,  # USB мікрофон працює на 44100
            input=True,
            input_device_index=self.input_device_index,
            frames_per_buffer=self.chunk
        )
        
        frames = []
        for _ in range(0, int(self.device_rate / self.chunk * duration)):
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
            self.device_rate,  # from 44100
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
            rate=self.device_rate,  # USB мікрофон працює на 44100
            input=True,
            input_device_index=self.input_device_index,
            frames_per_buffer=self.chunk
        )
        
        frames = []
        silent_chunks = 0
        chunks_per_silence = int(self.device_rate / self.chunk * silence_duration)
        max_chunks = int(self.device_rate / self.chunk * max_duration)
        
        start_time = time.time()
        
        speech_detected = False
        speech_chunks = 0
        
        while len(frames) < max_chunks:
            data = stream.read(self.chunk, exception_on_overflow=False)
            frames.append(data)
            
            # Перевіряємо рівень звуку
            rms = audioop.rms(data, 2)
            
            # Показуємо RMS кожні 10 chunks для кращої діагностики
            if len(frames) % 10 == 0:
                print(f"  📊 RMS: {rms}, Тиша: {silent_chunks}/{chunks_per_silence}, Поріг: {silence_threshold}")
            
            # Якщо RMS вище порогу - це мова
            if rms >= silence_threshold:
                speech_detected = True
                speech_chunks += 1
                silent_chunks = 0
                print(f"  🗣️ Мова детектована! RMS: {rms}")
            else:
                # Якщо мова вже була детектована, рахуємо тишу
                if speech_detected:
                    silent_chunks += 1
                    if silent_chunks > chunks_per_silence:
                        print(f"🔇 Тиша {silence_duration}s після мови detected.")
                        break
                else:
                    # Якщо мова ще не почалася, скидаємо лічильник тиші
                    silent_chunks = 0
                
        elapsed = time.time() - start_time
        
        # Перевіряємо чи була детектована мова
        if not speech_detected:
            print(f"⚠️  Мова не детектована за {elapsed:.1f}s (максимум {max_duration}s)")
        else:
            print(f"✅ Записано {elapsed:.1f}s (мова детектована)")
        
        # Отримуємо останній RMS значення
        last_rms = 0
        if frames:
            try:
                last_rms = audioop.rms(frames[-1], 2)
            except:
                last_rms = 0
        
        print(f"  📊 Підсумок: {len(frames)} chunks, мова: {speech_detected}, останній RMS: {last_rms}")
        
        stream.stop_stream()
        stream.close()
        
        # Об'єднуємо і конвертуємо
        raw_audio = b''.join(frames)
        
        # Resample: 44100 → 16000
        resampled = audioop.ratecv(
            raw_audio,
            2,
            1,
            self.device_rate,
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
        """Відтворює аудіо (WAV або MP3) з auto-resampling"""
        print(f"🔊 Відтворення {len(audio_data)} bytes...")
        
        if self.pa is None:
            print("⚠️  PyAudio не ініціалізовано, використовую aplay")
            self._play_with_aplay(audio_data)
            return
        
        try:
            from pydub import AudioSegment
            
            # Визначаємо формат
            if audio_data[:4] == b'RIFF':
                audio = AudioSegment.from_wav(BytesIO(audio_data))
            else:
                audio = AudioSegment.from_mp3(BytesIO(audio_data))
            
            print(f"   Формат: {'WAV' if audio_data[:4] == b'RIFF' else 'MP3'}")
            print(f"   Оригінал: {audio.channels}ch, {audio.frame_rate}Hz, {audio.sample_width*8}bit")
            
            # RESAMPLE до підтримуваного rate
            target_rate = 48000
            if audio.frame_rate != target_rate:
                print(f"   🔄 Resampling {audio.frame_rate}Hz → {target_rate}Hz")
                audio = audio.set_frame_rate(target_rate)
            
            # Конвертуємо mono → stereo
            if audio.channels == 1:
                print(f"   🔄 Конвертую mono → stereo")
                audio = audio.set_channels(2)
            
            raw_data = audio.raw_data
            sample_width = audio.sample_width
            channels = audio.channels
            frame_rate = audio.frame_rate
            
            print(f"   ✅ Фінальні параметри: {channels}ch, {frame_rate}Hz, {sample_width*8}bit")
            
            # ВАЖЛИВО: chunk size для 48kHz stereo
            # 1024 frames * 2 channels * 2 bytes = 4096 bytes
            chunk_frames = 1024
            chunk_bytes = chunk_frames * channels * sample_width
            
            print(f"   📦 Chunk size: {chunk_frames} frames = {chunk_bytes} bytes")
            
            # Відкриваємо stream з правильними параметрами
            stream = self.pa.open(
                format=self.pa.get_format_from_width(sample_width),
                channels=channels,
                rate=frame_rate,
                output=True,
                output_device_index=self.output_device_index,
                frames_per_buffer=chunk_frames  # ВАЖЛИВО!
            )
            
            print(f"   ▶️ Відтворюю {len(raw_data)} bytes...")
            
            # Пишемо по чанках
            bytes_written = 0
            for i in range(0, len(raw_data), chunk_bytes):
                chunk = raw_data[i:i + chunk_bytes]
                stream.write(chunk)
                bytes_written += len(chunk)
                
                # Прогрес кожні 10%
                progress = (bytes_written / len(raw_data)) * 100
                if progress % 10 < 0.1:  # грубо кожні 10%
                    print(f"   📊 {progress:.0f}%", end='\r')
            
            print(f"\n   ✅ Відтворено {bytes_written} bytes")
            
            # Чекаємо поки все відтвориться
            import time
            time.sleep(0.1)
            
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            print(f"❌ Помилка відтворення: {e}")
            import traceback
            traceback.print_exc()
    
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
