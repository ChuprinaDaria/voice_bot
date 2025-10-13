# Voice Bot

Асистент для Raspberry Pi з Telegram-ботом, голосовим керуванням, інтеграціями (Spotify, Google Calendar) і локальним демоном.

## Швидкий старт

1. Створіть `.env` на основі `.env.example` і заповніть секрети
2. Встановіть залежності для розробки:
```bash
pip install -r requirements.txt
```
3. Запустіть Telegram-бота (OAuth-сервер підніметься автоматично):
```bash
python main.py
```

## Raspberry Pi

Для Pi використовуйте окремий список залежностей:
```bash
pip install -r requirements-pi.txt
```
Головний процес на Pi:
```bash
python voice_daemon.py
```

## Структура
- `voice_daemon.py` — демон на Pi (wake word → запис → STT → логіка → TTS)
- `bot/` — Telegram-бот
- `core/` — спільна логіка (wake word, TTS, інтеграції API)
- `voice/` — робота з аудіо/STT для OpenAI Whisper
- `storage/` — база даних (SQLAlchemy)

## Ліцензія
MIT
