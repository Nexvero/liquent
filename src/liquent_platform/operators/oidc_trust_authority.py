"""Owner-only offline operator for global OIDC-trust authority lifecycle."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn

from sqlalchemy import Engine

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.oidc_trust import (
    AnchoredOidcTrustAuthoritySet,
    AuthorizedOidcTrustAuthorityLifecycleChange,
    OidcTrustAuthorityLifecycleChangeId,
    OidcTrustAuthorityLifecycleIntent,
    OidcTrustAuthoritySetRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.operators.initial_bootstrap import _read_private, _write_result
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityAnchorConflict,
    OidcTrustAuthorityAnchorUnavailable,
    OidcTrustAuthorityLifecycleConflict,
    OidcTrustAuthorityLifecycleUnavailable,
)
from liquent_platform.persistence.oidc_trust_authority_anchor import (
    DatabaseOidcTrustAuthoritySetAnchor,
)
from liquent_platform.persistence.oidc_trust_authority_lifecycle import (
    DatabaseAuthorizedOidcTrustAuthorityLifecycle,
)


class OidcTrustAuthorityOperatorInputRejected(Exception):
    code = "oidc_trust_authority_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class OidcTrustAuthorityAnchorRequest:
    actor_user_id: UserId = field(repr=False)
    change_id: OidcTrustAuthorityLifecycleChangeId = field(repr=False)


@dataclass(frozen=True, slots=True)
class OidcTrustAuthorityLifecycleRequest:
    actor_user_id: UserId = field(repr=False)
    change_id: OidcTrustAuthorityLifecycleChangeId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    intent: OidcTrustAuthorityLifecycleIntent
    expected_revision: OidcTrustAuthoritySetRevisionId = field(repr=False)


def _string(value: object) -> str:
    if type(value) is not str or not value:
        raise OidcTrustAuthorityOperatorInputRejected
    return value


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_read_private(path))
    except Exception:
        raise OidcTrustAuthorityOperatorInputRejected from None
    if not isinstance(value, dict):
        raise OidcTrustAuthorityOperatorInputRejected
    return value


def load_anchor_request(path: Path) -> OidcTrustAuthorityAnchorRequest:
    value = _json(path)
    if set(value) != {"actor_user_id", "change_id"}:
        raise OidcTrustAuthorityOperatorInputRejected
    try:
        return OidcTrustAuthorityAnchorRequest(
            UserId(_string(value["actor_user_id"])),
            OidcTrustAuthorityLifecycleChangeId(_string(value["change_id"])),
        )
    except (TypeError, ValueError):
        raise OidcTrustAuthorityOperatorInputRejected from None


def load_lifecycle_request(path: Path) -> OidcTrustAuthorityLifecycleRequest:
    value = _json(path)
    if set(value) != {
        "actor_user_id", "change_id", "target_user_id", "intent",
        "expected_revision",
    }:
        raise OidcTrustAuthorityOperatorInputRejected
    try:
        return OidcTrustAuthorityLifecycleRequest(
            UserId(_string(value["actor_user_id"])),
            OidcTrustAuthorityLifecycleChangeId(_string(value["change_id"])),
            UserId(_string(value["target_user_id"])),
            OidcTrustAuthorityLifecycleIntent(_string(value["intent"])),
            OidcTrustAuthoritySetRevisionId(
                _string(value["expected_revision"])
            ),
        )
    except (TypeError, ValueError):
        raise OidcTrustAuthorityOperatorInputRejected from None


def anchor_authority(
    engine: Engine,
    request: OidcTrustAuthorityAnchorRequest,
    material: SecureIdentityAuthorityMaterialGenerator,
) -> AnchoredOidcTrustAuthoritySet | None:
    return DatabaseOidcTrustAuthoritySetAnchor(
        engine,
        generate_revision_id=material.new_oidc_trust_authority_set_revision_id,
    ).anchor(request.change_id, SessionPrincipal(request.actor_user_id))


def apply_lifecycle(
    engine: Engine,
    request: OidcTrustAuthorityLifecycleRequest,
    material: SecureIdentityAuthorityMaterialGenerator,
) -> AuthorizedOidcTrustAuthorityLifecycleChange | None:
    return DatabaseAuthorizedOidcTrustAuthorityLifecycle(
        engine,
        generate_revision_id=material.new_oidc_trust_authority_set_revision_id,
    ).change_authority(
        request.change_id,
        SessionPrincipal(request.actor_user_id),
        request.target_user_id,
        request.intent,
        request.expected_revision,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-oidc-trust-authority")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("new-change-id")
    for name in ("anchor", "apply"):
        command = commands.add_parser(name)
        command.add_argument("--database-url-file", required=True, type=Path)
        command.add_argument("--request", required=True, type=Path)
        command.add_argument("--result-file", required=True, type=Path)
    return parser


def _emit(value: str) -> None:
    sys.stdout.write(json.dumps({"outcome": value}, separators=(",", ":")) + "\n")


def _fail(code: str, exit_code: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(exit_code)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    material = SecureIdentityAuthorityMaterialGenerator()
    if args.command == "new-change-id":
        sys.stdout.write(
            material.new_oidc_trust_authority_lifecycle_change_id().value + "\n"
        )
        return 0
    engine: Engine | None = None
    try:
        database_url = _read_private(args.database_url_file).strip()
        if not database_url:
            raise OidcTrustAuthorityOperatorInputRejected
        request = (
            load_anchor_request(args.request)
            if args.command == "anchor"
            else load_lifecycle_request(args.request)
        )
        engine = build_engine(database_url)
        result = (
            anchor_authority(engine, request, material)
            if isinstance(request, OidcTrustAuthorityAnchorRequest)
            else apply_lifecycle(engine, request, material)
        )
        if result is not None:
            _write_result(args.result_file, {
                "change_id": result.change_id.value,
                "revision_id": result.revision_id.value,
            })
    except OidcTrustAuthorityOperatorInputRejected:
        _fail(OidcTrustAuthorityOperatorInputRejected.code, 2)
    except (OidcTrustAuthorityAnchorConflict,
            OidcTrustAuthorityLifecycleConflict):
        _fail("oidc_trust_authority_operator_conflict", 3)
    except (OidcTrustAuthorityAnchorUnavailable,
            OidcTrustAuthorityLifecycleUnavailable):
        _fail("oidc_trust_authority_operator_unavailable", 4)
    except Exception:
        _fail("oidc_trust_authority_operator_unavailable", 4)
    finally:
        if engine is not None:
            engine.dispose()
    if result is None:
        _emit("rejected")
        return 5
    _emit("anchored" if args.command == "anchor" else "applied")
    return 0
