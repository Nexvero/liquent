"""Controlled offline operator for workspace membership management."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn

from sqlalchemy import Engine, text

from liquent_platform.identity.access import MembershipStatus, Permission, UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.membership_management import (
    AuthorizedWorkspaceMembershipChange,
    BootstrappedWorkspaceMembershipManagementAuthority,
    WorkspaceMembershipChangeId,
    WorkspaceMembershipRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.operators.initial_bootstrap import _read_private, _write_result
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipChangeConflict,
    WorkspaceMembershipChangeStoreUnavailable,
    WorkspaceMembershipManagementBootstrapUnavailable,
)
from liquent_platform.persistence.membership_changes import (
    DatabaseAuthorizedWorkspaceMembershipChanges,
)
from liquent_platform.persistence.membership_management_bootstrap import (
    DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap,
)


class MembershipManagementOperatorInputRejected(Exception):
    code = "membership_management_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class MembershipAuthorityBootstrapRequest:
    user_id: UserId = field(repr=False)
    workspace_id: WorkspaceId = field(repr=False)


@dataclass(frozen=True, slots=True)
class MembershipChangeRequest:
    actor_user_id: UserId = field(repr=False)
    change_id: WorkspaceMembershipChangeId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    workspace_id: WorkspaceId = field(repr=False)
    expected_revision: WorkspaceMembershipRevisionId | None = field(repr=False)
    status: MembershipStatus
    permissions: frozenset[Permission] = field(repr=False)


def _string(value: object) -> str:
    if type(value) is not str or not value:
        raise MembershipManagementOperatorInputRejected
    return value


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_read_private(path))
    except Exception:
        raise MembershipManagementOperatorInputRejected from None
    if not isinstance(value, dict):
        raise MembershipManagementOperatorInputRejected
    return value


def load_bootstrap_request(path: Path) -> MembershipAuthorityBootstrapRequest:
    value = _json(path)
    if set(value) != {"user_id", "workspace_id"}:
        raise MembershipManagementOperatorInputRejected
    return MembershipAuthorityBootstrapRequest(
        UserId(_string(value["user_id"])),
        WorkspaceId(_string(value["workspace_id"])),
    )


def load_change_request(path: Path) -> MembershipChangeRequest:
    value = _json(path)
    if set(value) != {
        "actor_user_id", "change_id", "target_user_id", "workspace_id",
        "expected_revision", "status", "permissions",
    }:
        raise MembershipManagementOperatorInputRejected
    raw_permissions = value["permissions"]
    if (
        not isinstance(raw_permissions, list)
        or any(type(item) is not str for item in raw_permissions)
        or len(set(raw_permissions)) != len(raw_permissions)
    ):
        raise MembershipManagementOperatorInputRejected
    try:
        expected_value = value["expected_revision"]
        expected = (
            None if expected_value is None
            else WorkspaceMembershipRevisionId(_string(expected_value))
        )
        request = MembershipChangeRequest(
            UserId(_string(value["actor_user_id"])),
            WorkspaceMembershipChangeId(_string(value["change_id"])),
            UserId(_string(value["target_user_id"])),
            WorkspaceId(_string(value["workspace_id"])),
            expected,
            MembershipStatus(_string(value["status"])),
            frozenset(Permission(item) for item in raw_permissions),
        )
    except (TypeError, ValueError):
        raise MembershipManagementOperatorInputRejected from None
    if request.status is MembershipStatus.INACTIVE and request.permissions:
        raise MembershipManagementOperatorInputRejected
    return request


def _recover_authority(
    engine: Engine, request: MembershipAuthorityBootstrapRequest
) -> BootstrappedWorkspaceMembershipManagementAuthority | None:
    with engine.connect() as connection:
        count = connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_management_authorities"
            " WHERE workspace_id=:workspace"
        ), {"workspace": str(request.workspace_id).encode()})
        row = connection.execute(text(
            "SELECT authority.user_id FROM"
            " workspace_membership_management_authorities AS authority"
            " JOIN identity_users AS users ON users.user_id=authority.user_id"
            " JOIN identity_workspaces AS workspaces"
            " ON workspaces.workspace_id=authority.workspace_id"
            " WHERE authority.workspace_id=:workspace"
            " AND authority.status='active' AND users.status='active'"
            " AND workspaces.status='active'"
        ), {"workspace": str(request.workspace_id).encode()}).first()
    if (
        count != 1 or row is None
        or bytes(row.user_id) != str(request.user_id).encode()
    ):
        return None
    return BootstrappedWorkspaceMembershipManagementAuthority(
        request.user_id, request.workspace_id
    )


def bootstrap_authority(
    engine: Engine, request: MembershipAuthorityBootstrapRequest
) -> tuple[BootstrappedWorkspaceMembershipManagementAuthority, bool] | None:
    result = DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap(
        engine
    ).bootstrap(request.user_id, request.workspace_id)
    if result is not None:
        return result, False
    recovered = _recover_authority(engine, request)
    return None if recovered is None else (recovered, True)


def apply_change(
    engine: Engine,
    request: MembershipChangeRequest,
    material: SecureIdentityAuthorityMaterialGenerator,
) -> AuthorizedWorkspaceMembershipChange | None:
    return DatabaseAuthorizedWorkspaceMembershipChanges(
        engine,
        generate_revision_id=material.new_workspace_membership_revision_id,
    ).change_membership(
        request.change_id,
        SessionPrincipal(request.actor_user_id),
        request.target_user_id,
        request.workspace_id,
        request.expected_revision,
        request.status,
        request.permissions,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-membership-management")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("new-change-id")
    for name in ("bootstrap-authority", "apply"):
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
        sys.stdout.write(material.new_workspace_membership_change_id().value + "\n")
        return 0
    engine: Engine | None = None
    try:
        database_url = _read_private(args.database_url_file).strip()
        if not database_url:
            raise MembershipManagementOperatorInputRejected
        engine = build_engine(database_url)
        if args.command == "bootstrap-authority":
            request = load_bootstrap_request(args.request)
            outcome = bootstrap_authority(engine, request)
            if outcome is not None:
                result, recovered = outcome
                _write_result(args.result_file, {
                    "user_id": str(result.user_id),
                    "workspace_id": str(result.workspace_id),
                })
                label = "recovered" if recovered else "bootstrapped"
        else:
            request = load_change_request(args.request)
            changed = apply_change(engine, request, material)
            outcome = changed
            if changed is not None:
                _write_result(args.result_file, {
                    "change_id": changed.change_id.value,
                    "revision_id": changed.revision_id.value,
                })
                label = "applied"
    except MembershipManagementOperatorInputRejected:
        _fail(MembershipManagementOperatorInputRejected.code, 2)
    except WorkspaceMembershipChangeConflict:
        _fail(WorkspaceMembershipChangeConflict.code, 3)
    except (
        WorkspaceMembershipChangeStoreUnavailable,
        WorkspaceMembershipManagementBootstrapUnavailable,
    ):
        _fail("membership_management_operator_unavailable", 4)
    except Exception:
        _fail("membership_management_operator_unavailable", 4)
    finally:
        if engine is not None:
            engine.dispose()
    if outcome is None:
        _emit("rejected")
        return 5
    _emit(label)
    return 0
