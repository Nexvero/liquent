"""Technical limits a later OIDC verification adapter must be given."""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class OidcVerificationPolicy:
    """The bounds LQ-160 requires, supplied by composition rather than defaults.

    LQ-160 makes finite connect, read, and overall timeouts, a bounded response
    size, and a time-bounded JWKS cache binding for the verification adapter.
    This object carries exactly those limits so they must be stated explicitly
    at composition time; there are deliberately **no defaults**, because a
    default timeout or size is an operational decision nobody consciously made.

    It also sets **no ceilings**: no maximum byte count and no maximum timeout
    or cache duration. This slice checks *structural* validity — that every
    bound exists, is finite, and is positive — not operational tuning. Concrete
    values come later from composition and are reviewed there.

    A duration is required to be a real ``timedelta``, and that requirement is
    what makes it finite and exactly microsecond-representable: a timedelta
    cannot hold infinity or NaN, since ``timedelta(seconds=float("inf"))``
    raises and the type is bounded with microsecond resolution. A separate
    finiteness check would therefore be unreachable. Sub-microsecond input is
    already rounded by ``timedelta`` itself at the caller's construction, so a
    duration too small to have any effect arrives as ``timedelta(0)`` and is
    rejected as non-positive. This object normalizes nothing of its own.

    The policy holds **only** technical limits. It carries no URL, issuer,
    client, redirect uri, algorithm, key, token, authorization code, nonce,
    state, identity, admission, session, or provider data. It reads no clock,
    performs no network operation, builds no client timeout object, implements
    no cache, and decides no retry or redirect behaviour — the adapter does all
    of that, bounded by these values.
    """

    connect_timeout: timedelta
    read_timeout: timedelta
    total_timeout: timedelta
    token_response_max_bytes: int
    jwks_response_max_bytes: int
    jwks_cache_ttl: timedelta

    def __post_init__(self) -> None:
        # Messages name the field but never echo the value, matching the
        # existing configuration model.
        for name in (
            "connect_timeout",
            "read_timeout",
            "total_timeout",
            "jwks_cache_ttl",
        ):
            self._validate_duration(name)
        for name in ("token_response_max_bytes", "jwks_response_max_bytes"):
            self._validate_size(name)
        # Compared only after both operands are known-good durations, so an
        # invalid type fails with the contractual ValueError rather than a
        # mixed-comparison TypeError.
        if self.connect_timeout > self.total_timeout:
            raise ValueError("connect_timeout must not exceed total_timeout")
        if self.read_timeout > self.total_timeout:
            raise ValueError("read_timeout must not exceed total_timeout")

    def _validate_duration(self, name: str) -> None:
        value = getattr(self, name)
        if not isinstance(value, timedelta):
            raise ValueError(f"{name} must be a timedelta")
        if value <= timedelta(0):
            raise ValueError(f"{name} must be positive")

    def _validate_size(self, name: str) -> None:
        value = getattr(self, name)
        # bool is a subclass of int, and True would silently mean one byte.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an int")
        if value <= 0:
            raise ValueError(f"{name} must be positive")
