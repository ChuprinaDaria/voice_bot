from __future__ import annotations

import re
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import threading
from server.oauth_server import run_server

from bot.handlers import (
    start_command,
    activate_code,
    settings_handler,
    voice_control_handler,
    openai_key_handler,
    spotify_code_handler,
    google_code_handler,
    personality_handler,
)
from config import get_settings
from storage.database import init_db


def main() -> None:
    settings = get_settings()
    init_db()

    app = Application.builder().token(settings.telegram_bot_token or "").build()

    # Команди
    app.add_handler(CommandHandler("start", start_command))

    # Текстові повідомлення з кодом активації (патерн VBOT-...)
    app.add_handler(
        MessageHandler(
            filters.Regex(re.compile(r"VBOT-[A-F0-9\-]{4,}", re.IGNORECASE)),
            activate_code,
        )
    )

    # Обробка кнопок вибору мови - найвищий пріоритет
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^(Українська \(uk\)|English \(en\)|Deutsch \(de\))$"),
            settings_handler,
        )
    )

    # Обробка кнопок керування голосом - високий пріоритет
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^(🎤 Увімкнути голос|🔇 Вимкнути голос|🎤 Enable Voice|🔇 Disable Voice|🎤 Stimme aktivieren|🔇 Stimme deaktivieren)$"),
            voice_control_handler,
        )
    )

    # Обробка кнопок меню налаштувань - кожна окрема кнопка для уникнення помилок
    # Використовуємо список всіх можливих варіантів
    settings_buttons = [
        r"^⚙️ Налаштування$", r"^⚙️ Settings$", r"^⚙️ Einstellungen$",
        r"^🔑 API Ключі$", r"^🔑 API Keys$", r"^🔑 API-Schlüsselverwaltung$",
        r"^🔑 OpenAI API Key$",
        r"^🔙 Назад до налаштувань$", r"^🔙 Back to Settings$", r"^🔙 Zurück zu Einstellungen$",
        r"^🌐 Вибрати мову$", r"^🌐 Choose Language$", r"^🌐 Sprache wählen$",
        r"^🗣️ Налаштувати особистість$", r"^🗣️ Setup Personality$", r"^🗣️ Persönlichkeit einrichten$",
        r"^🎤 Голосовий режим$", r"^🎤 Voice Control$", r"^🎤 Sprachsteuerung$",
        r"^✅ Завершити налаштування$", r"^✅ Finish Setup$", r"^✅ Einrichtung abschließen$",
    ]
    # Об'єднуємо в один regex з "|" (або)
    settings_regex = "|".join(settings_buttons)
    app.add_handler(
        MessageHandler(
            filters.Regex(settings_regex),
            settings_handler,
        )
    )

    # Обробник введення OpenAI ключа (має йти до контекстних обробників)
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^sk-") & ~filters.COMMAND,
            openai_key_handler,
        )
    )

    # Обробник команд перегляду/скидання особистості
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^(переглянути|view|скинути|reset)$"),
            personality_handler,
        )
    )

    # Контекстні обробники за станами (після кнопок і OpenAI key)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r".+"),
            spotify_code_handler,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r".+"),
            google_code_handler,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r".+"),
            personality_handler,
        )
    )

    # Загальне текстове повідомлення (для інших простих станів)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            settings_handler,
        )
    )

    # Запуск без OAuth сервера - він нам поки не потрібен
    print("🤖 VoiceBot запущено!")

    app.run_polling()


if __name__ == "__main__":
    main()


