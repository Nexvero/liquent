"""Owner-only offline operator for regular user lifecycle decisions."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

from sqlalchemy import Engine

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.lifecycle import (
    AuthorizedUserLifecycleChange,
    UserLifecycleChangeId,
    UserLifecycleIntent,
    UserLifecycleRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.operators.initial_bootstrap import _read_private, _write_result
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    UserLifecycleChangeConflict,
    UserLifecycleChangeStoreUnavailable,
)
from liquent_platform.persistence.user_lifecycle_changes import (
    DatabaseAuthorizedUserLifecycleChanges,
)


class UserLifecycleOperatorInputRejected(Exception):
    code = "user_lifecycle_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class UserCreateRequest:
    actor_user_id: UserId = field(repr=False)
    change_id: UserLifecycleChangeId = field(repr=False)
    expected_revision: UserLifecycleRevisionId = field(repr=False)


@dataclass(frozen=True, slots=True)
class UserStatusRequest:
    actor_user_id: UserId = field(repr=False)
    change_id: UserLifecycleChangeId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    expected_revision: UserLifecycleRevisionId = field(repr=False)


def _string(value: object) -> str:
    if type(value) is not str or not value:
        raise UserLifecycleOperatorInputRejected
    return value


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_read_private(path))
    except Exception:
        raise UserLifecycleOperatorInputRejected from None
    if not isinstance(value, dict):
        raise UserLifecycleOperatorInputRejected
    return value


def load_create_request(path: Path) -> UserCreateRequest:
    value = _json(path)
    if set(value) != {"actor_user_id", "change_id", "expected_revision"}:
        raise UserLifecycleOperatorInputRejected
    try:
        return UserCreateRequest(
            UserId(_string(value["actor_user_id"])),
            UserLifecycleChangeId(_string(value["change_id"])),
            UserLifecycleRevisionId(_string(value["expected_revision"])),
        )
    except (TypeError, ValueError):
        raise UserLifecycleOperatorInputRejected from None


def load_status_request(path: Path) -> UserStatusRequest:
    value = _json(path)
    if set(value) != {
        "actor_user_id", "change_id", "target_user_id", "expected_revision",
    }:
        raise UserLifecycleOperatorInputRejected
    try:
        return UserStatusRequest(
            UserId(_string(value["actor_user_id"])),
            UserLifecycleChangeId(_string(value["change_id"])),
            UserId(_string(value["target_user_id"])),
            UserLifecycleRevisionId(_string(value["expected_revision"])),
        )
    except (TypeError, ValueError):
        raise UserLifecycleOperatorInputRejected from None


def apply_user_lifecycle(
    engine: Engine,
    request: UserCreateRequest | UserStatusRequest,
    intent: UserLifecycleIntent,
    material: SecureIdentityAuthorityMaterialGenerator,
) -> AuthorizedUserLifecycleChange | None:
    store = DatabaseAuthorizedUserLifecycleChanges(
        engine,
        generate_user_id=material.new_user_id,
        generate_revision_id=material.new_user_lifecycle_revision_id,
        now=lambda: datetime.now(UTC),
    )
    principal = SessionPrincipal(request.actor_user_id)
    if type(request) is UserCreateRequest and intent is UserLifecycleIntent.CREATE:
        return store.create_user(
            request.change_id, principal, request.expected_revision
        )
    if type(request) is UserStatusRequest and intent in {
        UserLifecycleIntent.DEACTIVATE,
        UserLifecycleIntent.REACTIVATE,
    }:
        return store.change_user_status(
            request.change_id, principal, request.target_user_id,
            intent, request.expected_revision,
        )
    raise UserLifecycleOperatorInputRejected


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-user-lifecycle")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("new-change-id")
    for name in ("create", "deactivate", "reactivate"):
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
        sys.stdout.write(material.new_user_lifecycle_change_id().value + "\n")
        return 0
    engine: Engine | None = None
    try:
        database_url = _read_private(args.database_url_file).strip()
        if not database_url:
            raise UserLifecycleOperatorInputRejected
        request = (
            load_create_request(args.request)
            if args.command == "create"
            else load_status_request(args.request)
        )
        intent = UserLifecycleIntent(args.command)
        engine = build_engine(database_url)
        result = apply_user_lifecycle(engine, request, intent, material)
        if result is not None:
            _write_result(args.result_file, {
                "change_id": result.change_id.value,
                "revision_id": result.revision_id.value,
                "user_id": str(result.target_user_id),
            })
    except UserLifecycleOperatorInputRejected:
        _fail(UserLifecycleOperatorInputRejected.code, 2)
    except UserLifecycleChangeConflict:
        _fail("user_lifecycle_operator_conflict", 3)
    except UserLifecycleChangeStoreUnavailable:
        _fail("user_lifecycle_operator_unavailable", 4)
    except Exception:
        _fail("user_lifecycle_operator_unavailable", 4)
    finally:
        if engine is not None:
            engine.dispose()
    if result is None:
        _emit("rejected")
        return 5
    _emit("applied")
    return 0
