"""The server-side state of one not-yet-consumed OIDC login transaction."""

from dataclasses import dataclass, field
from datetime import datetime

from liquent_platform.identity.admission import IdentityAdmissionId


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class PendingOidcLoginTransaction:
    """One pending, secret-bearing login transaction awaiting its callback.

    The opaque ``state`` is the later store key and is not stored redundantly in
    the record; the ``code_challenge`` is only needed for the authorization
    request and is likewise not kept server-side. Values are stored verbatim and
    nothing is normalized. ``expected_nonce`` and ``code_verifier`` are sensitive
    and are hidden from ``repr``.

    The record carries no IdP tokens, authorization codes, claims, UserId,
    workspace membership, roles, permissions, or Liquent session data. It
    decides no current issuer trust — the callback re-checks the expected issuer
    against the active trust configuration — and it validates no URL or redirect
    safety rule: the later login-start boundary must pass an already validated
    internal relative ``return_path``. The record mutates no state and marks
    nothing as consumed; a later atomic claim store removes or replaces this
    pending state fail-closed.
    """

    expected_issuer: str
    expected_nonce: str = field(repr=False)
    code_verifier: str = field(repr=False)
    redirect_uri: str
    created_at: datetime
    expires_at: datetime
    admission_id: IdentityAdmissionId | None = None
    return_path: str | None = None

    def __post_init__(self) -> None:
        if not self.expected_issuer:
            raise ValueError("expected_issuer must not be empty")
        if not self.expected_nonce:
            raise ValueError("expected_nonce must not be empty")
        if not self.code_verifier:
            raise ValueError("code_verifier must not be empty")
        if not self.redirect_uri:
            raise ValueError("redirect_uri must not be empty")
        # Awareness is checked before the comparison so a naive value fails with
        # the contractual ValueError instead of a mixed-comparison TypeError.
        _require_aware(self.created_at, "created_at")
        _require_aware(self.expires_at, "expires_at")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        if self.return_path is not None and not self.return_path:
            raise ValueError("return_path must not be empty")
