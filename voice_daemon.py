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
        
        # Коротка пауза перед записом (щоб користувач встиг почати говорити після wake word)
        import time
        time.sleep(0.3)
        
        # Записуємо через arecord (обходить конфлікт з WakeWordDetector який тримає Device 0)
        audio_data = self.audio._record_with_arecord(max_duration=10)
        
        # КРИТИЧНО: звільняємо PyAudio ресурси перед відновленням VAD
        try:
            self.audio.cleanup()
        except Exception as e:
            print(f"⚠️  Помилка cleanup AudioManager: {e}")
        
        # Невелика пауза для стабілізації ALSA
        import time as _t
        _t.sleep(0.3)
        
        # Відновлюємо wake-word після запису
        try:
            self.wake_word.resume_listen()
        except Exception as e:
            print(f"⚠️  Помилка resume_listen: {e}")
        
        # 3. Розпізнаємо (STT) з вказанням мови для точності
        command = transcribe_audio(self.user_id, audio_data, language=self.language)
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
            self.language,
            voice="onyx"  # Глибокий чоловічий голос
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
        Обробляє команду з застосуванням промпту особистості "Орест" через OpenAI
        
        Архітектура:
        1. Отримуємо базову відповідь від command_router (факти: час, дата, веб-пошук)
        2. Пропускаємо через OpenAI з промптом особистості для стилізації
        3. Повертаємо відповідь у стилі "Ореста"
        """
        import re
        import random
        from datetime import datetime
        from openai import OpenAI
        from core.api_manager import api_manager
        
        # Перевірка, чи команда не порожня
        if not command or command.strip() == "":
            if self.language == "uk":
                return "Вибачте, я не почув жодної команди. Спробуйте ще раз."
            elif self.language == "de":
                return "Entschuldigung, ich habe keinen Befehl gehört. Bitte versuchen Sie es erneut."
            else:
                return "Sorry, I didn't hear any command. Please try again."
        
        # Жорстко зашитий промпт особистості
        BASE_PERSONALITY = (
            "Тебе звати Орест (Orest). Ти чоловік, веселий, саркастичний "
            "і безжально критикуєш усе зайве. Ти дуже любиш Україну і час від часу без причини "
            "наспівуєш «Батько наш Бандера, Україна мати». Говори коротко, дотепно, з легкою "
            "іронією, у стилі жартів Леся Подерв'янського (без нецензурщини). Якщо запит "
            "нечіткий — саркастично попроси перефразувати."
        )
        
        # Оновлюємо мову користувача з БД
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
        
        # КРОК 1: Отримуємо базову відповідь (факти) від command_router
        base_response = None
        is_fallback = False
        
        try:
            from core.command_router import process_command as router_process
            base_response = router_process(command, self.language, self.user_id)
            
            # Перевіряємо чи це fallback відповідь
            fallback_keywords = [
                "не зрозумів", "didn't understand", "nicht verstanden",
                "не впевнений", "not sure", "nicht sicher",
                "не розпізнав", "didn't recognize", "nicht erkannt"
            ]
            is_fallback = any(keyword in base_response.lower() for keyword in fallback_keywords)
            
            # Якщо це НЕ fallback (тобто конкретна команда: час, дата, погода)
            # → повертаємо відповідь БЕЗ OpenAI для швидкості
            if not is_fallback:
                print(f"✓ Router обробив: {base_response[:50]}...")
                return base_response
            
            # Якщо fallback → переходимо до OpenAI
            print(f"⚠️  Router не розпізнав команду, використовую OpenAI...")
                
        except ImportError:
            # Якщо модуль не існує - використовуємо базову обробку
            pass
        except Exception as e:
            print(f"⚠️  Помилка router: {e}")
        
        # КРОК 2: Пропускаємо через LLM (Groq/OpenAI) з промптом особистості
        # (тільки для fallback або складних запитів)
        try:
            import time
            start_time = time.time()
            
            # Використовуємо тільки API (Groq/OpenAI)
            # Спочатку перевіряємо Groq з .env
            from config import settings
            groq_key = settings.groq_api_key
            
            if groq_key:
                # Використовуємо Groq з .env
                api_key = groq_key
                is_groq = True
            else:
                # Fallback: OpenAI/Groq з БД користувача
                api_key = api_manager.get_openai_key(self.user_id)
                is_groq = api_key.startswith("gsk_") if api_key else False
            
            if api_key:
                if is_groq:
                    # Groq API (5x швидше!)
                    client = OpenAI(
                        api_key=api_key,
                        base_url="https://api.groq.com/openai/v1"
                    )
                    model = "llama-3.1-8b-instant"  # Швидка модель
                    print("⚡ Використовую Groq API (швидкий режим)")
                else:
                    # Стандартний OpenAI
                    client = OpenAI(api_key=api_key)
                    model = "gpt-3.5-turbo"
                    print("🤖 Використовую OpenAI API")
                
                # Формуємо системний промт
                system_prompt = f"{BASE_PERSONALITY}\n\nВідповідай українською мовою коротко (1-2 речення)."
                
                if self.language == "de":
                    system_prompt = f"{BASE_PERSONALITY}\n\nAntworte auf Deutsch kurz (1-2 Sätze)."
                elif self.language == "en":
                    system_prompt = f"{BASE_PERSONALITY}\n\nAnswer in English briefly (1-2 sentences)."
                
                # Діагностика: показуємо що промпт використовується
                print(f"💬 Промпт: {BASE_PERSONALITY[:50]}...")
                
                # Формуємо prompt користувача
                user_prompt = f"Користувач сказав: {command}\n\nВідповідай у своєму стилі."
                
                # Викликаємо LLM з timeout
                start_time = time.time()
                
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=80,  # Зменшено для швидших відповідей
                    temperature=0.8,
                    timeout=15  # Максимум 15 секунд
                )
                
                elapsed = time.time() - start_time
                print(f"⏱️  LLM відповіла за {elapsed:.1f}s")
                
                if response.choices and response.choices[0].message:
                    content = response.choices[0].message.content
                    if content:
                        return content
                        
        except Exception as e:
            print(f"❌ Помилка OpenAI: {e}")
            # Якщо OpenAI не спрацював - повертаємо базову відповідь
            if base_response:
                return base_response
        
        # КРОК 3: Fallback якщо все не спрацювало
        if base_response:
            return base_response
        
        # Остаточний fallback
        responses = {
            "uk": [
                "Вибачте, я не зрозумів вашу команду.",
                "Не впевнений, що ви маєте на увазі.",
                "Можете сформулювати по-іншому?"
            ],
            "de": [
                "Entschuldigung, ich habe Ihren Befehl nicht verstanden.",
                "Ich bin nicht sicher, was Sie meinen.",
                "Könnten Sie es anders formulieren?"
            ],
            "en": [
                "Sorry, I didn't understand your command.",
                "I'm not sure what you mean.",
                "Could you rephrase that?"
            ]
        }
        
        language_responses = responses.get(self.language, responses["en"])
        return random.choice(language_responses)
        
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
    daemon = VoiceDaemon(telegram_user_id=123456789)
    daemon.start()

