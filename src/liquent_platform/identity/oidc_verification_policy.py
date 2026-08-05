"""Technical limits a later OIDC verification adapter must be given."""

from dataclasses import dataclass
from datetime import timedelta


def _require_positive_duration(name: str, value: object) -> None:
    if not isinstance(value, timedelta):
        raise ValueError(f"{name} must be a timedelta")
    if value <= timedelta(0):
        raise ValueError(f"{name} must be positive")


def _require_positive_size(name: str, value: object) -> None:
    # bool is a subclass of int, and True would silently mean one byte.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class OidcVerificationPolicy:
    """The bounds LQ-160 requires, supplied explicitly by composition.

    There are no defaults and no ceilings: a default or maximum timeout or size
    is an operational decision, and this object only guarantees that every bound
    exists and is positive. Values are stored verbatim.

    It carries technical limits only and implements nothing: no clock, network,
    client timeout object, cache, retry, or redirect behaviour.
    """

    connect_timeout: timedelta
    read_timeout: timedelta
    total_timeout: timedelta
    token_response_max_bytes: int
    jwks_response_max_bytes: int
    jwks_cache_ttl: timedelta

    def __post_init__(self) -> None:
        # Messages name the field but never echo the value.
        for name in (
            "connect_timeout",
            "read_timeout",
            "total_timeout",
            "jwks_cache_ttl",
        ):
            _require_positive_duration(name, getattr(self, name))
        for name in ("token_response_max_bytes", "jwks_response_max_bytes"):
            _require_positive_size(name, getattr(self, name))
        # Compared only after both operands are known-good durations, so an
        # invalid type fails with the contractual ValueError instead of a
        # mixed-comparison TypeError.
        if self.connect_timeout > self.total_timeout:
            raise ValueError("connect_timeout must not exceed total_timeout")
        if self.read_timeout > self.total_timeout:
            raise ValueError("read_timeout must not exceed total_timeout")
