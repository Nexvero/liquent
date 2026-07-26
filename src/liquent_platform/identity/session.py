"""Verified session identity passed into application use cases."""

from dataclasses import dataclass

from liquent_platform.identity.access import UserId


@dataclass(frozen=True, slots=True)
class SessionPrincipal:
    """A user identity already verified by an outer session boundary."""

    user_id: UserId
