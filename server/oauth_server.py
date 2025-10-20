from __future__ import annotations

import os
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from config import get_settings


app = FastAPI(title="VoiceBot OAuth Server")
settings = get_settings()


@app.get("/")
async def root() -> dict[str, object]:
    """Головна сторінка OAuth сервера"""
    return {
        "service": "VoiceBot OAuth Server",
        "domain": settings.domain,
        "endpoints": {
            "spotify": f"https://{settings.domain}/spotify/callback",
            "google": f"https://{settings.domain}/google/callback",
        },
    }


@app.get("/spotify/callback")
async def spotify_callback(request: Request) -> dict[str, object]:
    """Обробка повернення від Spotify OAuth.
    Приймаємо ?code=...&state=... і повертаємо коротку відповідь.
    """
    params = dict(request.query_params)
    code: Optional[str] = params.get("code")
    state: Optional[str] = params.get("state")
    error: Optional[str] = params.get("error")

    if error:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "provider": "spotify",
            "error": error,
            "message": "Користувач відхилив авторизацію або сталась помилка",
        })

    if not code or not state:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "provider": "spotify",
            "message": "Відсутній код або state",
        })

    # TODO: Обміняти code на токени
    # telegram_user_id = int(state)
    # spotify_manager.exchange_code_for_tokens(telegram_user_id, code)

    return {
        "status": "success",
        "provider": "spotify",
        "message": "✅ Spotify підключено! Поверніться в Telegram бота.",
        "received_code": bool(code),
        "state": state,
    }


@app.get("/google/callback")
async def google_callback(request: Request) -> dict[str, object]:
    """Обробка повернення від Google OAuth.
    Приймаємо ?code=...&state=... і повертаємо коротку відповідь.
    """
    params = dict(request.query_params)
    code: Optional[str] = params.get("code")
    state: Optional[str] = params.get("state")
    error: Optional[str] = params.get("error")

    if error:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "provider": "google",
            "error": error,
            "message": "Користувач відхилив авторизацію або сталась помилка",
        })

    if not code or not state:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "provider": "google",
            "message": "Відсутній код або state",
        })

    # TODO: Обміняти code на токени
    # telegram_user_id = int(state)
    # google_calendar_manager.exchange_code_for_tokens(telegram_user_id, code)

    return {
        "status": "success",
        "provider": "google",
        "message": "✅ Google Calendar підключено! Поверніться в Telegram бота.",
        "received_code": bool(code),
        "state": state,
    }


def run_server() -> None:
    """Запуск FastAPI сервера з SSL або HTTP fallback"""
    force_http = os.getenv("OAUTH_SERVER_HTTP", "0") == "1"

    def run_http() -> None:
        print(f"🌐 OAuth сервер (HTTP) → http://0.0.0.0:8000")
        print(f"   Використовуйте для локальної розробки")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            proxy_headers=True,
            forwarded_allow_ips="*",
        )

    if force_http:
        run_http()
        return

    # Шлях до SSL сертифікатів Let's Encrypt
    ssl_cert = f"/etc/letsencrypt/live/{settings.domain}/fullchain.pem"
    ssl_key = f"/etc/letsencrypt/live/{settings.domain}/privkey.pem"

    if not (os.path.exists(ssl_cert) and os.path.exists(ssl_key)):
        print(f"❌ SSL сертифікати не знайдені для {settings.domain}!")
        print(f"   Очікується: {ssl_cert}")
        print(f"   Згенеруйте через: sudo certbot certonly --standalone -d {settings.domain}")
        print("➡️  Фолбек на HTTP (порт 8000)")
        run_http()
        return

    try:
        print(f"✅ OAuth сервер (HTTPS) → https://{settings.domain}")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8443,
            ssl_keyfile=ssl_key,
            ssl_certfile=ssl_cert,
            log_level="info",
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
    except PermissionError:
        print("❌ Немає прав читання SSL ключів.")
        print("   Рішення: sudo chmod 644 /etc/letsencrypt/live/*/privkey.pem")
        print("   Або додати користувача до групи ssl-cert")
        print("➡️  Фолбек на HTTP (порт 8000)")
        run_http()
    except Exception as exc:
        print(f"❌ Помилка запуску HTTPS: {exc}")
        print("➡️  Фолбек на HTTP (порт 8000)")
        run_http()


