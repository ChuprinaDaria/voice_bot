"""
Інтеграція з Mopidy музичним сервером
Mopidy керує Spotify, YouTube Music, локальними файлами через HTTP API
"""

from __future__ import annotations

from typing import Optional, Tuple, List, Dict, Any
import requests
import json


class MopidyManager:
    """Керування Mopidy музичним сервером через HTTP API"""

    def __init__(self, host: str = "127.0.0.1", port: int = 6680) -> None:
        self.base_url = f"http://{host}:{port}/mopidy/rpc"
        self.timeout = 30  # Збільшено для YouTube пошуку

    def _rpc_call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Виконує JSON-RPC виклик до Mopidy"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
        }
        if params:
            payload["params"] = params

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("result")
        except requests.exceptions.RequestException as e:
            print(f"❌ Помилка Mopidy RPC: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Помилка парсингу JSON: {e}")
            return None

    def is_running(self) -> bool:
        """Перевіряє чи запущений Mopidy"""
        version = self._rpc_call("core.get_version")
        return version is not None

    def search(self, query: str, source: str = "any") -> List[Dict[str, Any]]:
        """
        Шукає треки
        
        Args:
            query: Пошуковий запит
            source: spotify, youtube, local, або any
        
        Returns:
            Список знайдених треків
        """
        uris = None
        if source == "spotify":
            uris = ["spotify:"]
        elif source == "youtube":
            uris = ["yt:"]
        elif source == "local":
            uris = ["local:"]

        params: Dict[str, Any] = {"query": {"any": [query]}}
        if uris:
            params["uris"] = uris

        result = self._rpc_call("core.library.search", params)
        
        if not result:
            return []

        # Збираємо всі треки з результатів
        tracks: List[Dict[str, Any]] = []
        if isinstance(result, list):
            for search_result in result:
                if isinstance(search_result, dict) and "tracks" in search_result:
                    result_tracks = search_result.get("tracks", [])
                    if isinstance(result_tracks, list):
                        tracks.extend(result_tracks)
        
        return tracks

    def play_track(self, track_name: str, source: str = "any") -> Tuple[bool, str]:
        """
        Шукає і відтворює трек
        
        Args:
            track_name: Назва треку/виконавця
            source: spotify, youtube, local, або any
        """
        if not self.is_running():
            return False, "❌ Mopidy не запущений. Запусти: sudo systemctl start mopidy"

        # Шукаємо трек
        tracks = self.search(track_name, source)
        
        if not tracks:
            return False, f"❌ Трек '{track_name}' не знайдено"

        # Беремо перший результат
        track = tracks[0]
        track_uri = track.get("uri")
        
        if not track_uri:
            return False, f"❌ Не вдалося отримати URI треку"

        # Очищаємо поточний плейлист
        self._rpc_call("core.tracklist.clear")

        # Додаємо трек
        add_result = self._rpc_call("core.tracklist.add", {"uris": [track_uri]})
        
        if not add_result:
            return False, "❌ Не вдалося додати трек до плейлиста"

        # Відтворюємо
        play_result = self._rpc_call("core.playback.play")
        
        if play_result is None:
            return False, "❌ Не вдалося запустити відтворення"

        # Форматуємо відповідь
        track_name_result = track.get("name", track_name)
        artists = track.get("artists", [])
        artist_name = artists[0].get("name", "Unknown") if artists else "Unknown"
        
        return True, f"▶️ Грає: {track_name_result} - {artist_name}"

    def pause(self) -> Tuple[bool, str]:
        """Ставить паузу"""
        result = self._rpc_call("core.playback.pause")
        if result is not None:
            return True, "⏸️ Пауза"
        return False, "❌ Не вдалося поставити на паузу"

    def resume(self) -> Tuple[bool, str]:
        """Відновлює відтворення"""
        result = self._rpc_call("core.playback.resume")
        if result is not None:
            return True, "▶️ Продовжую"
        return False, "❌ Не вдалося відновити відтворення"

    def stop(self) -> Tuple[bool, str]:
        """Зупиняє відтворення"""
        result = self._rpc_call("core.playback.stop")
        if result is not None:
            return True, "⏹️ Зупинено"
        return False, "❌ Не вдалося зупинити"

    def next_track(self) -> Tuple[bool, str]:
        """Наступний трек"""
        result = self._rpc_call("core.playback.next")
        if result is not None:
            return True, "⏭️ Наступний трек"
        return False, "❌ Не вдалося перемкнути"

    def previous_track(self) -> Tuple[bool, str]:
        """Попередній трек"""
        result = self._rpc_call("core.playback.previous")
        if result is not None:
            return True, "⏮️ Попередній трек"
        return False, "❌ Не вдалося перемкнути"

    def get_current_track(self) -> Optional[Dict[str, Any]]:
        """Отримує інформацію про поточний трек"""
        return self._rpc_call("core.playback.get_current_track")

    def set_volume(self, volume: int) -> Tuple[bool, str]:
        """
        Встановлює гучність
        
        Args:
            volume: 0-100
        """
        volume = max(0, min(100, volume))  # Обмежуємо 0-100
        result = self._rpc_call("core.mixer.set_volume", {"volume": volume})
        if result is not None:
            return True, f"🔊 Гучність: {volume}%"
        return False, "❌ Не вдалося змінити гучність"


# Глобальний екземпляр
mopidy_manager = MopidyManager()

