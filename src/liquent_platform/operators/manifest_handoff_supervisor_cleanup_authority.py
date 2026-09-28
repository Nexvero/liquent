"""Owner-controlled operators for four supervisor cleanup authority sets."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, NoReturn

from sqlalchemy import Engine

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import ManifestHandoffRegistryScopeId
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_mutation_authority import (
    BootstrapCleanupHoldMutationAuthority,
    BootstrapCleanupManagementMutationAuthority,
    BootstrapCleanupRecoveryMutationAuthority,
    BootstrapCleanupReferenceMutationAuthority,
    ChangeCleanupHoldMutationAuthority,
    ChangeCleanupManagementMutationAuthority,
    ChangeCleanupRecoveryMutationAuthority,
    ChangeCleanupReferenceMutationAuthority,
    CleanupHoldMutationAuthorityBootstrapId,
    CleanupHoldMutationAuthorityLifecycleChangeId,
    CleanupHoldMutationAuthorityRecoveryId,
    CleanupHoldMutationAuthoritySetRevisionId,
    CleanupManagementMutationAuthorityBootstrapId,
    CleanupManagementMutationAuthorityLifecycleChangeId,
    CleanupManagementMutationAuthorityRecoveryId,
    CleanupManagementMutationAuthoritySetRevisionId,
    CleanupRecoveryMutationAuthorityBootstrapId,
    CleanupRecoveryMutationAuthorityLifecycleChangeId,
    CleanupRecoveryMutationAuthorityRecoveryId,
    CleanupRecoveryMutationAuthoritySetRevisionId,
    CleanupReferenceMutationAuthorityBootstrapId,
    CleanupReferenceMutationAuthorityLifecycleChangeId,
    CleanupReferenceMutationAuthorityRecoveryId,
    CleanupReferenceMutationAuthoritySetRevisionId,
    ManifestHandoffSupervisorCleanupMutationAuthorityConflict,
    ManifestHandoffSupervisorCleanupMutationAuthorityLifecycleIntent,
    RecoverCleanupHoldMutationAuthority,
    RecoverCleanupManagementMutationAuthority,
    RecoverCleanupRecoveryMutationAuthority,
    RecoverCleanupReferenceMutationAuthority,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.operators.initial_bootstrap import _write_result
from liquent_platform.operators.manifest_handoff_supervisor_control_directory_cleanup import (
    _one_line,
    _request,
    SupervisorControlDirectoryCleanupOperatorInputRejected,
    SupervisorControlDirectoryCleanupOperatorUnavailable,
)
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_cleanup_mutation_authority import (
    DatabaseManifestHandoffSupervisorCleanupMutationAuthorities,
)


class CleanupAuthorityOperatorInputRejected(Exception):
    """A detail-free rejection of malformed operator input."""


class CleanupAuthorityOperatorUnavailable(Exception):
    """A detail-free technical process-boundary failure."""


@dataclass(frozen=True, slots=True)
class _Domain:
    bootstrap_id_type: type
    bootstrap_type: type
    change_id_type: type
    change_type: type
    recovery_id_type: type
    recovery_type: type
    revision_type: type


_DOMAINS = {
    "management": _Domain(
        CleanupManagementMutationAuthorityBootstrapId,
        BootstrapCleanupManagementMutationAuthority,
        CleanupManagementMutationAuthorityLifecycleChangeId,
        ChangeCleanupManagementMutationAuthority,
        CleanupManagementMutationAuthorityRecoveryId,
        RecoverCleanupManagementMutationAuthority,
        CleanupManagementMutationAuthoritySetRevisionId,
    ),
    "hold": _Domain(
        CleanupHoldMutationAuthorityBootstrapId,
        BootstrapCleanupHoldMutationAuthority,
        CleanupHoldMutationAuthorityLifecycleChangeId,
        ChangeCleanupHoldMutationAuthority,
        CleanupHoldMutationAuthorityRecoveryId,
        RecoverCleanupHoldMutationAuthority,
        CleanupHoldMutationAuthoritySetRevisionId,
    ),
    "recovery": _Domain(
        CleanupRecoveryMutationAuthorityBootstrapId,
        BootstrapCleanupRecoveryMutationAuthority,
        CleanupRecoveryMutationAuthorityLifecycleChangeId,
        ChangeCleanupRecoveryMutationAuthority,
        CleanupRecoveryMutationAuthorityRecoveryId,
        RecoverCleanupRecoveryMutationAuthority,
        CleanupRecoveryMutationAuthoritySetRevisionId,
    ),
    "reference": _Domain(
        CleanupReferenceMutationAuthorityBootstrapId,
        BootstrapCleanupReferenceMutationAuthority,
        CleanupReferenceMutationAuthorityLifecycleChangeId,
        ChangeCleanupReferenceMutationAuthority,
        CleanupReferenceMutationAuthorityRecoveryId,
        RecoverCleanupReferenceMutationAuthority,
        CleanupReferenceMutationAuthoritySetRevisionId,
    ),
}


def _load(path: Path, fields: set[str]) -> dict[str, str]:
    try:
        return _request(path, fields)
    except SupervisorControlDirectoryCleanupOperatorInputRejected:
        raise CleanupAuthorityOperatorInputRejected from None
    except SupervisorControlDirectoryCleanupOperatorUnavailable:
        raise CleanupAuthorityOperatorUnavailable from None


def load_bootstrap_request(path: Path, domain: str):
    value = _load(path, {"bootstrap_id", "target_user_id", "scope_id"})
    selected = _DOMAINS[domain]
    try:
        return selected.bootstrap_type(
            selected.bootstrap_id_type(value["bootstrap_id"]),
            UserId(value["target_user_id"]),
            ManifestHandoffRegistryScopeId(value["scope_id"]),
        )
    except (TypeError, ValueError):
        raise CleanupAuthorityOperatorInputRejected from None


def load_lifecycle_request(path: Path, domain: str):
    value = _load(path, {
        "actor_user_id", "change_id", "target_user_id", "scope_id",
        "expected_revision_id", "intent",
    })
    selected = _DOMAINS[domain]
    try:
        command = selected.change_type(
            selected.change_id_type(value["change_id"]),
            UserId(value["target_user_id"]),
            ManifestHandoffRegistryScopeId(value["scope_id"]),
            selected.revision_type(value["expected_revision_id"]),
            ManifestHandoffSupervisorCleanupMutationAuthorityLifecycleIntent(
                value["intent"]
            ),
        )
        return SessionPrincipal(UserId(value["actor_user_id"])), command
    except (TypeError, ValueError):
        raise CleanupAuthorityOperatorInputRejected from None


def load_recovery_request(path: Path, domain: str):
    value = _load(path, {
        "recovery_id", "target_user_id", "scope_id", "expected_revision_id",
    })
    selected = _DOMAINS[domain]
    try:
        return selected.recovery_type(
            selected.recovery_id_type(value["recovery_id"]),
            UserId(value["target_user_id"]),
            ManifestHandoffRegistryScopeId(value["scope_id"]),
            selected.revision_type(value["expected_revision_id"]),
        )
    except (TypeError, ValueError):
        raise CleanupAuthorityOperatorInputRejected from None


def _bootstrap(store, domain: str, command):
    if domain == "management":
        return store.bootstrap_cleanup_management_mutation_authority(command)
    if domain == "hold":
        return store.bootstrap_cleanup_hold_mutation_authority(command)
    if domain == "recovery":
        return store.bootstrap_cleanup_recovery_mutation_authority(command)
    return store.bootstrap_cleanup_reference_mutation_authority(command)


def _change(store, domain: str, principal: SessionPrincipal, command):
    if domain == "management":
        return store.change_cleanup_management_mutation_authority(principal, command)
    if domain == "hold":
        return store.change_cleanup_hold_mutation_authority(principal, command)
    if domain == "recovery":
        return store.change_cleanup_recovery_mutation_authority(principal, command)
    return store.change_cleanup_reference_mutation_authority(principal, command)


def _recover(store, domain: str, command):
    if domain == "management":
        return store.recover_cleanup_management_mutation_authority(command)
    if domain == "hold":
        return store.recover_cleanup_hold_mutation_authority(command)
    if domain == "recovery":
        return store.recover_cleanup_recovery_mutation_authority(command)
    return store.recover_cleanup_reference_mutation_authority(command)


def _operation_id(command) -> str:
    for name in ("bootstrap_id", "change_id", "recovery_id"):
        value = getattr(command, name, None)
        if value is not None:
            return value.value
    raise CleanupAuthorityOperatorUnavailable


def _execute(kind: str, domain: str, engine: Engine, request_path: Path):
    if not DatabaseReadinessProbe(engine).check().ready:
        raise CleanupAuthorityOperatorUnavailable
    store = DatabaseManifestHandoffSupervisorCleanupMutationAuthorities(engine)
    if kind == "bootstrap":
        command = load_bootstrap_request(request_path, domain)
        result = _bootstrap(store, domain, command)
    elif kind == "lifecycle":
        principal, command = load_lifecycle_request(request_path, domain)
        result = _change(store, domain, principal, command)
    else:
        command = load_recovery_request(request_path, domain)
        result = _recover(store, domain, command)
    if result is None or type(result) is ManifestHandoffSupervisorCleanupMutationAuthorityConflict:
        return None
    selected = _DOMAINS[domain]
    if type(result.revision_id) is not selected.revision_type or result.scope_id != command.scope_id:
        raise CleanupAuthorityOperatorUnavailable
    return {
        "operation_id": _operation_id(command),
        "scope_id": command.scope_id.value,
        "revision_id": result.revision_id.value,
    }


def _parser(program: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=program)
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


def _main(kind: str, program: str, argv: list[str] | None = None) -> int:
    args = _parser(program).parse_args(argv)
    engine: Engine | None = None
    try:
        database_url = _one_line(args.database_url_file)
        engine = build_engine(database_url)
        result = _execute(kind, args.domain, engine, args.request)
        if result is not None:
            _write_result(args.result_file, result)
    except CleanupAuthorityOperatorInputRejected:
        _fail(f"{program}_input_rejected".replace("-", "_"), 2)
    except (CleanupAuthorityOperatorUnavailable, ManifestHandoffRegistryUnavailable):
        _fail(f"{program}_operator_unavailable".replace("-", "_"), 4)
    except Exception:
        _fail(f"{program}_operator_unavailable".replace("-", "_"), 4)
    finally:
        if engine is not None:
            engine.dispose()
    if result is None:
        _emit("rejected")
        return 5
    _emit("applied")
    return 0


def bootstrap_main(argv: list[str] | None = None) -> int:
    return _main(
        "bootstrap", "liquent-supervisor-cleanup-authority-bootstrap", argv
    )


def lifecycle_main(argv: list[str] | None = None) -> int:
    return _main(
        "lifecycle", "liquent-supervisor-cleanup-authority-lifecycle", argv
    )


def recovery_main(argv: list[str] | None = None) -> int:
    return _main(
        "recovery", "liquent-supervisor-cleanup-authority-recovery", argv
    )
