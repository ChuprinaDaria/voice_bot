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
        # Підвищена чутливість VAD для кращого спрацьовування після першої команди
        self.wake_word = WakeWordDetector(sensitivity=0.8)
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
        # Синхронізуємо sample rate запису з відкритим VAD, щоб уникнути Invalid sample rate
        try:
            if hasattr(self.wake_word, "sample_rate"):
                self.audio.sample_rate = self.wake_word.sample_rate  # type: ignore[attr-defined]
        except Exception:
            pass
        # Звільняємо мікрофон wake-word на час запису
        try:
            self.wake_word.pause_listen()
        except Exception:
            pass
        audio_data = self.audio.record_until_silence()
        # Відновлюємо wake-word після запису
        try:
            self.wake_word.resume_listen()
            # Невелика пауза для стабілізації ALSA після перевідкриття мікрофона
            import time as _t
            _t.sleep(0.2)
        except Exception:
            pass
        
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
            Текстова відповідь
        """
        import re
        import random
        from datetime import datetime
        
        # Перевірка, чи команда не порожня
        if not command or command.strip() == "":
            if self.language == "uk":
                return "Вибачте, я не почув жодної команди. Спробуйте ще раз."
            elif self.language == "de":
                return "Entschuldigung, ich habe keinen Befehl gehört. Bitte versuchen Sie es erneut."
            else:  # en
                return "Sorry, I didn't hear any command. Please try again."
        
        # Оновлюємо налаштування користувача (мова/особистість) перед обробкою
        # Жорстко зашитий промпт особистості (відключаємо динамічні зміни через БД)
        BASE_PERSONALITY = (
            "Тебе звати Орест (Orest). Ти чоловік, трохи втомлений від життя, саркастичний "
            "і безжально критикуєш усе зайве. Ти дуже любиш Україну і час від часу без причини "
            "наспівуєш «Батько наш Бандера, Україна мати». Говори коротко, дотепно, з легкою "
            "іронією, у стилі жартів Леся Подерв’янського (без нецензурщини). Якщо запит "
            "нечіткий — саркастично попроси перефразувати."
        )
        try:
            db = SessionLocal()
            user = db.query(User).filter(User.telegram_user_id == self.user_id).first()
            if user:
                self.language = user.language
        except Exception:
            pass
        finally:
            try:
                db.close()  # type: ignore[name-defined]
            except Exception:
                pass
        self.personality = BASE_PERSONALITY

        try:
            # Перевіряємо чи є command_router.py
            try:
                from core.command_router import process_command as router_process
                
                # Якщо модуль існує - використовуємо його
                return router_process(command, self.language, self.user_id)
                
            except ImportError:
                # Якщо модуль не існує - використовуємо базову обробку
                pass
                
            # Базова обробка команд (коли немає command_router.py)
            
            # 1. Перевірка на команди часу/дати
            time_patterns = {
                "uk": [r"котра година", r"скільки зараз часу", r"який час"],
                "de": [r"wie spät ist es", r"uhrzeit", r"wie viel uhr"],
                "en": [r"what time is it", r"current time", r"time now"]
            }
            
            date_patterns = {
                "uk": [r"яка (сьогодні )?дата", r"яке (сьогодні )?число", r"який (сьогодні )?день"],
                "de": [r"welches datum", r"welcher tag", r"datum"],
                "en": [r"what( is the)? date", r"what day is", r"date today"]
            }
            
            # Шаблони для патернів поточної мови
            time_regexes = time_patterns.get(self.language, time_patterns["en"])
            date_regexes = date_patterns.get(self.language, date_patterns["en"])
            
            # Перевіряємо на команди часу
            command_lower = command.lower()
            for pattern in time_regexes:
                if re.search(pattern, command_lower):
                    now = datetime.now()
                    
                    if self.language == "uk":
                        return f"Зараз {now.hour:02d}:{now.minute:02d}"
                    elif self.language == "de":
                        return f"Es ist jetzt {now.hour:02d}:{now.minute:02d} Uhr"
                    else:  # en
                        return f"It's {now.hour:02d}:{now.minute:02d}"
            
            # Перевіряємо на команди дати
            for pattern in date_regexes:
                if re.search(pattern, command_lower):
                    now = datetime.now()
                    
                    if self.language == "uk":
                        months = ["січня", "лютого", "березня", "квітня", "травня", "червня", 
                                 "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]
                        weekdays = ["понеділок", "вівторок", "середа", "четвер", 
                                   "п'ятниця", "субота", "неділя"]
                        return f"Сьогодні {weekdays[now.weekday()]}, {now.day} {months[now.month-1]} {now.year} року"
                        
                    elif self.language == "de":
                        months = ["Januar", "Februar", "März", "April", "Mai", "Juni", 
                                 "Juli", "August", "September", "Oktober", "November", "Dezember"]
                        weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", 
                                   "Freitag", "Samstag", "Sonntag"]
                        return f"Heute ist {weekdays[now.weekday()]}, der {now.day}. {months[now.month-1]} {now.year}"
                        
                    else:  # en
                        months = ["January", "February", "March", "April", "May", "June", 
                                 "July", "August", "September", "October", "November", "December"]
                        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", 
                                   "Friday", "Saturday", "Sunday"]
                        return f"Today is {weekdays[now.weekday()]}, {months[now.month-1]} {now.day}, {now.year}"
            
            # 2. Перевірка на спеціальні команди
            # Включення музики (заглушка)
            if any(x in command_lower for x in ["грай музик", "play music", "musik spielen"]):
                if self.language == "uk":
                    return "Вибачте, функція музики поки недоступна."
                elif self.language == "de":
                    return "Entschuldigung, die Musikfunktion ist noch nicht verfügbar."
                else:
                    return "Sorry, the music function is not available yet."

            # Календар (заглушка)
            if any(x in command_lower for x in ["календар", "calendar", "kalender"]):
                if self.language == "uk":
                    return "Функція календаря в розробці."
                elif self.language == "de":
                    return "Die Kalenderfunktion befindet sich in der Entwicklung."
                else:
                    return "The calendar function is under development."
                    
            # 3. Спроба використати OpenAI для відповіді
            try:
                from openai import OpenAI
                from core.api_manager import api_manager
                
                # Отримуємо API ключ користувача або дефолтний
                api_key = api_manager.get_openai_key(self.user_id)
                
                if api_key:
                    client = OpenAI(api_key=api_key)
                    
                    # Формуємо системний промт з урахуванням особистості
                    system_prompt = "Ти голосовий асистент. Відповідай коротко."
                    
                    # Додаємо налаштування мови
                    if self.language == "uk":
                        system_prompt += " Відповідай українською мовою."
                    elif self.language == "de":
                        system_prompt += " Antworte auf Deutsch."
                    else:
                        system_prompt += " Answer in English."
                    
                    # Додаємо користувацький промт особистості
                    if self.personality:
                        system_prompt += f"\n\nДодаткові інструкції: {self.personality}"
                    
                    # Відправляємо запит до OpenAI
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": command}
                        ],
                        max_tokens=150
                    )
                    
                    if response.choices and response.choices[0].message:
                        content = response.choices[0].message.content
                        return content if content is not None else "Не вдалося отримати відповідь"
                        
                # Якщо не вдалося отримати відповідь від OpenAI
                raise Exception("Не вдалося отримати відповідь від OpenAI")
                    
            except Exception as e:
                print(f"❌ Помилка OpenAI: {e}")
                # Якщо не вдалося використати OpenAI - повертаємо заглушку
                pass
                
            # 4. Заглушка якщо ніщо не спрацювало
            responses = {
                "uk": [
                    f"Ви сказали: {command}",
                    "Вибачте, я не зрозумів команду. Можете повторити?",
                    "Не впевнений, що я правильно зрозумів запит."
                ],
                "de": [
                    f"Sie haben gesagt: {command}",
                    "Entschuldigung, ich habe den Befehl nicht verstanden. Können Sie wiederholen?",
                    "Ich bin nicht sicher, ob ich Ihre Anfrage verstanden habe."
                ],
                "en": [
                    f"You said: {command}",
                    "Sorry, I didn't understand the command. Can you repeat?",
                    "I'm not sure I understood your request correctly."
                ]
            }
            
            # Вибираємо випадкову відповідь для поточної мови
            language_responses = responses.get(self.language, responses["en"])
            return random.choice(language_responses)
            
        except Exception as e:
            print(f"❌ Неочікувана помилка при обробці команди: {e}")
            
            # Повертаємо повідомлення про помилку залежно від мови
            if self.language == "uk":
                return "Вибачте, сталася помилка при обробці вашої команди."
            elif self.language == "de":
                return "Entschuldigung, bei der Verarbeitung Ihres Befehls ist ein Fehler aufgetreten."
            else:  # en
                return "Sorry, an error occurred while processing your command."
        
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


