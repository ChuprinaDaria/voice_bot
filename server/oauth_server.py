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
    """Запуск FastAPI сервера з SSL (Let's Encrypt сертифікати)."""
    ssl_cert = "/etc/letsencrypt/live/voicebot.laztsoft.pl/fullchain.pem"
    ssl_key = "/etc/letsencrypt/live/voicebot.laztsoft.pl/privkey.pem"

    if not (os.path.exists(ssl_cert) and os.path.exists(ssl_key)):
        print("❌ SSL сертифікати не знайдені! Очікується Let's Encrypt у /etc/letsencrypt/live/voicebot.laztsoft.pl/")
        return

    print("✅ Сервер запущено: https://voicebot.laztsoft.pl")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8443,
        ssl_keyfile=ssl_key,
        ssl_certfile=ssl_cert,
        log_level="info",
    )


