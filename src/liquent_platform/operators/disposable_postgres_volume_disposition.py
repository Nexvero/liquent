"""Read-only disposition of one retained disposable PostgreSQL volume."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from liquent_platform.operators.disposable_postgres_reconcile import (
    _observe, _owned_volume, _pairs, _timestamp,
)
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, OPAQUE, SHA256,
)
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner


AUTH_KEYS = {
    "schema_version", "volume_disposition_id", "run_id", "phase",
    "source_commit", "image_ref", "compose_sha256", "lineage_manifest_sha256",
    "retention_decision_sha256", "legal_hold_decision_sha256",
    "recovery_decision_sha256", "operation", "executor_id", "authorizer_id",
    "reviewer_id", "valid_from", "valid_until",
}
LINEAGE_KEYS = {
    "schema_version", "run_id", "phase", "source_commit", "image_ref",
    "compose_sha256", "retained_volume", "cleanup_finalized", "later_use",
    "artifacts",
}
ARTIFACT_KEYS = {"kind", "path", "sha256"}
REQUIRED_ARTIFACTS = {
    "staging_evidence", "recovery_disposition", "cleanup_authorization",
    "cleanup_finalization_evidence",
}
RETENTION_KEYS = {
    "schema_version", "retention_decision_id", "run_id", "retained_volume",
    "policy_version", "outcome", "authorizer_id", "valid_from", "valid_until",
}
HOLD_KEYS = {
    "schema_version", "legal_hold_decision_id", "run_id", "retained_volume",
    "outcome", "authorizer_id", "valid_from", "valid_until",
}
RECOVERY_KEYS = {
    "schema_version", "recovery_decision_id", "run_id", "retained_volume",
    "policy_version", "backup_required", "backup_outcome", "backup_id",
    "backup_integrity_sha256", "restore_required", "restore_outcome",
    "restore_id", "authorizer_id", "valid_from", "valid_until",
}


class DisposablePostgresVolumeDispositionUnavailable(Exception):
    code = "disposable_postgres_volume_disposition_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresVolumeDispositionUnavailable


def _json(path: Path, maximum: int = 262_144) -> tuple[bytes, dict]:
    try:
        raw = _private_file(path, maximum)
        value = json.loads(raw, object_pairs_hook=_pairs)
        if type(value) is not dict:
            raise DisposablePostgresVolumeDispositionUnavailable
        return raw, value
    except DisposablePostgresVolumeDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDispositionUnavailable from None


def _opaque(value) -> bool:
    return type(value) is str and OPAQUE.fullmatch(value) is not None


def _current(value: dict, *, clock) -> None:
    try:
        start, end, now = (
            _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock(),
        )
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
            or not start <= now.astimezone(UTC) <= end
        ):
            raise DisposablePostgresVolumeDispositionUnavailable
    except DisposablePostgresVolumeDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDispositionUnavailable from None


def _authorization(path: Path, *, clock) -> tuple[bytes, dict]:
    raw, value = _json(path, 32_768)
    try:
        if set(value) != AUTH_KEYS or value["schema_version"] != 1:
            raise DisposablePostgresVolumeDispositionUnavailable
        if (
            value["phase"] != "disposable_postgres"
            or value["operation"] != "resolve_disposable_postgres_volume_disposition"
        ):
            raise DisposablePostgresVolumeDispositionUnavailable
        for key in (
            "volume_disposition_id", "run_id", "executor_id", "authorizer_id",
            "reviewer_id",
        ):
            if not _opaque(value[key]):
                raise DisposablePostgresVolumeDispositionUnavailable
        if len({value["executor_id"], value["authorizer_id"], value["reviewer_id"]}) != 3:
            raise DisposablePostgresVolumeDispositionUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresVolumeDispositionUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresVolumeDispositionUnavailable
        for key in (
            "compose_sha256", "lineage_manifest_sha256", "retention_decision_sha256",
            "legal_hold_decision_sha256", "recovery_decision_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresVolumeDispositionUnavailable
        _current(value, clock=clock)
        return raw, value
    except DisposablePostgresVolumeDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDispositionUnavailable from None


def _bound_file(path: Path, expected: str, keys: set[str]) -> dict:
    raw, value = _json(path)
    if hashlib.sha256(raw).hexdigest() != expected or set(value) != keys:
        raise DisposablePostgresVolumeDispositionUnavailable
    return value


def _lineage(path: Path, expected: str, auth: dict, project: str) -> dict:
    value = _bound_file(path, expected, LINEAGE_KEYS)
    volume = f"{project}-postgres-data"
    try:
        if (
            value["schema_version"] != 1 or value["phase"] != "disposable_postgres"
            or value["run_id"] != auth["run_id"]
            or value["source_commit"] != auth["source_commit"]
            or value["image_ref"] != auth["image_ref"]
            or value["compose_sha256"] != auth["compose_sha256"]
            or value["retained_volume"] != volume
            or value["cleanup_finalized"] is not True
            or type(value["later_use"]) is not bool
            or type(value["artifacts"]) is not list
            or not value["artifacts"]
        ):
            raise DisposablePostgresVolumeDispositionUnavailable
        kinds = set()
        for artifact in value["artifacts"]:
            if type(artifact) is not dict or set(artifact) != ARTIFACT_KEYS:
                raise DisposablePostgresVolumeDispositionUnavailable
            if not _opaque(artifact["kind"]) or artifact["kind"] in kinds:
                raise DisposablePostgresVolumeDispositionUnavailable
            artifact_path = Path(artifact["path"])
            if type(artifact["path"]) is not str or not artifact_path.is_absolute():
                raise DisposablePostgresVolumeDispositionUnavailable
            raw = _private_file(artifact_path, 1_048_576)
            if (
                type(artifact["sha256"]) is not str
                or SHA256.fullmatch(artifact["sha256"]) is None
                or hashlib.sha256(raw).hexdigest() != artifact["sha256"]
            ):
                raise DisposablePostgresVolumeDispositionUnavailable
            kinds.add(artifact["kind"])
        if not REQUIRED_ARTIFACTS <= kinds:
            raise DisposablePostgresVolumeDispositionUnavailable
        return value
    except DisposablePostgresVolumeDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDispositionUnavailable from None


def _decision_common(value: dict, auth: dict, volume: str, *, clock) -> None:
    if (
        value["schema_version"] != 1 or value["run_id"] != auth["run_id"]
        or value["retained_volume"] != volume or not _opaque(value["authorizer_id"])
        or value["authorizer_id"] in {
            auth["executor_id"], auth["authorizer_id"], auth["reviewer_id"],
        }
    ):
        raise DisposablePostgresVolumeDispositionUnavailable
    _current(value, clock=clock)


def _claims_closed(root: Path) -> None:
    try:
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
        if (
            metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) & 0o077
            or any(name.startswith(".postgres-cleanup-") and name.endswith(".claim")
                   for name in os.listdir(descriptor))
        ):
            raise DisposablePostgresVolumeDispositionUnavailable
    except DisposablePostgresVolumeDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDispositionUnavailable from None
    finally:
        if "descriptor" in locals():
            os.close(descriptor)


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_volume_disposition",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def resolve_disposable_postgres_volume_disposition(
    *, docker_executable: Path, volume_disposition_file: Path,
    lineage_manifest_file: Path, retention_decision_file: Path,
    legal_hold_decision_file: Path, recovery_decision_file: Path,
    project_name: str, evidence_directory: Path, processes=None,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    try:
        processes = processes or LocalBoundedProcessRunner()
        _, auth = _authorization(volume_disposition_file, clock=clock)
        if project_name != f"liquent-{auth['run_id']}":
            raise DisposablePostgresVolumeDispositionUnavailable
        lineage = _lineage(
            lineage_manifest_file, auth["lineage_manifest_sha256"], auth, project_name,
        )
        volume = lineage["retained_volume"]
        retention = _bound_file(
            retention_decision_file, auth["retention_decision_sha256"], RETENTION_KEYS,
        )
        hold = _bound_file(
            legal_hold_decision_file, auth["legal_hold_decision_sha256"], HOLD_KEYS,
        )
        recovery = _bound_file(
            recovery_decision_file, auth["recovery_decision_sha256"], RECOVERY_KEYS,
        )
        for value in (retention, hold, recovery):
            _decision_common(value, auth, volume, clock=clock)
        if len({
            retention["authorizer_id"], hold["authorizer_id"],
            recovery["authorizer_id"],
        }) != 3:
            raise DisposablePostgresVolumeDispositionUnavailable
        if (
            not _opaque(retention["retention_decision_id"])
            or not _opaque(retention["policy_version"])
            or retention["outcome"] not in {"retain", "cleared"}
            or not _opaque(hold["legal_hold_decision_id"])
            or hold["outcome"] not in {"clear", "active", "conflict"}
            or not _opaque(recovery["recovery_decision_id"])
            or not _opaque(recovery["policy_version"])
            or type(recovery["backup_required"]) is not bool
            or recovery["backup_outcome"] not in {"not_required", "verified", "pending"}
            or type(recovery["restore_required"]) is not bool
            or recovery["restore_outcome"] not in {"not_required", "verified", "pending"}
        ):
            raise DisposablePostgresVolumeDispositionUnavailable
        backup_positive = (
            not recovery["backup_required"]
            and recovery["backup_outcome"] == "not_required"
            and recovery["backup_id"] is None
            and recovery["backup_integrity_sha256"] is None
        ) or (
            recovery["backup_required"] and recovery["backup_outcome"] == "verified"
            and _opaque(recovery["backup_id"])
            and type(recovery["backup_integrity_sha256"]) is str
            and SHA256.fullmatch(recovery["backup_integrity_sha256"]) is not None
        )
        restore_positive = (
            not recovery["restore_required"]
            and recovery["restore_outcome"] == "not_required"
            and recovery["restore_id"] is None
        ) or (
            recovery["restore_required"] and recovery["restore_outcome"] == "verified"
            and _opaque(recovery["restore_id"])
        )
        _claims_closed(evidence_directory)
        observed = _observe(
            processes, (str(docker_executable), "volume", "inspect", volume),
            maximum=1_048_576,
        )
        if not observed.stdout:
            return _result("investigation_required")
        if not _owned_volume(observed.stdout, name=volume, project=project_name):
            return _result("investigation_required")
        if lineage["later_use"] or retention["outcome"] == "retain" or hold["outcome"] == "active":
            return _result("retain")
        if hold["outcome"] == "conflict":
            return _result("investigation_required")
        if not backup_positive or not restore_positive:
            return _result("retain")
        return _result("deletion_review_eligible")
    except DisposablePostgresVolumeDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDispositionUnavailable from None


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        prog="liquent-disposable-postgres-volume-disposition", add_help=False,
    )
    for name in (
        "docker-executable", "volume-disposition-file", "lineage-manifest-file",
        "retention-decision-file", "legal-hold-decision-file",
        "recovery-decision-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(resolve_disposable_postgres_volume_disposition(**value))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
