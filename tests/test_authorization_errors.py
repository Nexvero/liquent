from liquent_platform.application.authorization_errors import (
    ResearchAuthorizationDenied,
)


def test_research_authorization_error_has_one_neutral_public_code() -> None:
    error = ResearchAuthorizationDenied()

    assert error.code == "permission_denied"
    assert str(error) == "permission_denied"
    assert error.args == ("permission_denied",)


def test_research_authorization_error_accepts_no_internal_detail() -> None:
    try:
        ResearchAuthorizationDenied("membership missing")  # type: ignore[call-arg]
    except TypeError:
        pass
    else:
        raise AssertionError("authorization error must not accept internal detail")
