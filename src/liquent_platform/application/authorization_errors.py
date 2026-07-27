"""Neutral application errors for authorization failures."""


class ResearchAuthorizationDenied(Exception):
    """Report denied research access without exposing the internal reason."""

    code = "permission_denied"

    def __init__(self) -> None:
        super().__init__(self.code)
