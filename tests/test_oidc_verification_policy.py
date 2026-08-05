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
DURATION_FIELDS = [
    "connect_timeout",
    "read_timeout",
    "total_timeout",
    "jwks_cache_ttl",
]
SIZE_FIELDS = ["token_response_max_bytes", "jwks_response_max_bytes"]


def _arguments(**overrides: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "connect_timeout": CONNECT,
        "read_timeout": READ,
        "total_timeout": TOTAL,
        "token_response_max_bytes": TOKEN_BYTES,
        "jwks_response_max_bytes": JWKS_BYTES,
        "jwks_cache_ttl": CACHE_TTL,
    }
    arguments.update(overrides)
    return arguments


def _policy(**overrides: Any) -> OidcVerificationPolicy:
    return OidcVerificationPolicy(**_arguments(**overrides))


# --- Success ---------------------------------------------------------------

def test_all_six_values_are_preserved_exactly() -> None:
    policy = _policy()

    assert policy.connect_timeout == CONNECT
    assert policy.read_timeout == READ
    assert policy.total_timeout == TOTAL
    assert policy.token_response_max_bytes == TOKEN_BYTES
    assert policy.jwks_response_max_bytes == JWKS_BYTES
    assert policy.jwks_cache_ttl == CACHE_TTL


def test_sub_second_and_equal_bounds_are_accepted_and_not_normalized() -> None:
    tiny = timedelta(microseconds=1)
    policy = _policy(connect_timeout=tiny, read_timeout=TOTAL)

    assert policy.connect_timeout == tiny  # not rounded up
    assert policy.read_timeout == policy.total_timeout  # equal is allowed


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
        assert field.default is MISSING
        assert field.default_factory is MISSING


# --- Durations -------------------------------------------------------------

@pytest.mark.parametrize("name", DURATION_FIELDS)
@pytest.mark.parametrize(
    "value", [2, 2.0, "2", None, float("inf"), timedelta, (2,)]
)
def test_a_non_timedelta_duration_is_rejected(name: str, value: Any) -> None:
    with pytest.raises(ValueError, match=f"{name} must be a timedelta"):
        _policy(**{name: value})


@pytest.mark.parametrize("name", DURATION_FIELDS)
@pytest.mark.parametrize(
    "value",
    [
        timedelta(0),
        timedelta(microseconds=-1),
        timedelta(seconds=-1),
        # Rounded to zero by timedelta itself before the model sees it.
        timedelta(microseconds=0.4),
    ],
)
def test_a_non_positive_duration_is_rejected(name: str, value: timedelta) -> None:
    with pytest.raises(ValueError, match=f"{name} must be positive"):
        _policy(**{name: value})


# --- Relations -------------------------------------------------------------

def test_connect_timeout_above_total_is_rejected() -> None:
    with pytest.raises(ValueError, match="connect_timeout must not exceed"):
        _policy(connect_timeout=TOTAL + timedelta(microseconds=1))


def test_read_timeout_above_total_is_rejected() -> None:
    with pytest.raises(ValueError, match="read_timeout must not exceed"):
        _policy(read_timeout=TOTAL + timedelta(microseconds=1))


def test_connect_plus_read_may_exceed_total() -> None:
    """The later deadline model decides actual expiry, not this object."""

    policy = _policy(connect_timeout=TOTAL, read_timeout=TOTAL)

    assert policy.connect_timeout + policy.read_timeout > policy.total_timeout


# --- Sizes -----------------------------------------------------------------

@pytest.mark.parametrize("name", SIZE_FIELDS)
@pytest.mark.parametrize("value", [True, False, 1.0, "1024", None, (1024,)])
def test_a_non_int_size_is_rejected(name: str, value: Any) -> None:
    # bool is an int subclass, so True would silently mean one byte.
    with pytest.raises(ValueError, match=f"{name} must be an int"):
        _policy(**{name: value})


@pytest.mark.parametrize("name", SIZE_FIELDS)
@pytest.mark.parametrize("value", [0, -1, -1024])
def test_a_non_positive_size_is_rejected(name: str, value: int) -> None:
    with pytest.raises(ValueError, match=f"{name} must be positive"):
        _policy(**{name: value})


# --- Structural boundaries -------------------------------------------------

def test_a_rejection_names_the_field_but_never_the_value() -> None:
    with pytest.raises(ValueError) as raised:
        _policy(token_response_max_bytes=-987654321)

    message = str(raised.value)
    assert message.startswith("token_response_max_bytes")
    assert "987654321" not in message


@pytest.mark.parametrize(
    "name",
    [
        "issuer",
        "token_endpoint",
        "jwks_uri",
        "client_id",
        "client_secret",
        "redirect_uri",
        "allowed_signing_algorithms",
        "clock_skew",
        "key",
        "keys",
        "id_token",
        "access_token",
        "authorization_code",
        "code_verifier",
        "nonce",
        "state",
        "subject",
        "identity",
        "admission_id",
        "session_id",
        "user_id",
        "workspace_id",
        "provider",
        "retries",
        "follow_redirects",
        "now",
        "clock",
    ],
)
def test_policy_carries_no_forbidden_field(name: str) -> None:
    assert not hasattr(_policy(), name)
    assert name not in {field.name for field in fields(OidcVerificationPolicy)}
