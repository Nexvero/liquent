from dataclasses import MISSING, FrozenInstanceError, fields
from datetime import timedelta
from typing import Any

import pytest

from liquent_platform.identity.oidc_verification_policy import (
    OidcVerificationPolicy,
)


CONNECT = timedelta(seconds=2)
READ = timedelta(seconds=5)
TOTAL = timedelta(seconds=10)
TOKEN_BYTES = 64 * 1024
JWKS_BYTES = 128 * 1024
CACHE_TTL = timedelta(minutes=5)

FIELD_NAMES = [
    "connect_timeout",
    "read_timeout",
    "total_timeout",
    "token_response_max_bytes",
    "jwks_response_max_bytes",
    "jwks_cache_ttl",
]
DURATION_FIELDS = ["connect_timeout", "read_timeout", "total_timeout", "jwks_cache_ttl"]
SIZE_FIELDS = ["token_response_max_bytes", "jwks_response_max_bytes"]


def _policy(**overrides: Any) -> OidcVerificationPolicy:
    arguments: dict[str, Any] = {
        "connect_timeout": CONNECT,
        "read_timeout": READ,
        "total_timeout": TOTAL,
        "token_response_max_bytes": TOKEN_BYTES,
        "jwks_response_max_bytes": JWKS_BYTES,
        "jwks_cache_ttl": CACHE_TTL,
    }
    arguments.update(overrides)
    return OidcVerificationPolicy(**arguments)


def test_a_valid_policy_preserves_its_values_and_allows_equal_bounds() -> None:
    policy = _policy(connect_timeout=TOTAL, read_timeout=TOTAL)

    assert policy.connect_timeout == policy.read_timeout == policy.total_timeout == TOTAL
    assert policy.token_response_max_bytes == TOKEN_BYTES
    assert policy.jwks_response_max_bytes == JWKS_BYTES
    assert policy.jwks_cache_ttl == CACHE_TTL


def test_model_is_immutable_slotted_and_hashable() -> None:
    policy = _policy()

    with pytest.raises(FrozenInstanceError):
        policy.total_timeout = TOTAL  # type: ignore[misc]
    assert OidcVerificationPolicy.__slots__ == tuple(FIELD_NAMES)
    assert not hasattr(policy, "__dict__")
    assert hash(policy) == hash(_policy())


def test_model_has_exactly_the_six_agreed_fields_without_defaults() -> None:
    declared = fields(OidcVerificationPolicy)

    assert [field.name for field in declared] == FIELD_NAMES
    for field in declared:
        assert field.default is MISSING and field.default_factory is MISSING


@pytest.mark.parametrize("name", DURATION_FIELDS)
def test_each_duration_rejects_a_wrong_type_zero_and_negative(name: str) -> None:
    for value, reason in (
        (5, "must be a timedelta"),
        (timedelta(0), "must be positive"),
        (timedelta(seconds=-1), "must be positive"),
    ):
        with pytest.raises(ValueError, match=f"{name} {reason}"):
            _policy(**{name: value})


@pytest.mark.parametrize("name", SIZE_FIELDS)
def test_each_size_rejects_bool_non_int_zero_and_negative(name: str) -> None:
    for value, reason in (
        (True, "must be an int"),  # bool is an int subclass
        (1.0, "must be an int"),
        (0, "must be positive"),
        (-1, "must be positive"),
    ):
        with pytest.raises(ValueError, match=f"{name} {reason}"):
            _policy(**{name: value})


@pytest.mark.parametrize("name", ["connect_timeout", "read_timeout"])
def test_connect_and_read_may_not_exceed_total(name: str) -> None:
    with pytest.raises(ValueError, match=f"{name} must not exceed total_timeout"):
        _policy(**{name: TOTAL + timedelta(microseconds=1)})


def test_connect_plus_read_may_exceed_total() -> None:
    """The later deadline model decides actual expiry, not this object."""

    policy = _policy(connect_timeout=TOTAL, read_timeout=TOTAL)

    assert policy.connect_timeout + policy.read_timeout > policy.total_timeout


def test_a_rejection_names_the_field_but_never_the_value() -> None:
    with pytest.raises(ValueError) as raised:
        _policy(token_response_max_bytes=-987654321)

    message = str(raised.value)
    assert message.startswith("token_response_max_bytes")
    assert "987654321" not in message


def test_declared_fields_carry_no_configuration_or_secret_name() -> None:
    declared = {field.name for field in fields(OidcVerificationPolicy)}

    assert declared.isdisjoint(
        {
            "issuer",
            "token_endpoint",
            "jwks_uri",
            "client_id",
            "client_secret",
            "redirect_uri",
            "allowed_signing_algorithms",
            "clock_skew",
            "id_token",
            "access_token",
            "authorization_code",
            "code_verifier",
            "nonce",
            "state",
            "subject",
            "admission_id",
            "session_id",
            "user_id",
            "provider",
            "follow_redirects",
            "now",
        }
    )
