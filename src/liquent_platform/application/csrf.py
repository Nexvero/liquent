"""Fail-closed CSRF proof validation for mutating browser requests."""

from hmac import compare_digest


class CsrfValidationFailed(Exception):
    """Report an invalid CSRF proof without exposing either value."""

    code = "csrf_validation_failed"

    def __init__(self) -> None:
        super().__init__(self.code)


def require_valid_csrf_token(
    expected: str | None,
    presented: str | None,
) -> None:
    """Accept only an exact, non-empty match using constant-time comparison."""

    if not expected or not presented or not compare_digest(
        expected.encode(), presented.encode()
    ):
        raise CsrfValidationFailed

