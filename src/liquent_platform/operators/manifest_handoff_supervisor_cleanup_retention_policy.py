"""Owner-controlled retention-policy control-plane operators."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import secrets
import sys

from sqlalchemy import Engine

from liquent_platform.application.manifest_handoff_supervisor_control_directory_cleanup_composition import (
    compose_manifest_handoff_supervisor_cleanup_retention_operation,
)

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention_policy import (
    BootstrapManifestHandoffSupervisorCleanupRetentionPolicy,
    ChangeManifestHandoffSupervisorCleanupRetentionPolicy,
    ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority,
    ChangedManifestHandoffSupervisorCleanupRetentionPolicy,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityChangeId,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityIntent,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityRecoveryId,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId,
    ManifestHandoffSupervisorCleanupRetentionPolicyBootstrapId,
    ManifestHandoffSupervisorCleanupRetentionPolicyChangeId,
    ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent,
    ManifestHandoffSupervisorCleanupRetentionPolicyConflict,
    RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention import (
    EvaluateManifestHandoffSupervisorControlDirectoryRetention,
    ManifestHandoffSupervisorCleanupRetentionOperationConflict,
    ManifestHandoffSupervisorCleanupRetentionOperationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.operators.initial_bootstrap import _read_private, _write_result
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_cleanup_retention_policy import (
    DatabaseManifestHandoffSupervisorCleanupRetentionPolicy,
)


class CleanupRetentionPolicyOperatorUnavailable(Exception):
    """Detail-free private process-boundary failure."""


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _request(path: Path, fields: set[str]):
    try:
        value = json.loads(_read_private(path), object_pairs_hook=_pairs)
    except Exception:
        raise CleanupRetentionPolicyOperatorUnavailable from None
    if type(value) is not dict or set(value) != fields:
        raise CleanupRetentionPolicyOperatorUnavailable
    return value


def _string(value):
    if type(value) is not str or not value or value.strip() != value:
        raise CleanupRetentionPolicyOperatorUnavailable
    return value


def _seconds(value):
    if type(value) is not int or value <= 0:
        raise CleanupRetentionPolicyOperatorUnavailable
    return timedelta(seconds=value)


def load_bootstrap_request(path: Path):
    value = _request(path, {"bootstrap_id", "target_user_id", "minimum_retention_seconds"})
    try:
        return BootstrapManifestHandoffSupervisorCleanupRetentionPolicy(
            ManifestHandoffSupervisorCleanupRetentionPolicyBootstrapId(_string(value["bootstrap_id"])),
            UserId(_string(value["target_user_id"])), _seconds(value["minimum_retention_seconds"]),
        )
    except (TypeError, ValueError):
        raise CleanupRetentionPolicyOperatorUnavailable from None


def load_policy_request(path: Path):
    value = _request(path, {"actor_user_id", "change_id", "expected_revision_id", "intent", "minimum_retention_seconds"})
    try:
        expected = value["expected_revision_id"]
        if expected is not None:
            expected = ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId(_string(expected))
        duration = value["minimum_retention_seconds"]
        if duration is not None:
            duration = _seconds(duration)
        return (SessionPrincipal(UserId(_string(value["actor_user_id"]))),
            ChangeManifestHandoffSupervisorCleanupRetentionPolicy(
                ManifestHandoffSupervisorCleanupRetentionPolicyChangeId(_string(value["change_id"])),
                expected, ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent(_string(value["intent"])), duration))
    except (TypeError, ValueError):
        raise CleanupRetentionPolicyOperatorUnavailable from None


def load_lifecycle_request(path: Path):
    value = _request(path, {"actor_user_id", "change_id", "target_user_id", "expected_revision_id", "intent"})
    try:
        return (SessionPrincipal(UserId(_string(value["actor_user_id"]))),
            ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority(
                ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityChangeId(_string(value["change_id"])),
                UserId(_string(value["target_user_id"])),
                ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId(_string(value["expected_revision_id"])),
                ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityIntent(_string(value["intent"]))))
    except (TypeError, ValueError):
        raise CleanupRetentionPolicyOperatorUnavailable from None


def load_recovery_request(path: Path):
    value = _request(path, {"recovery_id", "target_user_id", "expected_revision_id"})
    try:
        return RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority(
            ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityRecoveryId(_string(value["recovery_id"])),
            UserId(_string(value["target_user_id"])),
            ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId(_string(value["expected_revision_id"])))
    except (TypeError, ValueError):
        raise CleanupRetentionPolicyOperatorUnavailable from None


def load_retention_request(path: Path):
    value = _request(path, {"operation_id", "directory_id"})
    try:
        return EvaluateManifestHandoffSupervisorControlDirectoryRetention(
            ManifestHandoffSupervisorCleanupRetentionOperationId(_string(value["operation_id"])),
            ManifestHandoffSupervisorControlDirectoryId(_string(value["directory_id"])),
        )
    except (TypeError, ValueError):
        raise CleanupRetentionPolicyOperatorUnavailable from None


def _store(engine: Engine):
    return DatabaseManifestHandoffSupervisorCleanupRetentionPolicy(
        engine, clock=lambda: datetime.now(timezone.utc),
        policy_revision_generator=lambda: ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId(secrets.token_hex(32)),
        authority_revision_generator=lambda: ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId(secrets.token_hex(32)))


def execute_one(kind: str, engine: Engine, request_path: Path):
    if not DatabaseReadinessProbe(engine).check().ready:
        raise CleanupRetentionPolicyOperatorUnavailable
    if kind == "retention":
        command = load_retention_request(request_path)
        result = compose_manifest_handoff_supervisor_cleanup_retention_operation(
            database_engine=engine
        ).execute(command)
        if result is None or type(result) is ManifestHandoffSupervisorCleanupRetentionOperationConflict:
            return None
        return {"operation_id": command.operation_id.value,
            "directory_id": command.directory_id.value,
            "decision_id": result.decision.decision_id.value,
            "policy_revision_id": result.evaluation.policy_revision_id.value,
            "disposition": result.evaluation.disposition.value}
    store = _store(engine)
    if kind == "bootstrap":
        command = load_bootstrap_request(request_path)
        result = store.bootstrap_cleanup_retention_policy(command)
        if result is None or type(result) is ManifestHandoffSupervisorCleanupRetentionPolicyConflict:
            return None
        return {"operation_id": command.bootstrap_id.value,
            "policy_revision_id": result.active_policy.policy.revision_id.value,
            "authority_revision_id": result.authority_set.revision_id.value}
    if kind == "policy":
        principal, command = load_policy_request(request_path)
        result = store.change_cleanup_retention_policy(principal, command)
        if result is None or type(result) is ManifestHandoffSupervisorCleanupRetentionPolicyConflict:
            return None
        if type(result) is not ChangedManifestHandoffSupervisorCleanupRetentionPolicy:
            raise CleanupRetentionPolicyOperatorUnavailable
        payload = {"operation_id": command.change_id.value, "disposition":
            "inactive" if result.active_policy is None else "active"}
        if result.active_policy is not None:
            payload["revision_id"] = result.active_policy.policy.revision_id.value
        return payload
    if kind == "lifecycle":
        principal, command = load_lifecycle_request(request_path)
        result = store.change_cleanup_retention_policy_authority(principal, command)
        operation = command.change_id.value
    else:
        command = load_recovery_request(request_path)
        result = store.recover_cleanup_retention_policy_authority(command)
        operation = command.recovery_id.value
    if result is None or type(result) is ManifestHandoffSupervisorCleanupRetentionPolicyConflict:
        return None
    if type(result) is not ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet:
        raise CleanupRetentionPolicyOperatorUnavailable
    return {"operation_id": operation, "revision_id": result.revision_id.value}


def _parser(prog):
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("--database-url-file", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--result-file", required=True, type=Path)
    return parser


def _main(kind: str, prog: str, argv=None):
    args = _parser(prog).parse_args(argv); engine = None
    try:
        database_url = _read_private(args.database_url_file).strip()
        engine = build_engine(database_url)
        result = execute_one(kind, engine, args.request)
        if result is None:
            sys.stdout.write('{"outcome":"rejected"}\n'); return 1
        _write_result(args.result_file, result)
        sys.stdout.write('{"outcome":"applied"}\n'); return 0
    except (CleanupRetentionPolicyOperatorUnavailable, ManifestHandoffRegistryUnavailable):
        sys.stderr.write('{"error":"operator_unavailable"}\n'); return 2
    except Exception:
        sys.stderr.write('{"error":"operator_unavailable"}\n'); return 2
    finally:
        if engine is not None: engine.dispose()


def bootstrap_main(argv=None): return _main("bootstrap", "liquent-supervisor-cleanup-retention-policy-bootstrap", argv)
def policy_main(argv=None): return _main("policy", "liquent-supervisor-cleanup-retention-policy-change", argv)
def lifecycle_main(argv=None): return _main("lifecycle", "liquent-supervisor-cleanup-retention-authority-lifecycle", argv)
def recovery_main(argv=None): return _main("recovery", "liquent-supervisor-cleanup-retention-authority-recovery", argv)
def retention_main(argv=None): return _main("retention", "liquent-supervisor-cleanup-retention-evaluate", argv)
