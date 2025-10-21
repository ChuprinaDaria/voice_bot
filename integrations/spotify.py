from __future__ import annotations

from typing import Optional, Tuple

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from config import get_settings
from storage.database import SessionLocal
from storage.models import User, UserSecrets
from storage.secrets_manager import encrypt_token, decrypt_token


class SpotifyManager:
    """Керування Spotify інтеграцією"""

    def __init__(self) -> None:
        settings = get_settings()
        self.client_id: Optional[str] = settings.spotify_client_id
        self.client_secret: Optional[str] = settings.spotify_client_secret
        # Очікуємо, що змінна середовища задана (наприклад, https://your.domain/spotify/callback)
        self.redirect_uri: Optional[str] = settings.spotify_redirect_uri
        self.scope: str = (
            "user-read-playback-state user-modify-playback-state user-read-currently-playing"
        )

    def get_auth_url(self, telegram_user_id: int) -> str:
        """Генерує URL для авторизації Spotify"""
        # Спрощений варіант: використовуємо localhost redirect
        sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri="http://localhost:8888/callback",  # Локальний redirect
            scope=self.scope,
            state=str(telegram_user_id),
            show_dialog=True
        )
        return sp_oauth.get_authorize_url()
    
    def set_token_manually(self, telegram_user_id: int, token: str) -> Tuple[bool, str]:
        """
        Зберігає токен вручну (для простого налаштування без OAuth сервера)
        
        Отримати токен: https://developer.spotify.com/console/post-play/
        Тицьни "Get Token" → скопіюй access token
        """
        try:
            # Перевіряємо чи токен працює - простий пошук
            sp = spotipy.Spotify(auth=token)
            # Тест запит: пошук будь-чого
            sp.search(q="test", limit=1, type="track")
            
            # Зберігаємо токен (як access і refresh, хоча це тимчасовий токен)
            success = self.save_tokens(telegram_user_id, token, token)
            
            if success:
                return True, "✅ Spotify токен збережено! (дійсний ~1 година)"
            else:
                return False, "❌ Не вдалося зберегти токен"
                
        except Exception as e:
            return False, f"❌ Невірний токен: {str(e)}"

    def save_tokens(self, telegram_user_id: int, access_token: str, refresh_token: str) -> bool:
        """Зберігає зашифровані токени користувача"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
            if not user:
                return False

            encrypted_access = encrypt_token(access_token)
            encrypted_refresh = encrypt_token(refresh_token)

            secrets = db.query(UserSecrets).filter(UserSecrets.user_id == user.id).first()
            if secrets:
                secrets.spotify_access_token = encrypted_access
                secrets.spotify_refresh_token = encrypted_refresh
            else:
                secrets = UserSecrets(
                    user_id=user.id,
                    spotify_access_token=encrypted_access,
                    spotify_refresh_token=encrypted_refresh,
                )
                db.add(secrets)

            db.commit()
            return True
        finally:
            db.close()

    def get_client(self, telegram_user_id: int) -> Optional[spotipy.Spotify]:
        """Створює авторизований клієнт Spotipy для користувача"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
            if not user:
                return None

            secrets = db.query(UserSecrets).filter(UserSecrets.user_id == user.id).first()
            if not secrets or not secrets.spotify_access_token or not secrets.spotify_refresh_token:
                return None

            access_token = decrypt_token(secrets.spotify_access_token) or ""
            refresh_token = decrypt_token(secrets.spotify_refresh_token) or ""
        finally:
            db.close()

        sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
        )

        # Spotipy сам оновить токен при потребі через auth_manager, але тут
        # ми повертаємо клієнта з поточним access_token для простих викликів
        return spotipy.Spotify(auth_manager=sp_oauth, auth=access_token)

    def play_track(self, telegram_user_id: int, track_name: str) -> Tuple[bool, str]:
        """Відтворює трек за назвою"""
        sp = self.get_client(telegram_user_id)
        if not sp:
            return False, "❌ Spotify не підключено"

        try:
            results = sp.search(q=track_name, limit=1, type="track")
            # Уникаємо ланцюжка .get() на потенційно None об'єктах для статичної типізації
            results_dict = results or {}
            tracks = results_dict.get("tracks") or {}
            items = tracks.get("items") or []
            if not items:
                return False, f"❌ Трек '{track_name}' не знайдено"

            track = items[0]
            track_uri = track["uri"]
            sp.start_playback(uris=[track_uri])
            name = track.get("name", track_name)
            artist = (track.get("artists") or [{}])[0].get("name", "Unknown")
            return True, f"▶️ Грає: {name} - {artist}"
        except Exception as e:  # noqa: BLE001
            return False, f"❌ Помилка: {str(e)}"

    def is_connected(self, telegram_user_id: int) -> bool:
        """Чи збережені токени Spotify для користувача"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
            if not user:
                return False
            secrets = db.query(UserSecrets).filter(UserSecrets.user_id == user.id).first()
            return bool(secrets and secrets.spotify_access_token)
        finally:
            db.close()


spotify_manager = SpotifyManager()


