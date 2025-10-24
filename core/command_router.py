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
    JOKE = "joke"
    FACT = "fact"
    TIMER = "timer"
    HISTORY = "history"


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
            r"яка температура", r"як погода", r"погода в (.+)", r"погода (.+)",
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
        CommandType.JOKE: [
            r"розкажи жарт", r"розсміши мене", r"жарт", r"анекдот",
            r"хочу жарт", r"хочу посміятись",
        ],
        CommandType.FACT: [
            r"цікавий факт", r"розкажи факт", r"цікаве", r"факт",
            r"розкажи щось цікаве",
        ],
        CommandType.TIMER: [
            r"встанов таймер на (\d+)", r"таймер на (\d+)", r"нагадай через (\d+)",
            r"нагадай мені через (\d+)", r"поставити таймер",
        ],
        CommandType.HISTORY: [
            r"історія", r"що я питав", r"покажи історію", r"мої команди",
            r"що я запитував", r"історія розмов",
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
            r"how's the weather", r"is it (rain|sunny|cloudy)", r"weather in (.+)",
        ],
        CommandType.SPOTIFY: [
            r"play music", r"play (song|track|artist) (.+)", r"turn on music",
            r"play (.+)", r"stop music", r"pause",
        ],
        CommandType.CALENDAR: [
            r"what's in (my|the) calendar", r"any meetings", r"what's scheduled",
            r"add (event|meeting) (.+)",
        ],
        CommandType.JOKE: [
            r"tell (me )?(a )?joke", r"make me laugh", r"joke", r"something funny",
            r"i want a joke", r"funny",
        ],
        CommandType.FACT: [
            r"interesting fact", r"tell (me )?(a )?fact", r"fact", r"something interesting",
            r"tell me something interesting",
        ],
        CommandType.TIMER: [
            r"set (a )?timer for (\d+)", r"timer for (\d+)", r"remind (me )?in (\d+)",
            r"set timer", r"timer",
        ],
        CommandType.HISTORY: [
            r"history", r"what did i ask", r"show history", r"my commands",
            r"conversation history", r"chat history",
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
            r"wie wird das wetter", r"ist es (regnerisch|sonnig|bewölkt)", r"wetter in (.+)",
        ],
        CommandType.SPOTIFY: [
            r"musik abspielen", r"spiele (lied|track|künstler) (.+)", r"musik an",
            r"spiele (.+)", r"musik stoppen", r"pause",
        ],
        CommandType.CALENDAR: [
            r"was steht im kalender", r"irgendwelche termine", r"was ist geplant",
            r"(termin|meeting) hinzufügen (.+)",
        ],
        CommandType.JOKE: [
            r"erzähl (mir )?(einen )?witz", r"bring mich zum lachen", r"witz",
            r"etwas lustiges", r"ich will einen witz",
        ],
        CommandType.FACT: [
            r"interessante tatsache", r"erzähl (mir )?(eine )?tatsache", r"tatsache",
            r"etwas interessantes", r"erzähl mir etwas interessantes",
        ],
        CommandType.TIMER: [
            r"stelle timer für (\d+)", r"timer für (\d+)", r"erinnere (mich )?in (\d+)",
            r"timer stellen", r"timer",
        ],
        CommandType.HISTORY: [
            r"geschichte", r"was habe ich gefragt", r"zeige geschichte", r"meine befehle",
            r"gesprächsverlauf", r"chat-verlauf",
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
    
    # Зберігаємо команду в історію
    if telegram_user_id:
        _save_to_history(telegram_user_id, text, language)
    
    if command_type == CommandType.TIME:
        response = _get_time_response(language)
    elif command_type == CommandType.DATE:
        response = _get_date_response(language)
    elif command_type == CommandType.WEATHER:
        response = _get_weather_response(params, language)
    elif command_type == CommandType.SPOTIFY:
        response = _process_spotify_command(params, language, telegram_user_id)
    elif command_type == CommandType.CALENDAR:
        response = _process_calendar_command(params, language, telegram_user_id)
    elif command_type == CommandType.WEB_SEARCH:
        response = _process_web_search(text, language)
    elif command_type == CommandType.JOKE:
        response = _get_joke(language)
    elif command_type == CommandType.FACT:
        response = _get_fact(language)
    elif command_type == CommandType.TIMER:
        response = _set_timer(params, language)
    elif command_type == CommandType.HISTORY:
        response = _get_history(telegram_user_id, language)
    else:
        response = _get_unknown_response(language)
    
    # Зберігаємо відповідь в історію
    if telegram_user_id:
        _update_history_response(telegram_user_id, response)
    
    return response


def _get_unknown_response(language: str) -> str:
    """Відповідь на невідому команду"""
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


def _save_to_history(user_id: int, command: str, language: str) -> None:
    """Зберігає команду в історію"""
    try:
        from storage.database import SessionLocal
        from storage.models import Conversation
        
        db = SessionLocal()
        try:
            conv = Conversation(
                user_id=user_id,
                command=command,
                response="",  # Поки що порожня, оновимо після обробки
                language=language
            )
            db.add(conv)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ Помилка збереження в історію: {e}")


def _update_history_response(user_id: int, response: str) -> None:
    """Оновлює останню відповідь в історії"""
    try:
        from storage.database import SessionLocal
        from storage.models import Conversation
        
        db = SessionLocal()
        try:
            # Знаходимо останній запис
            last_conv = db.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(Conversation.timestamp.desc()).first()
            
            if last_conv:
                last_conv.response = response
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ Помилка оновлення відповіді: {e}")


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


def _get_weather_response(params: Optional[Dict[str, Any]], language: str) -> str:
    """Отримує погоду"""
    try:
        from integrations.weather import weather_manager
        
        # Витягуємо місто з параметрів
        city = None
        if params and "value" in params:
            city = params["value"]
        
        # Якщо міста немає - просимо вказати
        if not city:
            if language == "uk":
                return "🌤️ Скажи для якого міста перевірити погоду. Наприклад: 'Яка погода в Києві?'"
            elif language == "de":
                return "🌤️ Sag mir, für welche Stadt das Wetter sein soll. Zum Beispiel: 'Wie ist das Wetter in Berlin?'"
            else:
                return "🌤️ Tell me which city to check the weather for. For example: 'What's the weather in London?'"
        
        success, message = weather_manager.get_weather(city, language)
        return message
        
    except Exception as e:
        print(f"❌ Помилка погоди: {e}")
        if language == "uk":
            return "❌ Помилка отримання погоди"
        elif language == "de":
            return "❌ Fehler beim Abrufen des Wetters"
        else:
            return "❌ Error fetching weather"


def _get_joke(language: str) -> str:
    """Розповідає жарт"""
    try:
        from integrations.fun import fun_manager
        success, joke = fun_manager.get_joke(language)
        return joke
    except Exception as e:
        print(f"❌ Помилка жартів: {e}")
        if language == "uk":
            return "❌ Не вдалося отримати жарт"
        elif language == "de":
            return "❌ Fehler beim Abrufen des Witzes"
        else:
            return "❌ Error fetching joke"


def _get_fact(language: str) -> str:
    """Розповідає цікавий факт"""
    try:
        from integrations.fun import fun_manager
        success, fact = fun_manager.get_fact(language)
        return fact
    except Exception as e:
        print(f"❌ Помилка фактів: {e}")
        if language == "uk":
            return "❌ Не вдалося отримати факт"
        elif language == "de":
            return "❌ Fehler beim Abrufen der Fakten"
        else:
            return "❌ Error fetching fact"


def _set_timer(params: Optional[Dict[str, Any]], language: str) -> str:
    """Встановлює таймер (тільки повідомлення, логіка в Telegram боті)"""
    # Витягуємо час
    minutes = None
    if params and "value" in params:
        try:
            minutes = int(params["value"])
        except:
            pass
    
    if not minutes:
        if language == "uk":
            return "⏰ Скажи на скільки хвилин встановити таймер. Наприклад: 'встанов таймер на 5 хвилин'"
        elif language == "de":
            return "⏰ Sag mir, für wie viele Minuten der Timer eingestellt werden soll. Zum Beispiel: 'Stelle Timer für 5 Minuten'"
        else:
            return "⏰ Tell me how many minutes for the timer. For example: 'set timer for 5 minutes'"
    
    if language == "uk":
        return f"✅ Таймер на {minutes} хв буде встановлено через Telegram бота"
    elif language == "de":
        return f"✅ Timer für {minutes} Min wird über Telegram-Bot eingestellt"
    else:
        return f"✅ Timer for {minutes} min will be set via Telegram bot"


def _get_history(user_id: Optional[int], language: str) -> str:
    """Показує історію розмов"""
    if not user_id:
        if language == "uk":
            return "❌ Історія доступна тільки через Telegram бота"
        elif language == "de":
            return "❌ Verlauf nur über Telegram-Bot verfügbar"
        else:
            return "❌ History available only via Telegram bot"
    
    try:
        from storage.database import SessionLocal
        from storage.models import Conversation
        
        db = SessionLocal()
        try:
            # Останні 5 розмов
            conversations = db.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(Conversation.timestamp.desc()).limit(5).all()
            
            if not conversations:
                if language == "uk":
                    return "📜 Історія порожня"
                elif language == "de":
                    return "📜 Verlauf ist leer"
                else:
                    return "📜 History is empty"
            
            if language == "uk":
                history_text = "📜 Останні команди:\n\n"
            elif language == "de":
                history_text = "📜 Letzte Befehle:\n\n"
            else:
                history_text = "📜 Recent commands:\n\n"
            
            for i, conv in enumerate(reversed(conversations), 1):
                time_str = conv.timestamp.strftime("%H:%M")
                history_text += f"{i}. [{time_str}] {conv.command[:50]}\n"
            
            return history_text
            
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Помилка історії: {e}")
        if language == "uk":
            return "❌ Помилка отримання історії"
        elif language == "de":
            return "❌ Fehler beim Abrufen des Verlaufs"
        else:
            return "❌ Error fetching history"


def _process_spotify_command(params: Optional[Dict[str, Any]], language: str, user_id: Optional[int]) -> str:
    """Обробка музичних команд через Mopidy (Spotify/YouTube/локальні файли)"""
    try:
        from integrations.mopidy import mopidy_manager
        
        # Перевіряємо чи запущений Mopidy
        if not mopidy_manager.is_running():
            if language == "uk":
                return "❌ Музичний сервер не запущений. Запусти: sudo systemctl start mopidy"
            elif language == "de":
                return "❌ Musikserver läuft nicht. Starten: sudo systemctl start mopidy"
            else:
                return "❌ Music server not running. Start: sudo systemctl start mopidy"
        
        # Якщо є параметр з назвою пісні - шукаємо і включаємо
        track_name = None
        if params and "value" in params:
            track_name = params["value"]
        elif params and "action" in params:
            track_name = params["action"]
        
        if track_name:
            # Включаємо конкретний трек (шукає на Spotify, YouTube, локально)
            success, message = mopidy_manager.play_track(track_name, source="any")
            return message
        else:
            # Просто відновлюємо відтворення
            success, message = mopidy_manager.resume()
            return message
                
    except Exception as e:
        print(f"❌ Помилка Mopidy: {e}")
        if language == "uk":
            return f"❌ Помилка музичного сервера: {str(e)}"
        elif language == "de":
            return f"❌ Musikserver-Fehler: {str(e)}"
        else:
            return f"❌ Music server error: {str(e)}"


def _process_calendar_command(params: Optional[Dict[str, Any]], language: str, user_id: Optional[int]) -> str:
    if language == "uk":
        return "На жаль, інтеграція з Google Calendar ще в розробці."
    if language == "de":
        return "Leider ist die Google Calendar-Integration noch in Entwicklung."
    return "Sorry, Google Calendar integration is still in development."


def _process_web_search(query: str, language: str) -> str:
    from core.web_search import web_search
    return web_search(query, language)


