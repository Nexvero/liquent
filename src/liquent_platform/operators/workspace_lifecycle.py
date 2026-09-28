"""Owner-only offline operator for regular workspace lifecycle decisions."""

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
from liquent_platform.identity.lifecycle import (
    AuthorizedWorkspaceLifecycleChange,
    WorkspaceLifecycleChangeId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.operators.initial_bootstrap import _read_private, _write_result
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    WorkspaceLifecycleChangeConflict,
    WorkspaceLifecycleChangeStoreUnavailable,
)
from liquent_platform.persistence.workspace_lifecycle_changes import (
    DatabaseAuthorizedWorkspaceLifecycleChanges,
)


class WorkspaceLifecycleOperatorInputRejected(Exception):
    code = "workspace_lifecycle_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class WorkspaceCreateRequest:
    actor_user_id: UserId = field(repr=False)
    change_id: WorkspaceLifecycleChangeId = field(repr=False)
    initial_onboarding_manager_user_id: UserId = field(repr=False)
    expected_revision: WorkspaceLifecycleRevisionId = field(repr=False)


@dataclass(frozen=True, slots=True)
class WorkspaceDeactivateRequest:
    actor_user_id: UserId = field(repr=False)
    change_id: WorkspaceLifecycleChangeId = field(repr=False)
    target_workspace_id: WorkspaceId = field(repr=False)
    expected_revision: WorkspaceLifecycleRevisionId = field(repr=False)


def _string(value: object) -> str:
    if type(value) is not str or not value:
        raise WorkspaceLifecycleOperatorInputRejected
    return value


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_read_private(path))
    except Exception:
        raise WorkspaceLifecycleOperatorInputRejected from None
    if not isinstance(value, dict):
        raise WorkspaceLifecycleOperatorInputRejected
    return value


def load_create_request(path: Path) -> WorkspaceCreateRequest:
    value = _json(path)
    if set(value) != {
        "actor_user_id", "change_id", "initial_onboarding_manager_user_id",
        "expected_revision",
    }:
        raise WorkspaceLifecycleOperatorInputRejected
    try:
        return WorkspaceCreateRequest(
            UserId(_string(value["actor_user_id"])),
            WorkspaceLifecycleChangeId(_string(value["change_id"])),
            UserId(_string(value["initial_onboarding_manager_user_id"])),
            WorkspaceLifecycleRevisionId(_string(value["expected_revision"])),
        )
    except (TypeError, ValueError):
        raise WorkspaceLifecycleOperatorInputRejected from None


def load_deactivate_request(path: Path) -> WorkspaceDeactivateRequest:
    value = _json(path)
    if set(value) != {
        "actor_user_id", "change_id", "target_workspace_id",
        "expected_revision",
    }:
        raise WorkspaceLifecycleOperatorInputRejected
    try:
        return WorkspaceDeactivateRequest(
            UserId(_string(value["actor_user_id"])),
            WorkspaceLifecycleChangeId(_string(value["change_id"])),
            WorkspaceId(_string(value["target_workspace_id"])),
            WorkspaceLifecycleRevisionId(_string(value["expected_revision"])),
        )
    except (TypeError, ValueError):
        raise WorkspaceLifecycleOperatorInputRejected from None


def apply_workspace_lifecycle(
    engine: Engine,
    request: WorkspaceCreateRequest | WorkspaceDeactivateRequest,
    material: SecureIdentityAuthorityMaterialGenerator,
) -> AuthorizedWorkspaceLifecycleChange | None:
    store = DatabaseAuthorizedWorkspaceLifecycleChanges(
        engine,
        generate_workspace_id=material.new_workspace_id,
        generate_revision_id=material.new_workspace_lifecycle_revision_id,
    )
    principal = SessionPrincipal(request.actor_user_id)
    if type(request) is WorkspaceCreateRequest:
        return store.create_workspace(
            request.change_id, principal,
            request.initial_onboarding_manager_user_id,
            request.expected_revision,
        )
    if type(request) is WorkspaceDeactivateRequest:
        return store.deactivate_workspace(
            request.change_id, principal, request.target_workspace_id,
            request.expected_revision,
        )
    raise WorkspaceLifecycleOperatorInputRejected


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-workspace-lifecycle")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("new-change-id")
    for name in ("create", "deactivate"):
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
        sys.stdout.write(material.new_workspace_lifecycle_change_id().value + "\n")
        return 0
    engine: Engine | None = None
    try:
        database_url = _read_private(args.database_url_file).strip()
        if not database_url:
            raise WorkspaceLifecycleOperatorInputRejected
        request = (
            load_create_request(args.request)
            if args.command == "create"
            else load_deactivate_request(args.request)
        )
        engine = build_engine(database_url)
        result = apply_workspace_lifecycle(engine, request, material)
        if result is not None:
            _write_result(args.result_file, {
                "change_id": result.change_id.value,
                "revision_id": result.revision_id.value,
                "workspace_id": str(result.target_workspace_id),
            })
    except WorkspaceLifecycleOperatorInputRejected:
        _fail(WorkspaceLifecycleOperatorInputRejected.code, 2)
    except WorkspaceLifecycleChangeConflict:
        _fail("workspace_lifecycle_operator_conflict", 3)
    except WorkspaceLifecycleChangeStoreUnavailable:
        _fail("workspace_lifecycle_operator_unavailable", 4)
    except Exception:
        _fail("workspace_lifecycle_operator_unavailable", 4)
    finally:
        if engine is not None:
            engine.dispose()
    if result is None:
        _emit("rejected")
        return 5
    _emit("applied")
    return 0
