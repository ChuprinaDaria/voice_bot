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

    # Обробка меню налаштувань і OpenAI API ключа та інших кнопок
    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"^(⚙️ Налаштування|⚙️ Settings|🔑 API Ключі|🔑 API Keys|🔑 OpenAI API Key|🔙 Назад до налаштувань|🔙 Back to Settings|🌐 Вибрати мову|🌐 Choose Language|Українська \(uk\)|English \(en\)|📶 Підключити WiFi|📶 Connect WiFi|🎵 Spotify|🎵 Підключити Spotify|🎵 Connect Spotify|📅 Календар|📅 Підключити Google Calendar|📅 Connect Google Calendar|🗣️ Налаштувати особистість|🗣️ Setup Personality|✅ Завершити налаштування|✅ Finish Setup|переглянути|view|скинути|reset|🎤 Голосовий режим|🎤 Voice Control)$"
            ),
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

    # Загальне текстове повідомлення (для WiFi та інших простих станів)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            settings_handler,
        )
    )

    # Обробники керування голосом
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^(🎤 Увімкнути голос|🔇 Вимкнути голос|🎤 Enable Voice|🔇 Disable Voice)$"),
            voice_control_handler,
        )
    )

    # Запуск OAuth сервера в окремому потоці
    oauth_thread = threading.Thread(target=run_server, daemon=True)
    oauth_thread.start()
    # Примітка: logger не налаштований — залишаємо print/стандартні логи fastapi/uvicorn
    print("🌐 OAuth server thread started (https://voicebot.lazysoft.pl)")

    app.run_polling()


if __name__ == "__main__":
    main()


