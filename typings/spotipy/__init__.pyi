from typing import Any, Dict, List, Optional


class Spotify:
    def __init__(self, auth_manager: Any | None = ..., auth: str | None = ...) -> None: ...

    def search(self, q: str, limit: int = ..., type: str = ...) -> Dict[str, Any]: ...

    def start_playback(
        self,
        *,
        device_id: Optional[str] = ...,
        context_uri: Optional[str] = ...,
        uris: Optional[List[str]] = ...,
        offset: Any = ...,
        position_ms: Optional[int] = ...,
    ) -> None: ...


__all__ = ["Spotify"]


