"""Cryptographically secure material for browser-session issuance."""

import secrets

from liquent_platform.identity.session import SessionId


MINIMUM_ENTROPY_BYTES = 32


class SecureBrowserSessionMaterialGenerator:
    """Generate independent URL-safe values from operating-system randomness."""

    def __init__(self, entropy_bytes: int = MINIMUM_ENTROPY_BYTES) -> None:
        if (
            isinstance(entropy_bytes, bool)
            or not isinstance(entropy_bytes, int)
            or entropy_bytes < MINIMUM_ENTROPY_BYTES
        ):
            raise ValueError("session entropy must be at least 32 bytes")
        self._entropy_bytes = entropy_bytes

    def new_session_id(self) -> SessionId:
        return SessionId(secrets.token_urlsafe(self._entropy_bytes))

    def new_csrf_token(self) -> str:
        return secrets.token_urlsafe(self._entropy_bytes)
