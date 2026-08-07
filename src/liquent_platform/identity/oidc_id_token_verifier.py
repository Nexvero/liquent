"""Offline verification of one ID token against an already trusted JWKS."""

import hmac
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import jwt
from jwt import PyJWK
from jwt.exceptions import InvalidTokenError, PyJWTError

from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)


# Asymmetric only: a shared secret or an unsigned token cannot prove an
# issuer's identity, so HS*, none, and unlisted curves are never supported.
_SUPPORTED_SIGNING_ALGORITHMS = frozenset(
    {
        "RS256",
        "RS384",
        "RS512",
        "PS256",
        "PS384",
        "PS512",
        "ES256",
        "ES384",
        "ES512",
        "EdDSA",
    }
)

_TOKEN_CONTROLLED_KEY_SOURCES = ("jku", "x5u", "jwk")

# Key family, and where applicable curve, each algorithm needs. A curve of None
# means the family alone decides.
_REQUIRED_KEY_MATERIAL = {
    "RS256": ("RSA", None),
    "RS384": ("RSA", None),
    "RS512": ("RSA", None),
    "PS256": ("RSA", None),
    "PS384": ("RSA", None),
    "PS512": ("RSA", None),
    "ES256": ("EC", frozenset({"P-256"})),
    "ES384": ("EC", frozenset({"P-384"})),
    "ES512": ("EC", frozenset({"P-521"})),
    "EdDSA": ("OKP", frozenset({"Ed25519", "Ed448"})),
}


@dataclass(frozen=True, slots=True)
class _OidcIdTokenVerificationResult:
    """What one offline verification concluded, for this module's own use.

    Exactly three states exist: a verified identity, a definitive rejection, and
    a refreshable key miss — the token names a key identifier that is absent
    from the current trusted snapshot (LQ-168 §3). The miss is a private
    orchestration hint only; it proves no identity and grants no permission.

    Both fields are hidden from ``repr``, and the class stays underscore
    private: it is not exported, not part of any port, and never serialised,
    logged, or handed to transport code.
    """

    identity: ExternalIdentity | None = field(repr=False)
    refreshable_key_miss: bool = field(repr=False)

    def __post_init__(self) -> None:
        # Messages name the invariant but never echo an identity or token.
        if self.identity is not None and self.refreshable_key_miss:
            raise ValueError("a verified identity is never a refreshable key miss")


# Frozen and slotted, so the two identity-free states can be shared.
_REJECTED = _OidcIdTokenVerificationResult(identity=None, refreshable_key_miss=False)
_REFRESHABLE_KEY_MISS = _OidcIdTokenVerificationResult(
    identity=None, refreshable_key_miss=True
)


def verify_oidc_id_token(
    id_token: str,
    jwks: Mapping[str, object],
    configuration: TrustedOidcClientConfiguration,
    verification: OidcAuthorizationCodeVerification,
    now: datetime,
) -> ExternalIdentity | None:
    """Verify one ID token offline and return only the identity it proves.

    Performs no network operation and loads neither configuration nor keys: the
    caller supplies the already trusted JWKS and an explicit clock. A reliably
    reached rejection is ``None``; unusable key material or a library fault
    raises OidcVerificationUnavailable. No error carries a token, header,
    claim, key, issuer, subject, or nonce.

    A neutral wrapper around the one internal pass: a refreshable key miss and a
    definitive rejection both collapse to ``None`` here, so this contract is
    unchanged and no caller can tell the two apart.
    """

    return _verify_oidc_id_token_for_adapter(
        id_token, jwks, configuration, verification, now
    ).identity


def _verify_oidc_id_token_for_adapter(
    id_token: str,
    jwks: Mapping[str, object],
    configuration: TrustedOidcClientConfiguration,
    verification: OidcAuthorizationCodeVerification,
    now: datetime,
) -> _OidcIdTokenVerificationResult:
    """The single verification pass, keeping the refresh hint for this module.

    Same rules and the same one header parse and one ``jwt.decode`` as before;
    the only addition is that a key identifier absent from the trusted snapshot
    is reported as a refreshable miss instead of an indistinguishable rejection.
    """

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if configuration.issuer != verification.expected_issuer:
        return _REJECTED
    if not isinstance(id_token, str) or not id_token:
        return _REJECTED

    keys = jwks.get("keys") if isinstance(jwks, Mapping) else None
    if not isinstance(keys, Sequence) or isinstance(keys, (str, bytes)):
        # A trusted key set we cannot read is a technical fault, not a verdict.
        raise OidcVerificationUnavailable

    try:
        header = jwt.get_unverified_header(id_token)
    except InvalidTokenError:
        return _REJECTED
    except PyJWTError:
        raise OidcVerificationUnavailable from None

    # Following jku, x5u, or jwk would let the token being checked choose its
    # own verification key.
    if any(name in header for name in _TOKEN_CONTROLLED_KEY_SOURCES):
        return _REJECTED
    algorithm = header.get("alg")
    if not isinstance(algorithm, str) or not algorithm:
        return _REJECTED
    if algorithm not in _SUPPORTED_SIGNING_ALGORITHMS:
        return _REJECTED
    if algorithm not in configuration.allowed_signing_algorithms:
        return _REJECTED

    kid = header.get("kid")
    selected = _select_key(keys, kid, algorithm)
    if selected is None:
        # Everything LQ-168 §3 requires has been established by this point, so
        # a kid that is provably absent is the one refreshable case. Any other
        # reason for having no single key stays a definitive rejection.
        if _kid_is_provably_absent(keys, kid):
            return _REFRESHABLE_KEY_MISS
        return _REJECTED
    # A token asking for an algorithm no key in the trusted set can serve is a
    # reliable rejection, so it must not reach the unavailable path: otherwise
    # picking an allowed but unmatched alg would be a technical-failure oracle.
    if not _key_material_matches(selected, algorithm):
        return _REJECTED
    try:
        key = PyJWK.from_dict(dict(selected), algorithm=algorithm)
    except (PyJWTError, ValueError, TypeError):
        # The set is trusted, so an entry we cannot parse is a fault on our
        # side rather than a reason to reject the token.
        raise OidcVerificationUnavailable from None

    try:
        claims = jwt.decode(
            id_token,
            key=key,
            algorithms=[algorithm],
            audience=configuration.client_id,
            issuer=configuration.issuer,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                # Time is judged below against the passed clock, so no hidden
                # system time can decide validity.
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
            },
        )
    except InvalidTokenError:
        return _REJECTED
    except Exception:
        # An unexpected library or crypto fault means no verdict was reached,
        # which is never a business rejection.
        raise OidcVerificationUnavailable from None

    if not _time_claims_are_valid(claims, configuration, now):
        return _REJECTED
    if not _audience_is_valid(claims, configuration.client_id):
        return _REJECTED

    nonce = claims.get("nonce")
    if not isinstance(nonce, str) or not nonce:
        return _REJECTED
    if not hmac.compare_digest(nonce, verification.expected_nonce):
        return _REJECTED
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        return _REJECTED

    return _OidcIdTokenVerificationResult(
        identity=ExternalIdentity(issuer=configuration.issuer, subject=subject),
        refreshable_key_miss=False,
    )


def _kid_is_provably_absent(keys: Sequence[Any], kid: object) -> bool:
    """Whether the trusted set readably contains no entry with this exact kid.

    Only a structural presence probe over the same sequence the selection uses:
    no second selection matrix and no semantic JWK judgement. An entry that is
    not a mapping leaves the set unreadable, so absence cannot be claimed.
    """

    if not isinstance(kid, str) or not kid:
        return False
    return all(
        isinstance(entry, Mapping) and entry.get("kid") != kid for entry in keys
    )


def _select_key(
    keys: Sequence[Any], kid: object, algorithm: str
) -> Mapping[str, Any] | None:
    """Return the one usable JWK, or None if zero or several remain."""

    if kid is not None and (not isinstance(kid, str) or not kid):
        return None
    candidates = []
    for candidate in keys:
        if not isinstance(candidate, Mapping):
            continue
        use = candidate.get("use")
        if use is not None and use != "sig":
            continue
        key_ops = candidate.get("key_ops")
        if key_ops is not None and (
            not isinstance(key_ops, list) or "verify" not in key_ops
        ):
            continue
        declared = candidate.get("alg")
        if declared is not None and declared != algorithm:
            continue
        if kid is not None and candidate.get("kid") != kid:
            continue
        candidates.append(candidate)
    # Ambiguity is refused rather than resolved by picking one.
    return candidates[0] if len(candidates) == 1 else None


def _key_material_matches(jwk: Mapping[str, Any], algorithm: str) -> bool:
    """Whether the selected JWK is of the family the algorithm needs.

    A well-formed key of the wrong family is a rejection; a key whose family or
    curve cannot be read at all is unusable trusted material and raises.
    """

    family, curves = _REQUIRED_KEY_MATERIAL[algorithm]
    key_type = jwk.get("kty")
    if not isinstance(key_type, str) or not key_type:
        raise OidcVerificationUnavailable
    if key_type != family:
        return False
    if curves is None:
        return True
    curve = jwk.get("crv")
    if not isinstance(curve, str) or not curve:
        raise OidcVerificationUnavailable
    return curve in curves


def _numeric_date(claims: Mapping[str, Any], name: str) -> float | None:
    """Return a finite JSON NumericDate, or None if unusable."""

    value = claims.get(name)
    # bool is an int subclass and is never a timestamp.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return float(value)


def _time_claims_are_valid(
    claims: Mapping[str, Any],
    configuration: TrustedOidcClientConfiguration,
    now: datetime,
) -> bool:
    moment = now.timestamp()
    skew = configuration.clock_skew.total_seconds()

    expires_at = _numeric_date(claims, "exp")
    if expires_at is None or moment - skew >= expires_at:
        return False
    issued_at = _numeric_date(claims, "iat")
    if issued_at is None or issued_at > moment + skew:
        return False
    if "nbf" in claims:
        not_before = _numeric_date(claims, "nbf")
        if not_before is None or moment + skew < not_before:
            return False
    return True


def _audience_is_valid(claims: Mapping[str, Any], client_id: str) -> bool:
    audience = claims.get("aud")
    if isinstance(audience, str):
        audiences = [audience]
    elif isinstance(audience, list) and audience and all(
        isinstance(entry, str) and entry for entry in audience
    ):
        audiences = audience
    else:
        return False
    if client_id not in audiences:
        return False

    authorized_party = claims.get("azp")
    # Mandatory with several audiences, and validated whenever present.
    if len(audiences) > 1 or "azp" in claims:
        if not isinstance(authorized_party, str):
            return False
        if authorized_party != client_id:
            return False
    return True
