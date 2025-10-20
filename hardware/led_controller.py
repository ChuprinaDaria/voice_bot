"""
Контроль RGB LED кільця WS2812B (12 діодів)
Анімації синхронізовані з голосом TTS
"""

from typing import List, Tuple
import time
import threading

try:
    from rpi_ws281x import PixelStrip, Color
    LEDS_AVAILABLE = True
except ImportError:
    LEDS_AVAILABLE = False
    print("⚠️  rpi_ws281x не встановлено. LED контроль недоступний.")

from config import get_settings


class LEDController:
    """Контроль WS2812B RGB LED кільця"""
    
    def __init__(self):
        settings = get_settings()
        self.led_count = settings.led_count
        self.gpio_pin = settings.led_gpio_pin
        
        if LEDS_AVAILABLE:
            # Налаштування WS2812B
            self.strip = PixelStrip(
                num=self.led_count,
                pin=self.gpio_pin,
                freq_hz=800000,  # 800kHz
                dma=10,
                invert=False,
                brightness=128,  # 0-255
                channel=0
            )
            self.strip.begin()
        else:
            self.strip = None
            
        self.is_active = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        
    def _run_in_thread(self, target, *args, **kwargs) -> None:
        self.stop_animation()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self.is_active = True
        self._thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        self._thread.start()
        
    def turn_off(self):
        """Вимикає всі LED"""
        if not self.strip:
            return
        
        for i in range(self.led_count):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
        self.is_active = False
        
    def set_color(self, r: int, g: int, b: int):
        """Встановлює один колір для всіх LED"""
        if not self.strip:
            return
        
        color = Color(g, r, b)  # WS2812B uses GRB order
        for i in range(self.led_count):
            self.strip.setPixelColor(i, color)
        self.strip.show()
        
    # --- ПУБЛІЧНІ API для неблокуючих анімацій ---
    def start_listening(self) -> None:
        self._run_in_thread(self._listening_animation)

    def start_speaking(self, audio_duration: float = 0) -> None:
        self._run_in_thread(self._speaking_animation, audio_duration)

    def start_thinking(self) -> None:
        self._run_in_thread(self._thinking_animation)

    def blink_error(self) -> None:
        self._run_in_thread(self._error_animation)

    def blink_success(self) -> None:
        self._run_in_thread(self._success_animation)

    def start_rainbow(self, iterations: int = 1) -> None:
        self._run_in_thread(self._rainbow_cycle, iterations)
        
    # --- Реалізація анімацій ---
    def _listening_animation(self):
        """Синя пульсація - режим прослуховування"""
        if not self.strip:
            return
        
        self.is_active = True
        
        # Синя пульсація
        while self.is_active:
            for brightness in range(0, 255, 15):
                if not self.is_active:
                    break
                self.set_color(0, 0, brightness)
                time.sleep(0.05)
            for brightness in range(255, 0, -15):
                if not self.is_active:
                    break
                self.set_color(0, 0, brightness)
                time.sleep(0.05)
            
    def _speaking_animation(self, audio_duration: float = 0):
        """Зелена хвиля - режим відповіді"""
        if not self.strip:
            return
        
        self.is_active = True
        start_time = time.time()
        
        while self.is_active:
            if audio_duration > 0 and (time.time() - start_time) > audio_duration:
                break
                
            # Хвиля по колу
            for i in range(self.led_count):
                if not self.is_active:
                    break
                
                # Обчислюємо яскравість для кожного LED
                position = (i / self.led_count) * 255
                brightness = int(abs(127 * (1 + time.time() * 3) % 255 - position))
                
                self.strip.setPixelColor(i, Color(brightness, brightness // 2, 0))
                
            self.strip.show()
            time.sleep(0.05)
        self.turn_off()
            
    def _thinking_animation(self):
        """Жовта обертова анімація - обробка команди"""
        if not self.strip:
            return
        
        self.is_active = True
        
        position = 0
        while self.is_active:
            for i in range(self.led_count):
                if i == position % self.led_count:
                    self.strip.setPixelColor(i, Color(255, 100, 0))  # Жовтий
                else:
                    self.strip.setPixelColor(i, Color(0, 0, 0))
                    
            self.strip.show()
            position += 1
            time.sleep(0.1)
        self.turn_off()
            
    def _error_animation(self):
        """Червоне блимання - помилка"""
        if not self.strip:
            return
        
        for _ in range(3):
            if not self.is_active:
                break
            self.set_color(255, 0, 0)  # Червоний
            time.sleep(0.2)
            self.turn_off()
            time.sleep(0.2)
        self.turn_off()
            
    def _success_animation(self):
        """Зелене блимання - успіх"""
        if not self.strip:
            return
        
        for _ in range(2):
            if not self.is_active:
                break
            self.set_color(0, 255, 0)  # Зелений
            time.sleep(0.15)
            self.turn_off()
            time.sleep(0.15)
        self.turn_off()
            
    def _rainbow_cycle(self, iterations: int = 1):
        """Райдужна анімація по колу"""
        if not self.strip:
            return
        
        for j in range(256 * iterations):
            if not self.is_active:
                break
            for i in range(self.led_count):
                color = self._wheel((int(i * 256 / self.led_count) + j) & 255)
                self.strip.setPixelColor(i, color)
            self.strip.show()
            time.sleep(0.02)
        self.turn_off()
            
    def _wheel(self, pos: int) -> int:
        """Генерує колір веселки (0-255)"""
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)
            
    def stop_animation(self):
        """Зупиняє поточну анімацію"""
        self.is_active = False
        
        
# Глобальний об'єкт
led_controller = LEDController()


