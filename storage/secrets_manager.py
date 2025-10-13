from __future__ import annotations

import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from config import get_settings


def _get_fernet() -> Optional[Fernet]:
    settings = get_settings()
    key = settings.ENCRYPTION_KEY
    if not key:
        return None
    # Allow raw 32-byte base64 urlsafe or plain string key; normalize
    try:
        # If key looks like base64 urlsafe, try to use as is
        base64.urlsafe_b64decode(key.encode("utf-8"))
        normalized = key
    except Exception:
        # Otherwise, treat as plain string, pad/encode to 32 bytes
        raw = key.encode("utf-8")
        normalized = base64.urlsafe_b64encode(raw.ljust(32, b"0")[:32]).decode("utf-8")
    return Fernet(normalized)


def encrypt_token(plain_text: Optional[str]) -> Optional[str]:
    if plain_text is None:
        return None
    f = _get_fernet()
    if f is None:
        return plain_text
    token = f.encrypt(plain_text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_token(cipher_text: Optional[str]) -> Optional[str]:
    if cipher_text is None:
        return None
    f = _get_fernet()
    if f is None:
        return cipher_text
    try:
        plain = f.decrypt(cipher_text.encode("utf-8"))
        return plain.decode("utf-8")
    except InvalidToken:
        # Return as-is if key rotated or invalid; caller may handle
        return cipher_text


