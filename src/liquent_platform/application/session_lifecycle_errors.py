"""Neutral application errors for browser-session lifecycle conflicts."""


class SessionLifecycleConflict(Exception):
    """Report a failed atomic session change without internal details."""

    code = "session_lifecycle_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class SessionRevocationUnavailable(Exception):
    """Report that a session revocation could not be completed by its store.

    A neutral, typed infrastructure error that never carries a session id or
    other internal detail.
    """

    code = "session_revocation_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)
