from __future__ import annotations

from telegram import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    """Головне меню"""
    if language == "uk":
        buttons = [
            [KeyboardButton(text="⚙️ Налаштування")],
            [KeyboardButton(text="🎵 Керування музикою"), KeyboardButton(text="⏰ Таймер")],
            [KeyboardButton(text="📜 Історія"), KeyboardButton(text="🎲 Розважити мене")],
            [KeyboardButton(text="🎤 Увімкнути голос"), KeyboardButton(text="🔇 Вимкнути голос")],
        ]
    elif language == "de":
        buttons = [
            [KeyboardButton(text="⚙️ Einstellungen")],
            [KeyboardButton(text="🎵 Musiksteuerung"), KeyboardButton(text="⏰ Timer")],
            [KeyboardButton(text="📜 Verlauf"), KeyboardButton(text="🎲 Unterhaltung")],
            [KeyboardButton(text="🎤 Stimme aktivieren"), KeyboardButton(text="🔇 Stimme deaktivieren")],
        ]
    else:  # en
        buttons = [
            [KeyboardButton(text="⚙️ Settings")],
            [KeyboardButton(text="🎵 Music Control"), KeyboardButton(text="⏰ Timer")],
            [KeyboardButton(text="📜 History"), KeyboardButton(text="🎲 Entertain me")],
            [KeyboardButton(text="🎤 Enable Voice"), KeyboardButton(text="🔇 Disable Voice")],
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def setup_menu_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    """Меню налаштувань"""
    if language == "uk":
        keyboard = [
            ["🌐 Вибрати мову"],
            ["🔑 API Ключі"],
            ["🗣️ Налаштувати особистість"],
            ["🎤 Голосовий режим"],
            ["✅ Завершити налаштування"],
        ]
    elif language == "de":
        keyboard = [
            ["🌐 Sprache wählen"],
            ["🔑 API-Schlüsselverwaltung"],
            ["🗣️ Persönlichkeit einrichten"],
            ["🎤 Sprachsteuerung"],
            ["✅ Einrichtung abschließen"],
        ]
    else:  # en
        keyboard = [
            ["🌐 Choose Language"],
            ["🔑 API Keys"],
            ["🗣️ Setup Personality"],
            ["🎤 Voice Control"],
            ["✅ Finish Setup"],
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def api_keys_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    """Меню керування API ключами та інтеграціями"""
    if language == "uk":
        keyboard = [
            ["🔑 OpenAI API Key"],
            ["🎵 Музика", "📅 Google Calendar"],
            ["🔙 Назад до налаштувань"]
        ]
    elif language == "de":
        keyboard = [
            ["🔑 OpenAI API Key"],
            ["🎵 Music", "📅 Google Calendar"],
            ["🔙 Zurück zu Einstellungen"]
        ]
    else:  # en
        keyboard = [
            ["🔑 OpenAI API Key"],
            ["🎵 Music", "📅 Google Calendar"],
            ["🔙 Back to Settings"]
        ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def language_keyboard() -> ReplyKeyboardMarkup:
    """Клавіатура вибору мови"""
    keyboard = [
        ["Українська (uk)", "English (en)"],
        ["Deutsch (de)"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def voice_control_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    """Кнопки керування голосом"""
    if language == "uk":
        keyboard = [
            ["🎤 Увімкнути голос", "🔇 Заглушити мікрофон"],
            ["▶️ Відновити прослуховування"],
            ["🔙 Назад до налаштувань"]
        ]
    elif language == "de":
        keyboard = [
            ["🎤 Stimme aktivieren", "🔇 Mikrofon stumm"],
            ["▶️ Zuhören fortsetzen"],
            ["🔙 Zurück zu Einstellungen"]
        ]
    else:  # en
        keyboard = [
            ["🎤 Enable Voice", "🔇 Mute Microphone"],
            ["▶️ Resume Listening"],
            ["🔙 Back to Settings"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def music_control_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    """Кнопки керування музикою"""
    if language == "uk":
        keyboard = [
            ["⏸️ Пауза", "▶️ Продовжити"],
            ["⏭️ Наступна", "⏮️ Попередня"],
            ["⏹️ Зупинити музику"],
            ["🔙 Назад"]
        ]
    elif language == "de":
        keyboard = [
            ["⏸️ Pause", "▶️ Fortsetzen"],
            ["⏭️ Nächste", "⏮️ Vorherige"],
            ["⏹️ Musik stoppen"],
            ["🔙 Zurück"]
        ]
    else:  # en
        keyboard = [
            ["⏸️ Pause", "▶️ Resume"],
            ["⏭️ Next", "⏮️ Previous"],
            ["⏹️ Stop Music"],
            ["🔙 Back"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
