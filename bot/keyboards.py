from __future__ import annotations

from telegram import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🎙️ Почати розмову"), KeyboardButton(text="⚙️ Налаштування")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def setup_menu_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    """Меню початкового налаштування"""
    if language == "uk":
        keyboard = [
            ["🌐 Вибрати мову"],
            ["📶 Підключити WiFi"],
            ["🔑 API Ключі"],  # ← НОВА КНОПКА
            ["🎵 Підключити Spotify"],
            ["📅 Підключити Google Calendar"],
            ["🗣️ Налаштувати особистість"],
            ["✅ Завершити налаштування"],
        ]
    else:
        keyboard = [
            ["🌐 Choose Language"],
            ["📶 Connect WiFi"],
            ["🔑 API Keys"],  # ← НОВА КНОПКА
            ["🎵 Connect Spotify"],
            ["📅 Connect Google Calendar"],
            ["🗣️ Setup Personality"],
            ["✅ Finish Setup"],
        ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def api_keys_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    """Меню керування API ключами"""
    if language == "uk":
        keyboard = [["🔑 OpenAI API Key"], ["🔙 Назад до налаштувань"]]
    else:
        keyboard = [["🔑 OpenAI API Key"], ["🔙 Back to Settings"]]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)



def language_keyboard() -> ReplyKeyboardMarkup:
    """Клавіатура вибору мови"""
    keyboard = [
        ["Українська (uk)", "English (en)"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def voice_control_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    """Кнопки керування голосом"""
    if language == "uk":
        keyboard = [
            ["🎤 Увімкнути голос", "🔇 Вимкнути голос"],
            ["🔙 Назад до налаштувань"]
        ]
    else:
        keyboard = [
            ["🎤 Enable Voice", "🔇 Disable Voice"],
            ["🔙 Back to Settings"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
