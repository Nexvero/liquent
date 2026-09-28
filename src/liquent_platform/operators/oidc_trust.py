"""Strict offline operator boundary for authorized OIDC trust changes."""

from __future__ import annotations

import argparse
import json
import stat
import sys
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, NoReturn, TextIO

from sqlalchemy import Engine

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_trust import (
    AuthorizedOidcTrustChange,
    OidcTrustChangeId,
    OidcTrustChangeKind,
    OidcTrustRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OidcTrustChangeConflict,
    OidcTrustChangeStoreUnavailable,
)
from liquent_platform.persistence.oidc_trust_changes import (
    DatabaseAuthorizedOidcTrustChanges,
)

_REQUEST_KEYS = {
    "actor_user_id",
    "change_id",
    "kind",
    "expected_revision",
    "configuration",
}
_CONFIGURATION_KEYS = {
    "issuer",
    "authorization_endpoint",
    "client_id",
    "redirect_uri",
    "scopes",
    "token_endpoint",
    "jwks_uri",
    "allowed_signing_algorithms",
    "clock_skew_seconds",
}


class OidcTrustOperatorInputRejected(Exception):
    """Reject malformed or insecure operator input without reflecting detail."""

    code = "oidc_trust_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class OidcTrustOperatorRequest:
    """One fully parsed request whose stable change identity survives retries."""

    actor_user_id: UserId = field(repr=False)
    change_id: OidcTrustChangeId = field(repr=False)
    kind: OidcTrustChangeKind
    expected_revision: OidcTrustRevisionId | None = field(repr=False)
    configuration: TrustedOidcClientConfiguration | None = field(repr=False)


def _private_regular_file(path: Path) -> None:
    try:
        if path.is_symlink():
            raise OidcTrustOperatorInputRejected
        status = path.stat()
    except OSError:
        raise OidcTrustOperatorInputRejected from None
    if not stat.S_ISREG(status.st_mode) or status.st_mode & 0o077:
        raise OidcTrustOperatorInputRejected


def _read_private_text(path: Path) -> str:
    _private_regular_file(path)
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise OidcTrustOperatorInputRejected from None
    if not value or "\x00" in value:
        raise OidcTrustOperatorInputRejected
    return value


def _exact_string(value: object) -> str:
    if type(value) is not str or not value:
        raise OidcTrustOperatorInputRejected
    return value


def _string_tuple(value: object) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(type(item) is not str or not item for item in value)
    ):
        raise OidcTrustOperatorInputRejected
    return tuple(value)


def _parse_configuration(value: object) -> TrustedOidcClientConfiguration | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != _CONFIGURATION_KEYS:
        raise OidcTrustOperatorInputRejected
    seconds = value["clock_skew_seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise OidcTrustOperatorInputRejected
    try:
        return TrustedOidcClientConfiguration(
            issuer=_exact_string(value["issuer"]),
            authorization_endpoint=_exact_string(value["authorization_endpoint"]),
            client_id=_exact_string(value["client_id"]),
            redirect_uri=_exact_string(value["redirect_uri"]),
            scopes=_string_tuple(value["scopes"]),
            token_endpoint=_exact_string(value["token_endpoint"]),
            jwks_uri=_exact_string(value["jwks_uri"]),
            allowed_signing_algorithms=_string_tuple(
                value["allowed_signing_algorithms"]
            ),
            clock_skew=timedelta(seconds=seconds),
        )
    except (TypeError, ValueError, OverflowError):
        raise OidcTrustOperatorInputRejected from None


def load_operator_request(path: Path) -> OidcTrustOperatorRequest:
    """Load one exact, private, local JSON request without normalization."""

    try:
        raw = json.loads(_read_private_text(path))
        if not isinstance(raw, dict) or set(raw) != _REQUEST_KEYS:
            raise OidcTrustOperatorInputRejected
        expected_value = raw["expected_revision"]
        expected = (
            None
            if expected_value is None
            else OidcTrustRevisionId(_exact_string(expected_value))
        )
        request = OidcTrustOperatorRequest(
            actor_user_id=UserId(_exact_string(raw["actor_user_id"])),
            change_id=OidcTrustChangeId(_exact_string(raw["change_id"])),
            kind=OidcTrustChangeKind(_exact_string(raw["kind"])),
            expected_revision=expected,
            configuration=_parse_configuration(raw["configuration"]),
        )
    except OidcTrustOperatorInputRejected:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise OidcTrustOperatorInputRejected from None

    valid = (
        request.kind is OidcTrustChangeKind.ACTIVATE
        and request.expected_revision is None
        and request.configuration is not None
    ) or (
        request.kind is OidcTrustChangeKind.ROTATE
        and request.expected_revision is not None
        and request.configuration is not None
    ) or (
        request.kind is OidcTrustChangeKind.DEACTIVATE
        and request.expected_revision is not None
        and request.configuration is None
    )
    if not valid:
        raise OidcTrustOperatorInputRejected
    return request


def apply_operator_request(
    engine: Engine,
    request: OidcTrustOperatorRequest,
    *,
    material: SecureIdentityAuthorityMaterialGenerator,
) -> AuthorizedOidcTrustChange | None:
    """Delegate one already preserved request to the sole mutation boundary."""

    store = DatabaseAuthorizedOidcTrustChanges(
        engine, generate_revision_id=material.new_oidc_trust_revision_id
    )
    return store.change_trust(
        request.change_id,
        SessionPrincipal(request.actor_user_id),
        request.kind,
        request.expected_revision,
        request.configuration,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-oidc-trust")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("new-change-id")
    apply = commands.add_parser("apply")
    apply.add_argument("--database-url-file", required=True, type=Path)
    apply.add_argument("--request", required=True, type=Path)
    return parser


def _emit(stream: TextIO, outcome: str) -> None:
    stream.write(json.dumps({"outcome": outcome}, separators=(",", ":")) + "\n")


def _fail(stream: TextIO, code: str, exit_code: int) -> NoReturn:
    stream.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(exit_code)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    material = SecureIdentityAuthorityMaterialGenerator()
    if args.command == "new-change-id":
        sys.stdout.write(material.new_oidc_trust_change_id().value + "\n")
        return 0

    engine: Engine | None = None
    try:
        request = load_operator_request(args.request)
        database_url = _read_private_text(args.database_url_file).strip()
        if not database_url:
            raise OidcTrustOperatorInputRejected
        engine = build_engine(database_url)
        result = apply_operator_request(engine, request, material=material)
    except OidcTrustOperatorInputRejected:
        _fail(sys.stderr, OidcTrustOperatorInputRejected.code, 2)
    except OidcTrustChangeConflict:
        _fail(sys.stderr, OidcTrustChangeConflict.code, 3)
    except OidcTrustChangeStoreUnavailable:
        _fail(sys.stderr, OidcTrustChangeStoreUnavailable.code, 4)
    except Exception:
        _fail(sys.stderr, OidcTrustChangeStoreUnavailable.code, 4)
    finally:
        if engine is not None:
            engine.dispose()

    _emit(sys.stdout, "applied" if result is not None else "rejected")
    return 0 if result is not None else 5
