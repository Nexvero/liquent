"""Owner-controlled operator for four supervisor cleanup source revisions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, NoReturn

from sqlalchemy import Engine

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import ManifestHandoffRegistryScopeId
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_clearance import (
    ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition,
    ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId,
    ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId,
    ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus,
    ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId,
    ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_clearance_mutation import (
    ChangeManifestHandoffSupervisorControlDirectoryCleanupHold,
    ChangeManifestHandoffSupervisorControlDirectoryCleanupManagement,
    ChangeManifestHandoffSupervisorControlDirectoryCleanupRecovery,
    ChangeManifestHandoffSupervisorControlDirectoryCleanupReference,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupHoldChange,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupManagementChange,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupRecoveryChange,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupReferenceChange,
    ManifestHandoffSupervisorControlDirectoryCleanupHoldChangeId,
    ManifestHandoffSupervisorControlDirectoryCleanupManagementChangeId,
    ManifestHandoffSupervisorControlDirectoryCleanupRecoveryChangeId,
    ManifestHandoffSupervisorControlDirectoryCleanupReferenceChangeId,
    ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.operators.initial_bootstrap import _write_result
from liquent_platform.operators.manifest_handoff_supervisor_control_directory_cleanup import (
    _one_line,
    _private_text,
    SupervisorControlDirectoryCleanupOperatorInputRejected,
    SupervisorControlDirectoryCleanupOperatorUnavailable,
)
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_cleanup_revision_mutations import (
    DatabaseManifestHandoffSupervisorCleanupRevisionMutations,
)


class CleanupSourceRevisionOperatorInputRejected(Exception):
    """A detail-free rejection of malformed operator input."""


class CleanupSourceRevisionOperatorUnavailable(Exception):
    """A detail-free technical process-boundary failure."""


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CleanupSourceRevisionOperatorInputRejected
        value[key] = item
    return value


def _request(path: Path, fields: set[str]) -> dict[str, Any]:
    try:
        value = json.loads(_private_text(path), object_pairs_hook=_pairs)
    except CleanupSourceRevisionOperatorInputRejected:
        raise
    except SupervisorControlDirectoryCleanupOperatorUnavailable:
        raise CleanupSourceRevisionOperatorUnavailable from None
    except (TypeError, ValueError, json.JSONDecodeError):
        raise CleanupSourceRevisionOperatorInputRejected from None
    if type(value) is not dict or set(value) != fields:
        raise CleanupSourceRevisionOperatorInputRejected
    for key, item in value.items():
        if key == "expected_revision_id" and item is None:
            continue
        if type(item) is not str or not item or item.strip() != item:
            raise CleanupSourceRevisionOperatorInputRejected
    return value


def _expected(value: object, revision_type: type):
    if value is None:
        return None
    try:
        return revision_type(value)
    except (TypeError, ValueError):
        raise CleanupSourceRevisionOperatorInputRejected from None


def load_management_request(path: Path):
    value = _request(path, {
        "actor_user_id", "change_id", "target_user_id", "scope_id",
        "expected_revision_id", "status",
    })
    try:
        principal = SessionPrincipal(UserId(value["actor_user_id"]))
        command = ChangeManifestHandoffSupervisorControlDirectoryCleanupManagement(
            ManifestHandoffSupervisorControlDirectoryCleanupManagementChangeId(
                value["change_id"]
            ),
            UserId(value["target_user_id"]),
            ManifestHandoffRegistryScopeId(value["scope_id"]),
            _expected(
                value["expected_revision_id"],
                ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId,
            ),
            ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus(
                value["status"]
            ),
        )
        return principal, command
    except CleanupSourceRevisionOperatorInputRejected:
        raise
    except (TypeError, ValueError):
        raise CleanupSourceRevisionOperatorInputRejected from None


def _target_request(path: Path, domain: str):
    value = _request(path, {
        "actor_user_id", "change_id", "directory_id",
        "expected_revision_id", "disposition",
    })
    types = {
        "hold": (
            ManifestHandoffSupervisorControlDirectoryCleanupHoldChangeId,
            ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId,
            ChangeManifestHandoffSupervisorControlDirectoryCleanupHold,
        ),
        "recovery": (
            ManifestHandoffSupervisorControlDirectoryCleanupRecoveryChangeId,
            ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId,
            ChangeManifestHandoffSupervisorControlDirectoryCleanupRecovery,
        ),
        "reference": (
            ManifestHandoffSupervisorControlDirectoryCleanupReferenceChangeId,
            ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId,
            ChangeManifestHandoffSupervisorControlDirectoryCleanupReference,
        ),
    }
    change_type, revision_type, command_type = types[domain]
    try:
        principal = SessionPrincipal(UserId(value["actor_user_id"]))
        command = command_type(
            change_type(value["change_id"]),
            ManifestHandoffSupervisorControlDirectoryId(value["directory_id"]),
            _expected(value["expected_revision_id"], revision_type),
            ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition(
                value["disposition"]
            ),
        )
        return principal, command
    except CleanupSourceRevisionOperatorInputRejected:
        raise
    except (TypeError, ValueError):
        raise CleanupSourceRevisionOperatorInputRejected from None


def _change(store, domain: str, principal: SessionPrincipal, command):
    if domain == "management":
        return store.change_control_directory_cleanup_management(principal, command)
    if domain == "hold":
        return store.change_control_directory_cleanup_hold(principal, command)
    if domain == "recovery":
        return store.change_control_directory_cleanup_recovery(principal, command)
    return store.change_control_directory_cleanup_references(principal, command)


def _management_result(command, result) -> dict[str, str]:
    if (
        type(result)
        is not CommittedManifestHandoffSupervisorControlDirectoryCleanupManagementChange
        or result.change_id != command.change_id
        or result.authority.actor_user_id != command.target_user_id
        or result.authority.scope_id != command.scope_id
    ):
        raise CleanupSourceRevisionOperatorUnavailable
    return {
        "operation_id": command.change_id.value,
        "target_user_id": command.target_user_id,
        "scope_id": command.scope_id.value,
        "revision_id": result.authority.revision_id.value,
    }


def _target_result(domain: str, command, result) -> dict[str, str]:
    result_types = {
        "hold": CommittedManifestHandoffSupervisorControlDirectoryCleanupHoldChange,
        "recovery": CommittedManifestHandoffSupervisorControlDirectoryCleanupRecoveryChange,
        "reference": CommittedManifestHandoffSupervisorControlDirectoryCleanupReferenceChange,
    }
    if (
        type(result) is not result_types[domain]
        or result.change_id != command.change_id
        or result.decision.retired.directory_id != command.directory_id
    ):
        raise CleanupSourceRevisionOperatorUnavailable
    return {
        "operation_id": command.change_id.value,
        "directory_id": command.directory_id.value,
        "revision_id": result.decision.revision_id.value,
    }


def execute_one(domain: str, engine: Engine, request_path: Path):
    if not DatabaseReadinessProbe(engine).check().ready:
        raise CleanupSourceRevisionOperatorUnavailable
    store = DatabaseManifestHandoffSupervisorCleanupRevisionMutations(engine)
    if domain == "management":
        principal, command = load_management_request(request_path)
    else:
        principal, command = _target_request(request_path, domain)
    result = _change(store, domain, principal, command)
    if (
        result is None
        or type(result)
        is ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict
    ):
        return None
    if domain == "management":
        return _management_result(command, result)
    return _target_result(domain, command, result)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="liquent-supervisor-cleanup-source-revision")
    commands = parser.add_subparsers(dest="domain", required=True)
    for domain in ("management", "hold", "recovery", "reference"):
        command = commands.add_parser(domain)
        command.add_argument("--database-url-file", required=True, type=Path)
        command.add_argument("--request", required=True, type=Path)
        command.add_argument("--result-file", required=True, type=Path)
    return parser


def _emit(outcome: str) -> None:
    sys.stdout.write(json.dumps({"outcome": outcome}, separators=(",", ":")) + "\n")


def _fail(code: str, exit_code: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(exit_code)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    engine: Engine | None = None
    try:
        try:
            database_url = _one_line(args.database_url_file)
        except SupervisorControlDirectoryCleanupOperatorInputRejected:
            raise CleanupSourceRevisionOperatorInputRejected from None
        except SupervisorControlDirectoryCleanupOperatorUnavailable:
            raise CleanupSourceRevisionOperatorUnavailable from None
        engine = build_engine(database_url)
        result = execute_one(args.domain, engine, args.request)
        if result is not None:
            _write_result(args.result_file, result)
    except CleanupSourceRevisionOperatorInputRejected:
        _fail("supervisor_cleanup_source_revision_operator_input_rejected", 2)
    except (CleanupSourceRevisionOperatorUnavailable, ManifestHandoffRegistryUnavailable):
        _fail("supervisor_cleanup_source_revision_operator_unavailable", 4)
    except Exception:
        _fail("supervisor_cleanup_source_revision_operator_unavailable", 4)
    finally:
        if engine is not None:
            engine.dispose()
    if result is None:
        _emit("rejected")
        return 5
    _emit("applied")
    return 0
