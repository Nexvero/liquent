"""Cryptographically secure short-lived material for an OIDC login start."""

import hashlib
import secrets
from base64 import urlsafe_b64encode
from dataclasses import dataclass, field


MINIMUM_ENTROPY_BYTES = 32


@dataclass(frozen=True, slots=True)
class OidcLoginMaterial:
    """The independent secrets and derived PKCE challenge for one login start.

    ``state``, ``nonce``, and ``code_verifier`` are sensitive and are hidden
    from ``repr``. ``code_challenge`` is not a secret and may appear in ``repr``.
    The object carries no tokens, claims, issuer, user, admission, workspace, or
    session data and normalizes nothing.
    """

    state: str = field(repr=False)
    nonce: str = field(repr=False)
    code_verifier: str = field(repr=False)
    code_challenge: str

    def __post_init__(self) -> None:
        if not self.state:
            raise ValueError("state must not be empty")
        if not self.nonce:
            raise ValueError("nonce must not be empty")
        if not self.code_verifier:
            raise ValueError("code_verifier must not be empty")
        if not self.code_challenge:
            raise ValueError("code_challenge must not be empty")


def _s256_challenge(code_verifier: str) -> str:
    """Return BASE64URL-ENCODE(SHA256(ASCII(code_verifier))) without padding."""

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class SecureOidcLoginMaterialGenerator:
    """Generate independent URL-safe login secrets and their S256 challenge."""

    def __init__(self, entropy_bytes: int = MINIMUM_ENTROPY_BYTES) -> None:
        if (
            isinstance(entropy_bytes, bool)
            or not isinstance(entropy_bytes, int)
            or entropy_bytes < MINIMUM_ENTROPY_BYTES
        ):
            raise ValueError("login material entropy must be at least 32 bytes")
        self._entropy_bytes = entropy_bytes

    def new_login_material(self) -> OidcLoginMaterial:
        state = secrets.token_urlsafe(self._entropy_bytes)
        nonce = secrets.token_urlsafe(self._entropy_bytes)
        code_verifier = secrets.token_urlsafe(self._entropy_bytes)
        return OidcLoginMaterial(
            state,
            nonce,
            code_verifier,
            _s256_challenge(code_verifier),
        )
