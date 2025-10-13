"""
Wake word detection через Porcupine (Picovoice)
Буде слухати фразу типу "Привіт Бот"
"""

# TODO: Встановити на Pi:
# pip install pvporcupine


class WakeWordDetector:
    def __init__(self, wake_word: str = "hey google"):
        """
        Ініціалізація детектора
        
        Porcupine має готові wake words:
        - "hey google"
        - "alexa" 
        - "ok google"
        
        Кастомні фрази треба тренувати на їх сайті
        """
        self.wake_word = wake_word
        # TODO: Ініціалізувати Porcupine
        
    def listen(self) -> bool:
        """
        Слухає wake word в реал-таймі
        Returns True коли почув
        """
        # TODO: Реалізувати на Pi
        return False
        
    def stop(self):
        """Зупиняє прослуховування"""
        pass


