"""Owner-only offline operator for workspace management-authority recovery."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

from sqlalchemy import Engine

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.membership_management import (
    RecoveredWorkspaceMembershipAuthoritySet,
    WorkspaceMembershipAuthorityRecoveryId,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.operators.initial_bootstrap import _read_private, _write_result
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipAuthorityRecoveryConflict,
    WorkspaceMembershipAuthorityRecoveryUnavailable,
)
from liquent_platform.persistence.membership_authority_recovery import (
    DatabaseOfflineWorkspaceMembershipAuthorityRecovery,
)


class MembershipAuthorityRecoveryOperatorInputRejected(Exception):
    code = "membership_authority_recovery_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class MembershipAuthorityRecoveryRequest:
    recovery_id: WorkspaceMembershipAuthorityRecoveryId = field(repr=False)
    target_user_id: UserId = field(repr=False)
    workspace_id: WorkspaceId = field(repr=False)
    expected_revision: WorkspaceMembershipAuthoritySetRevisionId = field(
        repr=False
    )


def _string(value: object) -> str:
    if type(value) is not str or not value:
        raise MembershipAuthorityRecoveryOperatorInputRejected
    return value


def load_recovery_request(path: Path) -> MembershipAuthorityRecoveryRequest:
    try:
        value = json.loads(_read_private(path))
        if not isinstance(value, dict) or set(value) != {
            "recovery_id", "target_user_id", "workspace_id", "expected_revision",
        }:
            raise MembershipAuthorityRecoveryOperatorInputRejected
        return MembershipAuthorityRecoveryRequest(
            WorkspaceMembershipAuthorityRecoveryId(
                _string(value["recovery_id"])
            ),
            UserId(_string(value["target_user_id"])),
            WorkspaceId(_string(value["workspace_id"])),
            WorkspaceMembershipAuthoritySetRevisionId(
                _string(value["expected_revision"])
            ),
        )
    except MembershipAuthorityRecoveryOperatorInputRejected:
        raise
    except Exception:
        raise MembershipAuthorityRecoveryOperatorInputRejected from None


def recover_authority(
    engine: Engine,
    request: MembershipAuthorityRecoveryRequest,
    material: SecureIdentityAuthorityMaterialGenerator,
) -> RecoveredWorkspaceMembershipAuthoritySet | None:
    return DatabaseOfflineWorkspaceMembershipAuthorityRecovery(
        engine,
        generate_revision_id=(
            material.new_workspace_membership_authority_set_revision_id
        ),
    ).recover(
        request.recovery_id,
        request.target_user_id,
        request.workspace_id,
        request.expected_revision,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-membership-authority-recovery")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("new-recovery-id")
    recover = commands.add_parser("recover")
    recover.add_argument("--database-url-file", required=True, type=Path)
    recover.add_argument("--request", required=True, type=Path)
    recover.add_argument("--result-file", required=True, type=Path)
    return parser


def _emit(value: str) -> None:
    sys.stdout.write(json.dumps({"outcome": value}, separators=(",", ":")) + "\n")


def _fail(code: str, exit_code: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(exit_code)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    material = SecureIdentityAuthorityMaterialGenerator()
    if args.command == "new-recovery-id":
        sys.stdout.write(
            material.new_workspace_membership_authority_recovery_id().value + "\n"
        )
        return 0
    engine: Engine | None = None
    try:
        database_url = _read_private(args.database_url_file).strip()
        if not database_url:
            raise MembershipAuthorityRecoveryOperatorInputRejected
        request = load_recovery_request(args.request)
        engine = build_engine(database_url)
        result = recover_authority(engine, request, material)
        if result is not None:
            _write_result(args.result_file, {
                "recovery_id": result.recovery_id.value,
                "revision_id": result.revision_id.value,
            })
    except MembershipAuthorityRecoveryOperatorInputRejected:
        _fail(MembershipAuthorityRecoveryOperatorInputRejected.code, 2)
    except WorkspaceMembershipAuthorityRecoveryConflict:
        _fail("membership_authority_recovery_operator_conflict", 3)
    except WorkspaceMembershipAuthorityRecoveryUnavailable:
        _fail("membership_authority_recovery_operator_unavailable", 4)
    except Exception:
        _fail("membership_authority_recovery_operator_unavailable", 4)
    finally:
        if engine is not None:
            engine.dispose()
    if result is None:
        _emit("rejected")
        return 5
    _emit("recovered")
    return 0
