from dataclasses import FrozenInstanceError, fields

import pytest

from liquent_platform.identity.external_identity import ExternalIdentity


def test_valid_identity_holds_exact_values() -> None:
    identity = ExternalIdentity("https://issuer.example", "subject-123")

    assert identity.issuer == "https://issuer.example"
    assert identity.subject == "subject-123"


@pytest.mark.parametrize(
    ("issuer", "subject", "message"),
    [
        ("", "subject", "issuer must not be empty"),
        ("issuer", "", "subject must not be empty"),
    ],
)
def test_empty_issuer_or_subject_is_rejected(
    issuer: str, subject: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        ExternalIdentity(issuer, subject)


def test_exact_case_and_slashes_are_preserved() -> None:
    identity = ExternalIdentity(
        "https://Accounts.Example.COM/Tenant/",
        "User/Subject-ID//",
    )

    # No lowercasing, no slash trimming, no normalization.
    assert identity.issuer == "https://Accounts.Example.COM/Tenant/"
    assert identity.subject == "User/Subject-ID//"


def test_case_or_slash_difference_is_a_distinct_identity() -> None:
    base = ExternalIdentity("https://issuer.example", "subject")

    assert base != ExternalIdentity("https://Issuer.Example", "subject")
    assert base != ExternalIdentity("https://issuer.example/", "subject")
    assert base != ExternalIdentity("https://issuer.example", "Subject")


def test_identity_is_immutable() -> None:
    identity = ExternalIdentity("issuer", "subject")

    with pytest.raises(FrozenInstanceError):
        identity.issuer = "other"  # type: ignore[misc]


def test_model_holds_only_issuer_and_subject() -> None:
    names = [field.name for field in fields(ExternalIdentity)]

    assert names == ["issuer", "subject"]
