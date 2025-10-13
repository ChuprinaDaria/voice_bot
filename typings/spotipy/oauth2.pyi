from typing import Any, Optional


class SpotifyOAuth:
    def __init__(
        self,
        client_id: Optional[str] = ...,
        client_secret: Optional[str] = ...,
        redirect_uri: Optional[str] = ...,
        scope: Optional[str] = ...,
        state: Optional[str] = ...,
        show_dialog: Optional[bool] = ...,
    ) -> None: ...

    def get_authorize_url(self) -> str: ...


__all__ = ["SpotifyOAuth"]


