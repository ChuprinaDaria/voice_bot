from __future__ import annotations

import os
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request


app = FastAPI(title="VoiceBot OAuth Server")


@app.get("/spotify/callback")
async def spotify_callback(request: Request):
    """Обробка повернення від Spotify OAuth.
    Приймаємо ?code=...&state=... і повертаємо коротку відповідь.
    """
    params = dict(request.query_params)
    code: Optional[str] = params.get("code")
    state: Optional[str] = params.get("state")
    # TODO: обміняти code на токени, зберегти для користувача з state (telegram_user_id)
    return {"status": "ok", "provider": "spotify", "received_code": bool(code), "state": state}


@app.get("/google/callback")
async def google_callback(request: Request):
    """Обробка повернення від Google OAuth.
    Приймаємо ?code=...&state=... і повертаємо коротку відповідь.
    """
    params = dict(request.query_params)
    code: Optional[str] = params.get("code")
    state: Optional[str] = params.get("state")
    # TODO: обміняти code на токени, зберегти для користувача з state (telegram_user_id)
    return {"status": "ok", "provider": "google", "received_code": bool(code), "state": state}


def run_server() -> None:
    """Запуск FastAPI сервера.

    Поведінка:
    - Якщо OAUTH_SERVER_HTTP=1 → запуск без SSL на порті 8000.
    - Інакше намагаємось SSL на 8443; при помилці доступу/конфігурації автоматично фолбек на HTTP:8000.
    """
    force_http = os.getenv("OAUTH_SERVER_HTTP", "0") == "1"

    def run_http() -> None:
        print("🌐 OAuth сервер (HTTP) → http://0.0.0.0:8000")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
        )

    if force_http:
        run_http()
        return

    ssl_cert = "/etc/letsencrypt/live/voicebot.laztsoft.pl/fullchain.pem"
    ssl_key = "/etc/letsencrypt/live/voicebot.laztsoft.pl/privkey.pem"

    if not (os.path.exists(ssl_cert) and os.path.exists(ssl_key)):
        print("❌ SSL сертифікати не знайдені! Очікується Let's Encrypt у /etc/letsencrypt/live/voicebot.laztsoft.pl/")
        print("➡️  Фолбек на HTTP без SSL (порт 8000)")
        run_http()
        return

    try:
        print("✅ Сервер (HTTPS) → https://voicebot.laztsoft.pl")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8443,
            ssl_keyfile=ssl_key,
            ssl_certfile=ssl_cert,
            log_level="info",
        )
    except PermissionError:
        print("❌ Немає прав читання SSL ключів. Додаємо фолбек на HTTP (порт 8000).")
        print("ℹ️  Рішення: додати користувача до групи ssl-cert або проксувати через Nginx.")
        run_http()
    except Exception as exc:
        print(f"❌ Помилка запуску HTTPS: {exc}. Фолбек на HTTP (порт 8000).")
        run_http()


