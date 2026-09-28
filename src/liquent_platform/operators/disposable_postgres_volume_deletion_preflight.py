"""Read-only preflight for one authorized PostgreSQL volume deletion."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

from liquent_platform.operators.disposable_postgres_reconcile import _pairs
from liquent_platform.operators.disposable_postgres_volume_disposition import (
    HOLD_KEYS, RECOVERY_KEYS, RETENTION_KEYS, DisposablePostgresVolumeDispositionUnavailable,
    _authorization as _disposition_authorization, _bound_file, _current, _json,
    _opaque, resolve_disposable_postgres_volume_disposition,
)
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, SHA256,
)


KEYS = {
    "schema_version", "volume_deletion_id", "volume_deletion_claim_id",
    "volume_disposition_id", "retention_decision_id", "legal_hold_decision_id",
    "recovery_decision_id", "run_id", "phase", "source_commit", "image_ref",
    "compose_sha256", "retained_volume", "volume_disposition_authorization_sha256",
    "lineage_manifest_sha256", "retention_decision_sha256",
    "legal_hold_decision_sha256", "recovery_decision_sha256", "operation",
    "scope", "executor_id", "authorizer_id", "reviewer_id", "valid_from",
    "valid_until",
}


class DisposablePostgresVolumeDeletionPreflightUnavailable(Exception):
    code = "disposable_postgres_volume_deletion_preflight_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresVolumeDeletionPreflightUnavailable


def _authorization(path: Path, *, clock) -> tuple[bytes, dict]:
    try:
        raw, value = _json(path, 32_768)
        if set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresVolumeDeletionPreflightUnavailable
        if (
            value["phase"] != "disposable_postgres"
            or value["operation"] != "remove_disposable_postgres_data_volume"
            or value["scope"] != "data_volume_only"
        ):
            raise DisposablePostgresVolumeDeletionPreflightUnavailable
        for key in (
            "volume_deletion_id", "volume_deletion_claim_id", "volume_disposition_id",
            "retention_decision_id", "legal_hold_decision_id", "recovery_decision_id",
            "run_id", "executor_id", "authorizer_id", "reviewer_id",
        ):
            if not _opaque(value[key]):
                raise DisposablePostgresVolumeDeletionPreflightUnavailable
        if len({value["executor_id"], value["authorizer_id"], value["reviewer_id"]}) != 3:
            raise DisposablePostgresVolumeDeletionPreflightUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresVolumeDeletionPreflightUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresVolumeDeletionPreflightUnavailable
        for key in (
            "compose_sha256", "volume_disposition_authorization_sha256",
            "lineage_manifest_sha256", "retention_decision_sha256",
            "legal_hold_decision_sha256", "recovery_decision_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresVolumeDeletionPreflightUnavailable
        _current(value, clock=clock)
        return raw, value
    except DisposablePostgresVolumeDeletionPreflightUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionPreflightUnavailable from None


def _volume_claims_absent(root: Path) -> None:
    descriptor = None
    try:
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
            raise DisposablePostgresVolumeDeletionPreflightUnavailable
        if any(
            name.startswith(".postgres-volume-deletion-") and name.endswith(".claim")
            for name in os.listdir(descriptor)
        ):
            raise DisposablePostgresVolumeDeletionPreflightUnavailable
    except DisposablePostgresVolumeDeletionPreflightUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionPreflightUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_volume_deletion_preflight",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def preflight_disposable_postgres_volume_deletion(
    *, docker_executable: Path, volume_disposition_file: Path,
    volume_deletion_file: Path, lineage_manifest_file: Path,
    retention_decision_file: Path, legal_hold_decision_file: Path,
    recovery_decision_file: Path, project_name: str, evidence_directory: Path,
    processes=None, clock=lambda: datetime.now(UTC),
) -> bytes:
    try:
        disposition_raw, disposition = _disposition_authorization(
            volume_disposition_file, clock=clock,
        )
        _, deletion = _authorization(volume_deletion_file, clock=clock)
        retention = _bound_file(
            retention_decision_file, deletion["retention_decision_sha256"], RETENTION_KEYS,
        )
        hold = _bound_file(
            legal_hold_decision_file, deletion["legal_hold_decision_sha256"], HOLD_KEYS,
        )
        recovery = _bound_file(
            recovery_decision_file, deletion["recovery_decision_sha256"], RECOVERY_KEYS,
        )
        volume = f"{project_name}-postgres-data"
        if (
            project_name != f"liquent-{deletion['run_id']}"
            or deletion["retained_volume"] != volume
            or deletion["volume_disposition_authorization_sha256"]
            != hashlib.sha256(disposition_raw).hexdigest()
            or deletion["volume_disposition_id"] != disposition["volume_disposition_id"]
            or deletion["lineage_manifest_sha256"] != disposition["lineage_manifest_sha256"]
            or deletion["retention_decision_sha256"] != disposition["retention_decision_sha256"]
            or deletion["legal_hold_decision_sha256"] != disposition["legal_hold_decision_sha256"]
            or deletion["recovery_decision_sha256"] != disposition["recovery_decision_sha256"]
            or deletion["retention_decision_id"] != retention["retention_decision_id"]
            or deletion["legal_hold_decision_id"] != hold["legal_hold_decision_id"]
            or deletion["recovery_decision_id"] != recovery["recovery_decision_id"]
            or any(deletion[key] != disposition[key] for key in (
                "run_id", "source_commit", "image_ref", "compose_sha256",
            ))
        ):
            raise DisposablePostgresVolumeDeletionPreflightUnavailable
        all_identities = {
            deletion["executor_id"], deletion["authorizer_id"], deletion["reviewer_id"],
            disposition["executor_id"], disposition["authorizer_id"],
            disposition["reviewer_id"], retention["authorizer_id"],
            hold["authorizer_id"], recovery["authorizer_id"],
        }
        if len(all_identities) != 9:
            raise DisposablePostgresVolumeDeletionPreflightUnavailable
        _volume_claims_absent(evidence_directory)
        resolved = resolve_disposable_postgres_volume_disposition(
            docker_executable=docker_executable,
            volume_disposition_file=volume_disposition_file,
            lineage_manifest_file=lineage_manifest_file,
            retention_decision_file=retention_decision_file,
            legal_hold_decision_file=legal_hold_decision_file,
            recovery_decision_file=recovery_decision_file,
            project_name=project_name, evidence_directory=evidence_directory,
            processes=processes, clock=clock,
        )
        value = json.loads(resolved, object_pairs_hook=_pairs)
        if (
            type(value) is not dict
            or set(value) != {"schema_version", "operation", "outcome"}
            or value["schema_version"] != 1
            or value["operation"] != "disposable_postgres_volume_disposition"
            or value["outcome"] not in {
                "retain", "deletion_review_eligible", "investigation_required",
            }
        ):
            raise DisposablePostgresVolumeDeletionPreflightUnavailable
        return _result({
            "deletion_review_eligible": "ready", "retain": "rejected",
            "investigation_required": "investigation_required",
        }[value["outcome"]])
    except DisposablePostgresVolumeDeletionPreflightUnavailable:
        raise
    except DisposablePostgresVolumeDispositionUnavailable:
        raise DisposablePostgresVolumeDeletionPreflightUnavailable from None
    except Exception:
        raise DisposablePostgresVolumeDeletionPreflightUnavailable from None


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        prog="liquent-disposable-postgres-volume-deletion-preflight", add_help=False,
    )
    for name in (
        "docker-executable", "volume-disposition-file", "volume-deletion-file",
        "lineage-manifest-file", "retention-decision-file",
        "legal-hold-decision-file", "recovery-decision-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        sys.stdout.buffer.write(preflight_disposable_postgres_volume_deletion(
            **vars(parser.parse_args(argv)),
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
