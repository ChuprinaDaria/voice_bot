"""
Інтеграція з OpenWeatherMap для отримання погоди
"""

from typing import Optional, Tuple
import requests


class WeatherManager:
    """Керування погодою через OpenWeatherMap API"""

    def __init__(self, api_key: Optional[str] = None):
        # Завантажуємо ключ з config
        if not api_key:
            from config import get_settings
            settings = get_settings()
            api_key = settings.openweather_api_key
        
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"

    def get_weather(self, city: str, language: str = "uk") -> Tuple[bool, str]:
        """
        Отримує погоду для міста
        
        Args:
            city: Назва міста
            language: Мова відповіді (uk, en, de)
        
        Returns:
            (success, message)
        """
        # Перевірка API ключа
        if not self.api_key:
            if language == "uk":
                return False, "❌ API ключ OpenWeatherMap не налаштований. Додай OPENWEATHER_API_KEY в .env файл"
            elif language == "de":
                return False, "❌ OpenWeatherMap API-Schlüssel nicht konfiguriert. Fügen Sie OPENWEATHER_API_KEY zur .env-Datei hinzu"
            else:
                return False, "❌ OpenWeatherMap API key not configured. Add OPENWEATHER_API_KEY to .env file"
        
        try:
            # Переклад мови для API
            api_lang = language
            if language == "uk":
                api_lang = "ua"
            
            params = {
                "q": city,
                "appid": self.api_key,
                "units": "metric",  # Цельсій
                "lang": api_lang
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 404:
                if language == "uk":
                    return False, f"❌ Місто '{city}' не знайдено"
                elif language == "de":
                    return False, f"❌ Stadt '{city}' nicht gefunden"
                else:
                    return False, f"❌ City '{city}' not found"
            
            if response.status_code == 401:
                if language == "uk":
                    return False, "❌ Невірний API ключ OpenWeatherMap"
                elif language == "de":
                    return False, "❌ Ungültiger OpenWeatherMap API-Schlüssel"
                else:
                    return False, "❌ Invalid OpenWeatherMap API key"
            
            response.raise_for_status()
            data = response.json()
            
            # Парсимо дані
            temp = round(data['main']['temp'])
            feels_like = round(data['main']['feels_like'])
            humidity = data['main']['humidity']
            description = data['weather'][0]['description']
            wind_speed = round(data['wind']['speed'])
            
            # Форматуємо відповідь
            if language == "uk":
                message = (
                    f"🌤️ Погода в {city}:\n"
                    f"🌡️ Температура: {temp}°C (відчувається як {feels_like}°C)\n"
                    f"☁️ {description.capitalize()}\n"
                    f"💧 Вологість: {humidity}%\n"
                    f"💨 Вітер: {wind_speed} м/с"
                )
            elif language == "de":
                message = (
                    f"🌤️ Wetter in {city}:\n"
                    f"🌡️ Temperatur: {temp}°C (fühlt sich an wie {feels_like}°C)\n"
                    f"☁️ {description.capitalize()}\n"
                    f"💧 Luftfeuchtigkeit: {humidity}%\n"
                    f"💨 Wind: {wind_speed} m/s"
                )
            else:  # en
                message = (
                    f"🌤️ Weather in {city}:\n"
                    f"🌡️ Temperature: {temp}°C (feels like {feels_like}°C)\n"
                    f"☁️ {description.capitalize()}\n"
                    f"💧 Humidity: {humidity}%\n"
                    f"💨 Wind: {wind_speed} m/s"
                )
            
            return True, message
            
        except requests.exceptions.Timeout:
            if language == "uk":
                return False, "❌ Час очікування минув. Спробуй пізніше"
            elif language == "de":
                return False, "❌ Zeitüberschreitung. Versuche es später"
            else:
                return False, "❌ Request timeout. Try later"
        except requests.exceptions.RequestException as e:
            print(f"❌ Weather API error: {e}")
            if language == "uk":
                return False, "❌ Помилка отримання погоди"
            elif language == "de":
                return False, "❌ Fehler beim Abrufen des Wetters"
            else:
                return False, "❌ Error fetching weather"
        except (KeyError, ValueError) as e:
            print(f"❌ Weather parsing error: {e}")
            if language == "uk":
                return False, "❌ Помилка обробки даних погоди"
            elif language == "de":
                return False, "❌ Fehler bei der Verarbeitung von Wetterdaten"
            else:
                return False, "❌ Error parsing weather data"


# Глобальний екземпляр
weather_manager = WeatherManager()

