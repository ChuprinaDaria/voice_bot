from __future__ import annotations

from telegram import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    """Головне меню"""
    if language == "uk":
        buttons = [
            [KeyboardButton(text="🎙️ Почати розмову"), KeyboardButton(text="⚙️ Налаштування")],
        ]
    elif language == "de":
        buttons = [
            [KeyboardButton(text="🎙️ Gespräch starten"), KeyboardButton(text="⚙️ Einstellungen")],
        ]
    else:  # en
        buttons = [
            [KeyboardButton(text="🎙️ Start conversation"), KeyboardButton(text="⚙️ Settings")],
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
    """Меню керування API ключами"""
    if language == "uk":
        keyboard = [["🔑 OpenAI API Key"], ["🔙 Назад до налаштувань"]]
    elif language == "de":
        keyboard = [["🔑 OpenAI API Key"], ["🔙 Zurück zu Einstellungen"]]
    else:  # en
        keyboard = [["🔑 OpenAI API Key"], ["🔙 Back to Settings"]]

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
            ["🎤 Увімкнути голос", "🔇 Вимкнути голос"],
            ["🔙 Назад до налаштувань"]
        ]
    elif language == "de":
        keyboard = [
            ["🎤 Stimme aktivieren", "🔇 Stimme deaktivieren"],
            ["🔙 Zurück zu Einstellungen"]
        ]
    else:  # en
        keyboard = [
            ["🎤 Enable Voice", "🔇 Disable Voice"],
            ["🔙 Back to Settings"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
