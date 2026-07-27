"""Neutral application errors for browser-session lifecycle conflicts."""


class SessionLifecycleConflict(Exception):
    """Report a failed atomic session change without internal details."""

    code = "session_lifecycle_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)
