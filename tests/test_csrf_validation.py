import pytest

from liquent_platform.application.csrf import (
    CsrfValidationFailed,
    require_valid_csrf_token,
)


def test_exact_non_empty_csrf_token_is_accepted() -> None:
    require_valid_csrf_token("session-proof", "session-proof")


@pytest.mark.parametrize(
    ("expected", "presented"),
    [
        (None, "proof"),
        ("proof", None),
        ("", ""),
        ("expected", "different"),
    ],
)
def test_missing_empty_or_mismatched_csrf_token_is_rejected(
    expected: str | None,
    presented: str | None,
) -> None:
    with pytest.raises(CsrfValidationFailed) as captured:
        require_valid_csrf_token(expected, presented)

    assert captured.value.code == "csrf_validation_failed"
    assert str(captured.value) == "csrf_validation_failed"
    assert "expected" not in captured.value.args
    assert "different" not in captured.value.args


def test_non_ascii_mismatch_remains_a_neutral_failure() -> None:
    with pytest.raises(CsrfValidationFailed, match="csrf_validation_failed"):
        require_valid_csrf_token("gültig", "ungültig")

