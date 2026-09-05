"""Read-only reconciliation of a PostgreSQL volume-deletion continuation claim."""

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
    DisposablePostgresVolumeDeletionUnavailable, _binding as _deletion_binding,
    _claim as _deletion_claim, _existing as _deletion_evidence,
    _historical_authorization,
)
from liquent_platform.operators.disposable_postgres_volume_deletion_continue import (
    KEYS as CONTINUATION_KEYS,
    DisposablePostgresVolumeDeletionContinueUnavailable,
    _authorization as _continuation_authorization, _binding, _claim, _existing,
)
from liquent_platform.operators.disposable_postgres_volume_deletion_finalize import (
    DisposablePostgresVolumeDeletionFinalizeUnavailable,
    _binding as _finalization_binding, _existing as _finalization_evidence,
    _historical_reconciliation,
)
from liquent_platform.operators.disposable_postgres_volume_disposition import (
    _current, _json, _opaque,
)
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, SHA256,
)
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner


KEYS = (
    CONTINUATION_KEYS
    - {"operation", "executor_id", "authorizer_id", "reviewer_id",
       "valid_from", "valid_until"}
    | {"volume_deletion_continuation_reconciliation_id",
       "volume_deletion_continuation_authorization_sha256", "operation",
       "executor_id", "authorizer_id", "reviewer_id", "valid_from", "valid_until"}
)


class DisposablePostgresVolumeDeletionContinueReconcileUnavailable(Exception):
    code = "disposable_postgres_volume_deletion_continue_reconcile_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        _, value = _json(path, 32_768)
        if set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        if (
            value["phase"] != "disposable_postgres"
            or value["operation"]
            != "inspect_disposable_postgres_volume_deletion_continuation"
            or value["scope"] != "data_volume_only"
        ):
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        for key in (
            "volume_deletion_continuation_reconciliation_id",
            "volume_deletion_continuation_id",
            "volume_deletion_continuation_claim_id",
            "volume_deletion_finalization_id", "volume_deletion_reconciliation_id",
            "volume_deletion_id", "volume_deletion_claim_id", "volume_disposition_id",
            "retention_decision_id", "legal_hold_decision_id", "recovery_decision_id",
            "run_id", "executor_id", "authorizer_id", "reviewer_id",
        ):
            if not _opaque(value[key]):
                raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        if len({value["executor_id"], value["authorizer_id"], value["reviewer_id"]}) != 3:
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        for key in (
            "compose_sha256", "volume_deletion_authorization_sha256",
            "volume_disposition_authorization_sha256", "lineage_manifest_sha256",
            "retention_decision_sha256", "legal_hold_decision_sha256",
            "recovery_decision_sha256",
            "volume_deletion_reconciliation_authorization_sha256",
            "volume_deletion_finalization_authorization_sha256",
            "volume_deletion_continuation_authorization_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        _current(value, clock=clock)
        return value
    except DisposablePostgresVolumeDeletionContinueReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable from None


def _historical_continuation(path: Path) -> tuple[bytes, dict]:
    try:
        raw, value = _json(path, 32_768)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        checked_raw, checked = _continuation_authorization(
            path, clock=lambda: start + (end - start) / 2,
        )
        if checked_raw != raw:
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        return raw, checked
    except DisposablePostgresVolumeDeletionContinueReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_volume_deletion_continuation_reconciliation",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def reconcile_disposable_postgres_volume_deletion_continuation(
    *, docker_executable: Path, volume_disposition_file: Path,
    volume_deletion_file: Path, volume_deletion_reconciliation_file: Path,
    volume_deletion_finalization_file: Path,
    volume_deletion_continuation_file: Path,
    volume_deletion_continuation_reconciliation_file: Path,
    lineage_manifest_file: Path, retention_decision_file: Path,
    legal_hold_decision_file: Path, recovery_decision_file: Path,
    project_name: str, evidence_directory: Path, processes=None,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        processes = processes or LocalBoundedProcessRunner()
        deletion_raw, deletion = _historical_authorization(volume_deletion_file)
        reconciliation_raw, _ = _historical_reconciliation(
            volume_deletion_reconciliation_file,
        )
        continuation_raw, previous = _historical_continuation(
            volume_deletion_continuation_file,
        )
        current = _authorization(
            volume_deletion_continuation_reconciliation_file, clock=clock,
        )
        compare = CONTINUATION_KEYS - {
            "schema_version", "operation", "executor_id", "authorizer_id",
            "reviewer_id", "valid_from", "valid_until",
        }
        if (
            project_name != f"liquent-{current['run_id']}"
            or current["retained_volume"] != f"{project_name}-postgres-data"
            or current["volume_deletion_continuation_authorization_sha256"]
            != hashlib.sha256(continuation_raw).hexdigest()
            or current["volume_deletion_reconciliation_authorization_sha256"]
            != hashlib.sha256(reconciliation_raw).hexdigest()
            or any(current[key] != previous[key] for key in compare)
            or len({
                current["executor_id"], current["authorizer_id"], current["reviewer_id"],
                previous["executor_id"], previous["authorizer_id"], previous["reviewer_id"],
                deletion["executor_id"], deletion["authorizer_id"], deletion["reviewer_id"],
            }) != 9
        ):
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        binding = _binding(previous, continuation_raw)
        deletion_binding = _deletion_binding(deletion, deletion_raw)
        evidence_stem = hashlib.sha256(
            current["volume_deletion_continuation_id"].encode(),
        ).hexdigest()
        claim_stem = hashlib.sha256(
            current["volume_deletion_continuation_claim_id"].encode(),
        ).hexdigest()
        original_claim_stem = hashlib.sha256(
            current["volume_deletion_claim_id"].encode(),
        ).hexdigest()
        deletion_stem = hashlib.sha256(current["volume_deletion_id"].encode()).hexdigest()
        finalization_stem = hashlib.sha256(
            current["volume_deletion_finalization_id"].encode(),
        ).hexdigest()
        evidence = evidence_directory / f"postgres-volume-deletion-continuation-{evidence_stem}.json"
        claim = evidence_directory / f".postgres-volume-deletion-continuation-{claim_stem}.claim"
        original_claim = evidence_directory / f".postgres-volume-deletion-{original_claim_stem}.claim"
        deletion_evidence = evidence_directory / f"postgres-volume-deletion-{deletion_stem}.json"
        finalization_evidence = evidence_directory / f"postgres-volume-deletion-finalization-{finalization_stem}.json"
        root_descriptor = _evidence_root(evidence_directory)
        if _existing(evidence, binding):
            return _result("continuation_evidence_present")
        if not claim.exists():
            return _result("not_found")
        if not _claim(claim, binding):
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        if deletion_evidence.exists():
            if not _deletion_evidence(deletion_evidence, deletion_binding):
                raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
            return _result("conflict")
        finalization_binding = _finalization_binding(
            previous, volume_deletion_finalization_file,
        )
        if finalization_evidence.exists():
            if _finalization_evidence(finalization_evidence, finalization_binding) is None:
                raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
            return _result("conflict")
        if not original_claim.exists():
            return _result("conflict")
        if not _deletion_claim(original_claim, deletion_binding):
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        docker, volume = str(docker_executable), current["retained_volume"]
        listed = _observe(processes, (
            docker, "volume", "ls", "--filter", f"name=^{volume}$",
            "--format", "{{.Name}}",
        ), maximum=65_536)
        try:
            names = listed.stdout.decode("utf-8").splitlines()
        except Exception:
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable from None
        if not names:
            return _result("volume_absent_evidence_missing")
        if names != [volume]:
            raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable
        observed = _observe(
            processes, (docker, "volume", "inspect", volume), maximum=1_048_576,
        )
        if _owned_volume(observed.stdout, name=volume, project=project_name):
            return _result("volume_present")
        return _result("conflict")
    except DisposablePostgresVolumeDeletionContinueReconcileUnavailable:
        raise
    except (
        DisposablePostgresVolumeDeletionUnavailable,
        DisposablePostgresVolumeDeletionContinueUnavailable,
        DisposablePostgresVolumeDeletionFinalizeUnavailable,
    ):
        raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable from None
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueReconcileUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        prog="liquent-disposable-postgres-volume-delete-continue-reconcile",
        add_help=False,
    )
    for name in (
        "docker-executable", "volume-disposition-file", "volume-deletion-file",
        "volume-deletion-reconciliation-file", "volume-deletion-finalization-file",
        "volume-deletion-continuation-file",
        "volume-deletion-continuation-reconciliation-file",
        "lineage-manifest-file", "retention-decision-file",
        "legal-hold-decision-file", "recovery-decision-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        sys.stdout.buffer.write(
            reconcile_disposable_postgres_volume_deletion_continuation(
                **vars(parser.parse_args(argv)),
            )
        )
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
