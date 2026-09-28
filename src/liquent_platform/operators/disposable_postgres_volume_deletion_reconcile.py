"""Read-only reconciliation of one PostgreSQL volume-deletion claim."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from liquent_platform.operators.disposable_postgres_reconcile import (
    _evidence_root, _observe, _owned_volume, _pairs, _timestamp,
)
from liquent_platform.operators.disposable_postgres_volume_deletion import (
    DisposablePostgresVolumeDeletionUnavailable, _binding, _claim, _existing,
    _historical_authorization,
)
from liquent_platform.operators.disposable_postgres_volume_disposition import (
    HOLD_KEYS, RECOVERY_KEYS, RETENTION_KEYS, _authorization as _disposition_authorization,
    _bound_file, _current, _decision_common, _json, _lineage, _opaque,
)
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, SHA256,
)
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner


KEYS = {
    "schema_version", "volume_deletion_reconciliation_id", "volume_deletion_id",
    "volume_deletion_claim_id", "volume_disposition_id", "retention_decision_id",
    "legal_hold_decision_id", "recovery_decision_id", "run_id", "phase",
    "source_commit", "image_ref", "compose_sha256", "retained_volume",
    "volume_deletion_authorization_sha256",
    "volume_disposition_authorization_sha256", "lineage_manifest_sha256",
    "retention_decision_sha256", "legal_hold_decision_sha256",
    "recovery_decision_sha256", "operation", "scope", "executor_id",
    "authorizer_id", "reviewer_id", "valid_from", "valid_until",
}


class DisposablePostgresVolumeDeletionReconcileUnavailable(Exception):
    code = "disposable_postgres_volume_deletion_reconcile_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresVolumeDeletionReconcileUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        _, value = _json(path, 32_768)
        if set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresVolumeDeletionReconcileUnavailable
        if (
            value["phase"] != "disposable_postgres"
            or value["operation"] != "inspect_disposable_postgres_volume_deletion"
            or value["scope"] != "data_volume_only"
        ):
            raise DisposablePostgresVolumeDeletionReconcileUnavailable
        for key in (
            "volume_deletion_reconciliation_id", "volume_deletion_id",
            "volume_deletion_claim_id", "volume_disposition_id",
            "retention_decision_id", "legal_hold_decision_id",
            "recovery_decision_id", "run_id", "executor_id", "authorizer_id",
            "reviewer_id",
        ):
            if not _opaque(value[key]):
                raise DisposablePostgresVolumeDeletionReconcileUnavailable
        if len({value["executor_id"], value["authorizer_id"], value["reviewer_id"]}) != 3:
            raise DisposablePostgresVolumeDeletionReconcileUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresVolumeDeletionReconcileUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresVolumeDeletionReconcileUnavailable
        for key in (
            "compose_sha256", "volume_deletion_authorization_sha256",
            "volume_disposition_authorization_sha256", "lineage_manifest_sha256",
            "retention_decision_sha256", "legal_hold_decision_sha256",
            "recovery_decision_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresVolumeDeletionReconcileUnavailable
        _current(value, clock=clock)
        return value
    except DisposablePostgresVolumeDeletionReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionReconcileUnavailable from None


def _historical_disposition(path: Path) -> tuple[bytes, dict]:
    try:
        raw, value = _json(path, 32_768)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        checked_raw, checked = _disposition_authorization(
            path, clock=lambda: start + (end - start) / 2,
        )
        if raw != checked_raw:
            raise DisposablePostgresVolumeDeletionReconcileUnavailable
        return raw, checked
    except DisposablePostgresVolumeDeletionReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionReconcileUnavailable from None


def _historical_decision(
    path: Path, expected: str, keys: set[str], auth: dict, volume: str,
) -> dict:
    try:
        value = _bound_file(path, expected, keys)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        _decision_common(
            value, auth, volume,
            clock=lambda: start + (end - start) / 2,
        )
        return value
    except Exception:
        raise DisposablePostgresVolumeDeletionReconcileUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_volume_deletion_reconciliation",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def reconcile_disposable_postgres_volume_deletion(
    *, docker_executable: Path, volume_disposition_file: Path,
    volume_deletion_file: Path, volume_deletion_reconciliation_file: Path,
    lineage_manifest_file: Path, retention_decision_file: Path,
    legal_hold_decision_file: Path, recovery_decision_file: Path,
    project_name: str, evidence_directory: Path, processes=None,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        processes = processes or LocalBoundedProcessRunner()
        deletion_raw, deletion = _historical_authorization(volume_deletion_file)
        current = _authorization(volume_deletion_reconciliation_file, clock=clock)
        disposition_raw, disposition = _historical_disposition(volume_disposition_file)
        volume = f"{project_name}-postgres-data"
        if (
            project_name != f"liquent-{deletion['run_id']}"
            or deletion["retained_volume"] != volume
            or current["volume_deletion_authorization_sha256"]
            != hashlib.sha256(deletion_raw).hexdigest()
            or current["volume_disposition_authorization_sha256"]
            != hashlib.sha256(disposition_raw).hexdigest()
            or any(current[key] != deletion[key] for key in (
                "volume_deletion_id", "volume_deletion_claim_id", "volume_disposition_id",
                "retention_decision_id", "legal_hold_decision_id",
                "recovery_decision_id", "run_id", "phase", "source_commit",
                "image_ref", "compose_sha256", "retained_volume",
                "volume_disposition_authorization_sha256", "lineage_manifest_sha256",
                "retention_decision_sha256", "legal_hold_decision_sha256",
                "recovery_decision_sha256", "scope",
            ))
            or deletion["operation"] != "remove_disposable_postgres_data_volume"
            or disposition["volume_disposition_id"] != current["volume_disposition_id"]
        ):
            raise DisposablePostgresVolumeDeletionReconcileUnavailable
        _lineage(
            lineage_manifest_file, current["lineage_manifest_sha256"],
            disposition, project_name,
        )
        retention = _historical_decision(
            retention_decision_file, current["retention_decision_sha256"],
            RETENTION_KEYS, disposition, volume,
        )
        hold = _historical_decision(
            legal_hold_decision_file, current["legal_hold_decision_sha256"],
            HOLD_KEYS, disposition, volume,
        )
        recovery = _historical_decision(
            recovery_decision_file, current["recovery_decision_sha256"],
            RECOVERY_KEYS, disposition, volume,
        )
        if (
            current["retention_decision_id"] != retention["retention_decision_id"]
            or current["legal_hold_decision_id"] != hold["legal_hold_decision_id"]
            or current["recovery_decision_id"] != recovery["recovery_decision_id"]
            or len({
                current["executor_id"], current["authorizer_id"], current["reviewer_id"],
                deletion["executor_id"], deletion["authorizer_id"], deletion["reviewer_id"],
                disposition["executor_id"], disposition["authorizer_id"],
                disposition["reviewer_id"], retention["authorizer_id"],
                hold["authorizer_id"], recovery["authorizer_id"],
            }) != 12
        ):
            raise DisposablePostgresVolumeDeletionReconcileUnavailable
        binding = _binding(deletion, deletion_raw)
        evidence_stem = hashlib.sha256(deletion["volume_deletion_id"].encode()).hexdigest()
        claim_stem = hashlib.sha256(deletion["volume_deletion_claim_id"].encode()).hexdigest()
        final = evidence_directory / f"postgres-volume-deletion-{evidence_stem}.json"
        claim = evidence_directory / f".postgres-volume-deletion-{claim_stem}.claim"
        root_descriptor = _evidence_root(evidence_directory)
        if _existing(final, binding):
            return _result("final_evidence_present")
        if not claim.exists():
            return _result("not_found")
        if not _claim(claim, binding):
            raise DisposablePostgresVolumeDeletionReconcileUnavailable
        docker = str(docker_executable)
        listed = _observe(processes, (
            docker, "volume", "ls", "--filter", f"name=^{volume}$",
            "--format", "{{.Name}}",
        ), maximum=65_536)
        try:
            names = listed.stdout.decode("utf-8").splitlines()
        except Exception:
            raise DisposablePostgresVolumeDeletionReconcileUnavailable from None
        if not names:
            return _result("volume_absent_evidence_missing")
        if names != [volume]:
            raise DisposablePostgresVolumeDeletionReconcileUnavailable
        observed = _observe(
            processes, (docker, "volume", "inspect", volume), maximum=1_048_576,
        )
        if _owned_volume(observed.stdout, name=volume, project=project_name):
            return _result("volume_present")
        return _result("conflict")
    except DisposablePostgresVolumeDeletionReconcileUnavailable:
        raise
    except DisposablePostgresVolumeDeletionUnavailable:
        raise DisposablePostgresVolumeDeletionReconcileUnavailable from None
    except Exception:
        raise DisposablePostgresVolumeDeletionReconcileUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        prog="liquent-disposable-postgres-volume-delete-reconcile", add_help=False,
    )
    for name in (
        "docker-executable", "volume-disposition-file", "volume-deletion-file",
        "volume-deletion-reconciliation-file", "lineage-manifest-file",
        "retention-decision-file", "legal-hold-decision-file",
        "recovery-decision-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        sys.stdout.buffer.write(reconcile_disposable_postgres_volume_deletion(
            **vars(parser.parse_args(argv)),
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
