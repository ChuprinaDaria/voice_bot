from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None)

    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    
    # Groq (для швидкої LLM)
    GROQ_API_KEY: Optional[str] = Field(default=None)

    # Spotify
    SPOTIFY_CLIENT_ID: Optional[str] = Field(default=None)
    SPOTIFY_CLIENT_SECRET: Optional[str] = Field(default=None)
    SPOTIFY_REDIRECT_URI: Optional[str] = Field(default="https://voicebot.lazysoft.pl/spotify/callback")

    # Google
    GOOGLE_CREDENTIALS_PATH: str = Field(default=str(PROJECT_ROOT / "secrets" / "client_secret_763674966520-mm4jf3km7du4k23h6s963bh6qaak7qfv.apps.googleusercontent.com.json"))
    GOOGLE_REDIRECT_URI: Optional[str] = Field(default="https://voicebot.lazysoft.pl/google/callback")

    # Domain & Redirects
    DOMAIN: str = Field(default="voicebot.lazysoft.pl")

    # Security
    ENCRYPTION_KEY: Optional[str] = Field(default=None, description="URL-safe base64-encoded 32-byte key for Fernet")

    # Picovoice (Wake Word)
    PICOVOICE_ACCESS_KEY: Optional[str] = Field(default=None)
    WAKE_WORD: str = Field(default="hey google", description="Wake word для Porcupine (hey google, alexa, ok google)")

    # LED Control
    LED_GPIO_PIN: int = Field(default=18, description="GPIO pin для WS2812B LED кільця")
    LED_COUNT: int = Field(default=12, description="Кількість LED діодів")

    # Voice bot defaults
    DEFAULT_LANGUAGE: str = Field(default="uk")
    VOICE_GENDER: str = Field(default="male")

    # Database
    DATABASE_URL: str = Field(default=f"sqlite:///{PROJECT_ROOT / 'storage' / 'app.db'}")

    # Convenience accessors (snake_case) for code that prefers non-ENV style names
    @property
    def telegram_bot_token(self) -> Optional[str]:
        return self.TELEGRAM_BOT_TOKEN

    @property
    def openai_api_key(self) -> Optional[str]:
        return self.OPENAI_API_KEY
    
    @property
    def groq_api_key(self) -> Optional[str]:
        return self.GROQ_API_KEY

    @property
    def spotify_client_id(self) -> Optional[str]:
        return self.SPOTIFY_CLIENT_ID

    @property
    def spotify_client_secret(self) -> Optional[str]:
        return self.SPOTIFY_CLIENT_SECRET

    @property
    def spotify_redirect_uri(self) -> Optional[str]:
        return self.SPOTIFY_REDIRECT_URI

    @property
    def google_redirect_uri(self) -> Optional[str]:
        return self.GOOGLE_REDIRECT_URI

    @property
    def domain(self) -> str:
        return self.DOMAIN

    @property
    def google_credentials_path(self) -> str:
        return self.GOOGLE_CREDENTIALS_PATH

    @property
    def encryption_key(self) -> Optional[str]:
        return self.ENCRYPTION_KEY

    @property
    def picovoice_access_key(self) -> Optional[str]:
        return self.PICOVOICE_ACCESS_KEY

    @property
    def wake_word(self) -> str:
        return self.WAKE_WORD

    @property
    def default_language(self) -> str:
        return self.DEFAULT_LANGUAGE

    @property
    def voice_gender(self) -> str:
        return self.VOICE_GENDER

    @property
    def led_gpio_pin(self) -> int:
        return self.LED_GPIO_PIN

    @property
    def led_count(self) -> int:
        return self.LED_COUNT

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Export a module-level settings instance for convenient imports
settings = get_settings()


