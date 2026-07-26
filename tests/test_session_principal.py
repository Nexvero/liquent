from dataclasses import FrozenInstanceError, fields

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import SessionPrincipal


def test_session_principal_contains_only_verified_user_identity() -> None:
    principal = SessionPrincipal(user_id=UserId("user-1"))

    assert principal.user_id == "user-1"
    assert [field.name for field in fields(SessionPrincipal)] == ["user_id"]


def test_session_principal_is_immutable() -> None:
    principal = SessionPrincipal(user_id=UserId("user-1"))

    with pytest.raises(FrozenInstanceError):
        principal.user_id = UserId("user-2")  # type: ignore[misc]
