"""
Daemon який запускається на Raspberry Pi
Слухає wake word → записує команду → розпізнає → виконує → відповідає
"""

import time
from core.wake_word import WakeWordDetector
from hardware.led_controller import led_controller
from core.audio_manager import AudioManager
from voice.stt import transcribe_audio
from core.tts import text_to_speech
from storage.database import SessionLocal
from storage.models import User
from core.command_router import process_command as route_command


class VoiceDaemon:
    def __init__(self, telegram_user_id: int):
        self.user_id = telegram_user_id
        self.wake_word = WakeWordDetector()
        self.audio = AudioManager()
        self.is_running = False
        self.language = "uk"
        self.personality = None
        
    def load_user_settings(self):
        """Завантажує налаштування з БД"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(
                User.telegram_user_id == self.user_id
            ).first()
        finally:
            db.close()
        
        if user:
            self.language = user.language
            self.personality = user.personality_prompt
            return True
        return False
        
    def start(self, listen_immediately: bool = False):
        """Запускає daemon

        Args:
            listen_immediately: Якщо True — одразу записати команду без wake word
        """
        if not self.load_user_settings():
            print("❌ Користувач не знайдений")
            return
            
        self.is_running = True
        print(f"✅ Daemon запущено (мова: {self.language})")
        
        while self.is_running:
            # Якщо потрібно одразу слухати — один раз виконуємо команду
            if listen_immediately:
                try:
                    led_controller.start_listening()
                except Exception:
                    pass
                self.handle_command()
                listen_immediately = False
                continue

            # Звичайний режим: чекаємо wake word
            if self.wake_word.listen():
                print("🎤 Wake word detected!")
                try:
                    led_controller.start_listening()
                except Exception:
                    pass
                self.handle_command()
                
    def handle_command(self):
        """Обробляє голосову команду"""
        # 1. Сигнал що слухаємо
        print("👂 Слухаю команду...")
        
        # 2. Записуємо аудіо
        audio_data = self.audio.record_until_silence()
        
        # 3. Розпізнаємо (STT)
        command = transcribe_audio(self.user_id, audio_data)
        print(f"📝 Розпізнано: {command}")
        
        # 4. Обробляємо команду
        try:
            led_controller.start_thinking()
        except Exception:
            pass
        response = self.process_command(command)
        
        # 5. Відповідаємо голосом (TTS)
        audio_response = text_to_speech(
            self.user_id, 
            response, 
            self.language
        )
        try:
            led_controller.start_speaking()
        except Exception:
            pass
        self.audio.play_audio(audio_response)
        try:
            led_controller.blink_success()
        except Exception:
            pass
        
    def process_command(self, command: str) -> str:
        """
        Обробляє команду і повертає текстову відповідь
        
        Args:
            command: Текст команди
            
        Returns:
            Текстова відповідь для озвучування
        """
        if not command:
            # Якщо команда порожня - повідомлення залежно від мови
            if self.language == "uk":
                return "Вибачте, я нічого не почув. Спробуйте знову."
            elif self.language == "de":
                return "Entschuldigung, ich habe nichts gehört. Bitte versuchen Sie es erneut."
            else:  # en
                return "Sorry, I didn't hear anything. Please try again."
                
        # Виводимо розпізнаний текст
        print(f"📝 Розпізнано: {command}")
        
        try:
            # Використовуємо маршрутизатор команд для обробки
            response = route_command(command, self.language, self.user_id)
            
            # Перевіряємо що відповідь не порожня
            if not response:
                if self.language == "uk":
                    response = "Вибачте, я не зміг знайти відповідь на ваше питання."
                elif self.language == "de":
                    response = "Es tut mir leid, ich konnte keine Antwort auf Ihre Frage finden."
                else:  # en
                    response = "Sorry, I couldn't find an answer to your question."
                    
            return response
            
        except Exception as e:
            # У випадку помилки
            print(f"❌ Помилка при обробці команди: {e}")
            
            if self.language == "uk":
                return "Вибачте, сталася помилка при обробці вашого запиту."
            elif self.language == "de":
                return "Entschuldigung, bei der Verarbeitung Ihrer Anfrage ist ein Fehler aufgetreten."
            else:  # en
                return "Sorry, an error occurred while processing your request."
        
    def stop(self):
        """Зупиняє daemon"""
        self.is_running = False
        self.wake_word.stop()
        try:
            led_controller.stop_animation()
            led_controller.turn_off()
        except Exception:
            pass
        print("🛑 Daemon зупинено")


if __name__ == "__main__":
    # Тестовий запуск
    # TODO: Взяти telegram_user_id з якогось конфіга
    daemon = VoiceDaemon(telegram_user_id=123456789)
    daemon.start()


