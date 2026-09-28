"""Evidence-first finalization of a PostgreSQL volume-deletion continuation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

from liquent_platform.operators.disposable_postgres_reconcile import (
    _evidence_root, _pairs, _timestamp,
)
from liquent_platform.operators.disposable_postgres_volume_deletion import (
    DisposablePostgresVolumeDeletionUnavailable, _binding as _deletion_binding,
    _claim as _deletion_claim, _historical_authorization,
)
from liquent_platform.operators.disposable_postgres_volume_deletion_continue import (
    DisposablePostgresVolumeDeletionContinueUnavailable,
    _authorization as _continuation_authorization, _binding as _claim_binding,
    _claim,
)
from liquent_platform.operators.disposable_postgres_volume_deletion_continue_reconcile import (
    KEYS as RECONCILIATION_KEYS,
    DisposablePostgresVolumeDeletionContinueReconcileUnavailable,
    _authorization as _reconciliation_authorization,
    reconcile_disposable_postgres_volume_deletion_continuation,
)
from liquent_platform.operators.disposable_postgres_volume_disposition import (
    _current, _json, _opaque,
)
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, SHA256,
)


KEYS = (
    RECONCILIATION_KEYS
    - {"volume_deletion_continuation_reconciliation_id", "operation",
       "executor_id", "authorizer_id", "reviewer_id", "valid_from", "valid_until"}
    | {"volume_deletion_continuation_finalization_id",
       "volume_deletion_continuation_reconciliation_id",
       "volume_deletion_continuation_reconciliation_authorization_sha256",
       "operation", "executor_id", "authorizer_id", "reviewer_id",
       "valid_from", "valid_until"}
)
FINAL = {
    "continuation_evidence_present": "continuation_evidence_confirmed",
    "volume_absent_evidence_missing":
        "volume_removal_ready_for_deletion_finalization",
}


class DisposablePostgresVolumeDeletionContinueFinalizeUnavailable(Exception):
    code = "disposable_postgres_volume_deletion_continue_finalize_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        _, value = _json(path, 32_768)
        if set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        if (
            value["phase"] != "disposable_postgres"
            or value["operation"]
            != "finalize_disposable_postgres_volume_deletion_continuation"
            or value["scope"] != "data_volume_only"
        ):
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        for key in (
            "volume_deletion_continuation_finalization_id",
            "volume_deletion_continuation_reconciliation_id",
            "volume_deletion_continuation_id",
            "volume_deletion_continuation_claim_id",
            "volume_deletion_finalization_id", "volume_deletion_reconciliation_id",
            "volume_deletion_id", "volume_deletion_claim_id", "volume_disposition_id",
            "retention_decision_id", "legal_hold_decision_id", "recovery_decision_id",
            "run_id", "executor_id", "authorizer_id", "reviewer_id",
        ):
            if not _opaque(value[key]):
                raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        if len({value["executor_id"], value["authorizer_id"], value["reviewer_id"]}) != 3:
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        for key in (
            "compose_sha256", "volume_deletion_authorization_sha256",
            "volume_disposition_authorization_sha256", "lineage_manifest_sha256",
            "retention_decision_sha256", "legal_hold_decision_sha256",
            "recovery_decision_sha256",
            "volume_deletion_reconciliation_authorization_sha256",
            "volume_deletion_finalization_authorization_sha256",
            "volume_deletion_continuation_authorization_sha256",
            "volume_deletion_continuation_reconciliation_authorization_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        _current(value, clock=clock)
        return value
    except DisposablePostgresVolumeDeletionContinueFinalizeUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable from None


def _historical_reconciliation(path: Path) -> tuple[bytes, dict]:
    try:
        raw, value = _json(path, 32_768)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        checked = _reconciliation_authorization(
            path, clock=lambda: start + (end - start) / 2,
        )
        return raw, checked
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable from None


def _historical_continuation(path: Path) -> tuple[bytes, dict]:
    try:
        raw, value = _json(path, 32_768)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        checked_raw, checked = _continuation_authorization(
            path, clock=lambda: start + (end - start) / 2,
        )
        if checked_raw != raw:
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        return raw, checked
    except DisposablePostgresVolumeDeletionContinueFinalizeUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable from None


def _binding(current: dict, finalization_file: Path) -> dict:
    return {
        "schema_version": 1,
        **{key: current[key] for key in KEYS if key not in {
            "schema_version", "valid_from", "valid_until",
        }},
        "volume_deletion_continuation_finalization_authorization_sha256":
            hashlib.sha256(_json(finalization_file, 32_768)[0]).hexdigest(),
    }


def _existing(path: Path, binding: dict) -> str | None:
    try:
        if not path.exists():
            return None
        metadata = path.stat(follow_symlinks=False)
        value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or type(value) is not dict
            or set(value) != set(binding) | {"observed_state", "outcome", "completed_at"}
            or any(value[key] != expected for key, expected in binding.items())
            or value["observed_state"] not in FINAL
            or value["outcome"] != FINAL[value["observed_state"]]
            or type(value["completed_at"]) is not str
            or datetime.fromisoformat(value["completed_at"].replace("Z", "+00:00")).tzinfo is None
        ):
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        return value["outcome"]
    except DisposablePostgresVolumeDeletionContinueFinalizeUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable from None


def _write(root: Path, root_descriptor: int, final: Path, record: dict, binding: dict) -> None:
    temporary = root / f".{final.stem}-{os.getpid()}.tmp"
    descriptor = None
    try:
        content = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
        )
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            if written < 1:
                raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.link(temporary, final)
        temporary.unlink()
        os.fsync(root_descriptor)
        if _existing(final, binding) != record["outcome"]:
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
    except DisposablePostgresVolumeDeletionContinueFinalizeUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _release_claim(path: Path, binding: dict, root_descriptor: int) -> None:
    try:
        if not path.exists():
            return
        if not _claim(path, binding):
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        os.unlink(path)
        os.fsync(root_descriptor)
    except DisposablePostgresVolumeDeletionContinueFinalizeUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_volume_deletion_continuation_finalization",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def finalize_disposable_postgres_volume_deletion_continuation(
    *, docker_executable: Path, volume_disposition_file: Path,
    volume_deletion_file: Path, volume_deletion_reconciliation_file: Path,
    volume_deletion_finalization_file: Path,
    volume_deletion_continuation_file: Path,
    volume_deletion_continuation_reconciliation_file: Path,
    volume_deletion_continuation_finalization_file: Path,
    lineage_manifest_file: Path, retention_decision_file: Path,
    legal_hold_decision_file: Path, recovery_decision_file: Path,
    project_name: str, evidence_directory: Path, processes=None,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        deletion_raw, deletion = _historical_authorization(volume_deletion_file)
        continuation_raw, continuation = _historical_continuation(
            volume_deletion_continuation_file,
        )
        reconciliation_raw, previous = _historical_reconciliation(
            volume_deletion_continuation_reconciliation_file,
        )
        current = _authorization(
            volume_deletion_continuation_finalization_file, clock=clock,
        )
        compare = RECONCILIATION_KEYS - {
            "schema_version", "operation", "executor_id", "authorizer_id",
            "reviewer_id", "valid_from", "valid_until",
        }
        if (
            project_name != f"liquent-{current['run_id']}"
            or current["retained_volume"] != f"{project_name}-postgres-data"
            or current["volume_deletion_continuation_reconciliation_authorization_sha256"]
            != hashlib.sha256(reconciliation_raw).hexdigest()
            or any(current[key] != previous[key] for key in compare)
            or len({
                current["executor_id"], current["authorizer_id"], current["reviewer_id"],
                previous["executor_id"], previous["authorizer_id"], previous["reviewer_id"],
                continuation["executor_id"], continuation["authorizer_id"],
                continuation["reviewer_id"], deletion["executor_id"],
                deletion["authorizer_id"], deletion["reviewer_id"],
            }) != 12
        ):
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        binding = _binding(current, volume_deletion_continuation_finalization_file)
        claim_binding = _claim_binding(continuation, continuation_raw)
        deletion_binding = _deletion_binding(deletion, deletion_raw)
        final_stem = hashlib.sha256(
            current["volume_deletion_continuation_finalization_id"].encode(),
        ).hexdigest()
        claim_stem = hashlib.sha256(
            current["volume_deletion_continuation_claim_id"].encode(),
        ).hexdigest()
        original_claim_stem = hashlib.sha256(
            current["volume_deletion_claim_id"].encode(),
        ).hexdigest()
        final = evidence_directory / f"postgres-volume-deletion-continuation-finalization-{final_stem}.json"
        claim = evidence_directory / f".postgres-volume-deletion-continuation-{claim_stem}.claim"
        original_claim = evidence_directory / f".postgres-volume-deletion-{original_claim_stem}.claim"
        root_descriptor = _evidence_root(evidence_directory)
        existing = _existing(final, binding)
        if existing is not None:
            _release_claim(claim, claim_binding, root_descriptor)
            return _result(existing)
        raw = reconcile_disposable_postgres_volume_deletion_continuation(
            docker_executable=docker_executable,
            volume_disposition_file=volume_disposition_file,
            volume_deletion_file=volume_deletion_file,
            volume_deletion_reconciliation_file=volume_deletion_reconciliation_file,
            volume_deletion_finalization_file=volume_deletion_finalization_file,
            volume_deletion_continuation_file=volume_deletion_continuation_file,
            volume_deletion_continuation_reconciliation_file=
                volume_deletion_continuation_reconciliation_file,
            lineage_manifest_file=lineage_manifest_file,
            retention_decision_file=retention_decision_file,
            legal_hold_decision_file=legal_hold_decision_file,
            recovery_decision_file=recovery_decision_file,
            project_name=project_name, evidence_directory=evidence_directory,
            processes=processes, clock=clock,
        )
        observed = json.loads(raw, object_pairs_hook=_pairs)
        if (
            type(observed) is not dict
            or set(observed) != {"schema_version", "operation", "outcome"}
            or observed["schema_version"] != 1
            or observed["operation"]
            != "disposable_postgres_volume_deletion_continuation_reconciliation"
            or observed["outcome"] not in {
                "continuation_evidence_present", "not_found", "volume_present",
                "volume_absent_evidence_missing", "conflict",
            }
        ):
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        state = observed["outcome"]
        if state == "not_found":
            return _result("not_found")
        if state in {"volume_present", "conflict"}:
            return _result("investigation_required")
        if not original_claim.exists():
            return _result("investigation_required")
        if not _deletion_claim(original_claim, deletion_binding):
            raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable
        outcome = FINAL[state]
        _write(evidence_directory, root_descriptor, final, {
            **binding, "observed_state": state, "outcome": outcome,
            "completed_at": clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
        }, binding)
        _release_claim(claim, claim_binding, root_descriptor)
        return _result(outcome)
    except DisposablePostgresVolumeDeletionContinueFinalizeUnavailable:
        raise
    except (
        DisposablePostgresVolumeDeletionUnavailable,
        DisposablePostgresVolumeDeletionContinueUnavailable,
        DisposablePostgresVolumeDeletionContinueReconcileUnavailable,
    ):
        raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable from None
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueFinalizeUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        prog="liquent-disposable-postgres-volume-delete-continue-finalize",
        add_help=False,
    )
    for name in (
        "docker-executable", "volume-disposition-file", "volume-deletion-file",
        "volume-deletion-reconciliation-file", "volume-deletion-finalization-file",
        "volume-deletion-continuation-file",
        "volume-deletion-continuation-reconciliation-file",
        "volume-deletion-continuation-finalization-file",
        "lineage-manifest-file", "retention-decision-file",
        "legal-hold-decision-file", "recovery-decision-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        sys.stdout.buffer.write(
            finalize_disposable_postgres_volume_deletion_continuation(
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
