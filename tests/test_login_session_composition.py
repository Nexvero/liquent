from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from liquent_platform.identity.secure_material import (
    SecureBrowserSessionMaterialGenerator,
)
from liquent_platform.persistence.browser_sessions import DatabaseBrowserSessions
from liquent_platform.persistence.login_session_composition import (
    LoginSessionComposition,
    compose_login_sessions,
)
from liquent_platform.persistence.oidc_login_transactions import (
    DatabaseOidcLoginTransactions,
)


class EngineSentinel:
    def dispose(self) -> None:  # pragma: no cover - must never be called
        raise AssertionError("composition does not own the engine")


def test_composition_exposes_persistent_ports_and_secure_material() -> None:
    composition = compose_login_sessions(
        EngineSentinel(),  # type: ignore[arg-type]
        session_lifetime=timedelta(hours=8),
        now=lambda: datetime(2026, 8, 12, tzinfo=UTC),
    )

    assert isinstance(composition, LoginSessionComposition)
    assert isinstance(composition.transactions, DatabaseOidcLoginTransactions)
    assert isinstance(composition.sessions, DatabaseBrowserSessions)
    assert isinstance(composition.material, SecureBrowserSessionMaterialGenerator)
    assert repr(composition) == "LoginSessionComposition()"


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(seconds=-1), "day"])
def test_invalid_policy_fails_before_composition(lifetime: Any) -> None:
    with pytest.raises(ValueError, match="session lifetime must be positive"):
        compose_login_sessions(
            EngineSentinel(),  # type: ignore[arg-type]
            session_lifetime=lifetime,
        )


def test_composition_never_disposes_injected_engine() -> None:
    compose_login_sessions(
        EngineSentinel(),  # type: ignore[arg-type]
        session_lifetime=timedelta(hours=1),
    )
