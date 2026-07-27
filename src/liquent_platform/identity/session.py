"""Verified session identity passed into application use cases."""

from dataclasses import dataclass, field
from typing import NewType

from liquent_platform.identity.access import UserId


SessionId = NewType("SessionId", str)


@dataclass(frozen=True, slots=True)
class SessionPrincipal:
    """A user identity already verified by an outer session boundary."""

    user_id: UserId


@dataclass(frozen=True, slots=True)
class ResolvedBrowserSession:
    """Security context produced only after an outer session check succeeds."""

    principal: SessionPrincipal
    expected_csrf_token: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.expected_csrf_token:
            raise ValueError("expected csrf token must not be empty")
