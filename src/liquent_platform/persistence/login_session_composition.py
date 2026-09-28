"""Internal composition of persistent login transactions and browser sessions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from liquent_platform.application.issue_session import issue_browser_session
from liquent_platform.application.rotate_session import rotate_browser_session
from liquent_platform.identity.secure_material import (
    SecureBrowserSessionMaterialGenerator,
)
from liquent_platform.identity.session import (
    IssuedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.persistence.browser_sessions import DatabaseBrowserSessions
from liquent_platform.persistence.oidc_login_transactions import (
    DatabaseOidcLoginTransactions,
)


@dataclass(frozen=True, slots=True)
class LoginSessionComposition:
    """Internal persistent capabilities without engine ownership or transport."""

    transactions: DatabaseOidcLoginTransactions
    sessions: DatabaseBrowserSessions
    material: SecureBrowserSessionMaterialGenerator
    _clock: Callable[[], datetime] = field(repr=False)
    _session_lifetime: timedelta = field(repr=False)

    def issue_session(self, principal: SessionPrincipal) -> IssuedBrowserSession:
        return issue_browser_session(
            self.sessions,
            self.material,
            principal,
            now=self._clock(),
            lifetime=self._session_lifetime,
        )

    def rotate_session(self, session_id: SessionId) -> IssuedBrowserSession:
        return rotate_browser_session(
            self.sessions,
            self.material,
            session_id,
            now=self._clock(),
            lifetime=self._session_lifetime,
        )

    def __repr__(self) -> str:
        return "LoginSessionComposition()"


def compose_login_sessions(
    engine: Engine,
    *,
    session_lifetime: timedelta,
    now: Callable[[], datetime] | None = None,
    material: SecureBrowserSessionMaterialGenerator | None = None,
) -> LoginSessionComposition:
    """Wire persistent ports around one externally owned database engine."""

    if type(session_lifetime) is not timedelta or session_lifetime <= timedelta(0):
        raise ValueError("session lifetime must be positive")
    clock = now or (lambda: datetime.now(UTC))
    source = material or SecureBrowserSessionMaterialGenerator()
    return LoginSessionComposition(
        transactions=DatabaseOidcLoginTransactions(engine, now=clock),
        sessions=DatabaseBrowserSessions(engine, now=clock),
        material=source,
        _clock=clock,
        _session_lifetime=session_lifetime,
    )
