from __future__ import annotations

import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import random


class CommandType:
    GENERAL_INFO = "general_info"
    TIME = "time"
    DATE = "date"
    WEATHER = "weather"
    SPOTIFY = "spotify"
    CALENDAR = "calendar"
    UNKNOWN = "unknown"
    WEB_SEARCH = "web_search"


PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "uk": {
        CommandType.TIME: [
            r"котра година", r"скільки зараз часу", r"скільки годин",
            r"який час", r"котра зараз година",
        ],
        CommandType.DATE: [
            r"яка сьогодні дата", r"яке сьогодні число", r"який сьогодні день",
            r"яке число", r"яка зараз дата",
        ],
        CommandType.WEATHER: [
            r"яка погода", r"який прогноз погоди", r"що з погодою",
            r"яка температура", r"як погода",
        ],
        CommandType.SPOTIFY: [
            r"включи музику", r"(включи|грай) пісню (.+)", r"поставити музику",
            r"грай (.+)", r"зупини музику", r"пауза",
            r"спотіфай", r"spotify", r"хочу послухати", r"включи (.+)",
            r"поставити (.+)", r"пусти (.+)", r"запусти музику",
        ],
        CommandType.CALENDAR: [
            r"що в календарі", r"які зустрічі", r"що заплановано",
            r"додай (подію|зустріч) (.+)",
        ],
    },
    "en": {
        CommandType.TIME: [
            r"what time is it", r"current time", r"tell me the time",
            r"time now", r"what's the time",
        ],
        CommandType.DATE: [
            r"what date is it", r"current date", r"what day is it",
            r"today's date", r"what's the date",
        ],
        CommandType.WEATHER: [
            r"what's the weather", r"weather forecast", r"what's the temperature",
            r"how's the weather", r"is it (rain|sunny|cloudy)",
        ],
        CommandType.SPOTIFY: [
            r"play music", r"play (song|track|artist) (.+)", r"turn on music",
            r"play (.+)", r"stop music", r"pause",
        ],
        CommandType.CALENDAR: [
            r"what's in (my|the) calendar", r"any meetings", r"what's scheduled",
            r"add (event|meeting) (.+)",
        ],
    },
    "de": {
        CommandType.TIME: [
            r"wie spät ist es", r"wie viel uhr ist es", r"uhrzeit",
            r"aktuelle zeit", r"was ist die uhrzeit",
        ],
        CommandType.DATE: [
            r"welches datum ist heute", r"welcher tag ist heute", r"heutiges datum",
            r"aktuelles datum", r"was ist das datum",
        ],
        CommandType.WEATHER: [
            r"wie ist das wetter", r"wettervorhersage", r"wie ist die temperatur",
            r"wie wird das wetter", r"ist es (regnerisch|sonnig|bewölkt)",
        ],
        CommandType.SPOTIFY: [
            r"musik abspielen", r"spiele (lied|track|künstler) (.+)", r"musik an",
            r"spiele (.+)", r"musik stoppen", r"pause",
        ],
        CommandType.CALENDAR: [
            r"was steht im kalender", r"irgendwelche termine", r"was ist geplant",
            r"(termin|meeting) hinzufügen (.+)",
        ],
    },
}


def determine_command_type(text: str, language: str = "uk") -> tuple[str, Optional[Dict[str, Any]]]:
    lang_patterns = PATTERNS.get(language, PATTERNS["en"])
    text_lower = text.lower()
    for command_type, patterns in lang_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                params: Dict[str, Any] = {}
                if match.groups():
                    if len(match.groups()) >= 1:
                        params["action"] = match.group(1)
                    if len(match.groups()) >= 2:
                        params["value"] = match.group(2)
                return command_type, params
    if (
        "що таке" in text_lower
        or "розкажи про" in text_lower
        or "what is" in text_lower
        or "tell me about" in text_lower
        or "was ist" in text_lower
        or "erzähl mir über" in text_lower
    ):
        return CommandType.WEB_SEARCH, {"query": text}
    return CommandType.UNKNOWN, None


def process_command(text: str, language: str = "uk", telegram_user_id: Optional[int] = None) -> str:
    command_type, params = determine_command_type(text, language)
    if command_type == CommandType.TIME:
        return _get_time_response(language)
    if command_type == CommandType.DATE:
        return _get_date_response(language)
    if command_type == CommandType.WEATHER:
        return _get_weather_response(language)
    if command_type == CommandType.SPOTIFY:
        return _process_spotify_command(params, language, telegram_user_id)
    if command_type == CommandType.CALENDAR:
        return _process_calendar_command(params, language, telegram_user_id)
    if command_type == CommandType.WEB_SEARCH:
        return _process_web_search(text, language)
    if language == "uk":
        responses = [
            "Вибачте, я не зрозумів вашу команду.",
            "Не впевнений, що ви маєте на увазі.",
            "Можете, будь ласка, сформулювати по-іншому?",
            "Я не розпізнав цю команду.",
        ]
    elif language == "de":
        responses = [
            "Entschuldigung, ich habe Ihren Befehl nicht verstanden.",
            "Ich bin nicht sicher, was Sie meinen.",
            "Könnten Sie es bitte anders formulieren?",
            "Ich habe diesen Befehl nicht erkannt.",
        ]
    else:
        responses = [
            "Sorry, I didn't understand your command.",
            "I'm not sure what you mean.",
            "Could you please rephrase that?",
            "I didn't recognize this command.",
        ]
    return random.choice(responses)


def _get_time_response(language: str) -> str:
    now = datetime.now()
    if language == "uk":
        return f"Зараз {now.hour:02d}:{now.minute:02d}."
    if language == "de":
        return f"Es ist jetzt {now.hour:02d}:{now.minute:02d} Uhr."
    return f"It's {now.hour:02d}:{now.minute:02d} now."


def _get_date_response(language: str) -> str:
    now = datetime.now()
    if language == "uk":
        months = [
            "січня",
            "лютого",
            "березня",
            "квітня",
            "травня",
            "червня",
            "липня",
            "серпня",
            "вересня",
            "жовтня",
            "листопада",
            "грудня",
        ]
        weekdays = [
            "понеділок",
            "вівторок",
            "середа",
            "четвер",
            "п'ятниця",
            "субота",
            "неділя",
        ]
        return f"Сьогодні {weekdays[now.weekday()]}, {now.day} {months[now.month-1]} {now.year} року."
    if language == "de":
        months = [
            "Januar",
            "Februar",
            "März",
            "April",
            "Mai",
            "Juni",
            "Juli",
            "August",
            "September",
            "Oktober",
            "November",
            "Dezember",
        ]
        weekdays = [
            "Montag",
            "Dienstag",
            "Mittwoch",
            "Donnerstag",
            "Freitag",
            "Samstag",
            "Sonntag",
        ]
        return f"Heute ist {weekdays[now.weekday()]}, der {now.day}. {months[now.month-1]} {now.year}."
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    weekdays = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    return f"Today is {weekdays[now.weekday()]}, {months[now.month-1]} {now.day}, {now.year}."


def _get_weather_response(language: str) -> str:
    if language == "uk":
        return "На жаль, я поки не можу перевірити погоду. Ця функція в розробці."
    if language == "de":
        return "Leider kann ich das Wetter noch nicht überprüfen. Diese Funktion ist in Entwicklung."
    return "Sorry, I can't check the weather yet. This feature is under development."


def _process_spotify_command(params: Optional[Dict[str, Any]], language: str, user_id: Optional[int]) -> str:
    """Обробка Spotify команд (включення музики)"""
    if not user_id:
        if language == "uk":
            return "❌ Не вдалося визначити користувача."
        elif language == "de":
            return "❌ Benutzer konnte nicht ermittelt werden."
        else:
            return "❌ Could not identify user."
    
    try:
        from integrations.spotify import spotify_manager
        
        # Перевіряємо чи Spotify підключений
        if not spotify_manager.is_connected(user_id):
            if language == "uk":
                return "❌ Spotify не підключено. Налаштуй його через бота в Telegram."
            elif language == "de":
                return "❌ Spotify nicht verbunden. Konfigurieren Sie es über den Telegram-Bot."
            else:
                return "❌ Spotify not connected. Configure it via the Telegram bot."
        
        # Якщо є параметр з назвою пісні - шукаємо і включаємо
        track_name = None
        if params and "value" in params:
            track_name = params["value"]
        elif params and "action" in params:
            track_name = params["action"]
        
        if track_name:
            # Включаємо конкретний трек
            success, message = spotify_manager.play_track(user_id, track_name)
            return message
        else:
            # Просто включаємо останню музику (resume)
            if language == "uk":
                return "▶️ Включаю музику на Spotify..."
            elif language == "de":
                return "▶️ Spiele Musik auf Spotify..."
            else:
                return "▶️ Playing music on Spotify..."
                
    except Exception as e:
        print(f"❌ Помилка Spotify: {e}")
        if language == "uk":
            return f"❌ Помилка при роботі зі Spotify: {str(e)}"
        elif language == "de":
            return f"❌ Fehler bei Spotify: {str(e)}"
        else:
            return f"❌ Spotify error: {str(e)}"


def _process_calendar_command(params: Optional[Dict[str, Any]], language: str, user_id: Optional[int]) -> str:
    if language == "uk":
        return "На жаль, інтеграція з Google Calendar ще в розробці."
    if language == "de":
        return "Leider ist die Google Calendar-Integration noch in Entwicklung."
    return "Sorry, Google Calendar integration is still in development."


def _process_web_search(query: str, language: str) -> str:
    from core.web_search import web_search
    return web_search(query, language)


