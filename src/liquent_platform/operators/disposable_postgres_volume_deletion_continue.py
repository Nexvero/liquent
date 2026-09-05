"""Owner-controlled continuation of one PostgreSQL volume deletion."""

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
    _evidence_root, _observe, _owned_volume, _pairs, _timestamp,
)
from liquent_platform.operators.disposable_postgres_volume_deletion import (
    DisposablePostgresVolumeDeletionUnavailable, _binding as _deletion_binding,
    _claim as _deletion_claim, _historical_authorization,
)
from liquent_platform.operators.disposable_postgres_volume_deletion_finalize import (
    KEYS as FINALIZATION_KEYS,
    DisposablePostgresVolumeDeletionFinalizeUnavailable,
    _authorization as _finalization_authorization,
    finalize_disposable_postgres_volume_deletion,
)
from liquent_platform.operators.disposable_postgres_volume_disposition import (
    _current, _json, _opaque,
)
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, SHA256,
)
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner


KEYS = (
    FINALIZATION_KEYS
    - {"volume_deletion_finalization_id", "operation", "executor_id",
       "authorizer_id", "reviewer_id", "valid_from", "valid_until"}
    | {"volume_deletion_continuation_id", "volume_deletion_continuation_claim_id",
       "volume_deletion_finalization_id",
       "volume_deletion_finalization_authorization_sha256", "operation",
       "executor_id", "authorizer_id", "reviewer_id", "valid_from", "valid_until"}
)


class DisposablePostgresVolumeDeletionContinueUnavailable(Exception):
    code = "disposable_postgres_volume_deletion_continue_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresVolumeDeletionContinueUnavailable


def _authorization(path: Path, *, clock) -> tuple[bytes, dict]:
    try:
        raw, value = _json(path, 32_768)
        if set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        if (
            value["phase"] != "disposable_postgres"
            or value["operation"] != "continue_disposable_postgres_volume_deletion"
            or value["scope"] != "data_volume_only"
        ):
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        for key in (
            "volume_deletion_continuation_id",
            "volume_deletion_continuation_claim_id",
            "volume_deletion_finalization_id", "volume_deletion_reconciliation_id",
            "volume_deletion_id", "volume_deletion_claim_id", "volume_disposition_id",
            "retention_decision_id", "legal_hold_decision_id", "recovery_decision_id",
            "run_id", "executor_id", "authorizer_id", "reviewer_id",
        ):
            if not _opaque(value[key]):
                raise DisposablePostgresVolumeDeletionContinueUnavailable
        if len({value["executor_id"], value["authorizer_id"], value["reviewer_id"]}) != 3:
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        for key in (
            "compose_sha256", "volume_deletion_authorization_sha256",
            "volume_disposition_authorization_sha256", "lineage_manifest_sha256",
            "retention_decision_sha256", "legal_hold_decision_sha256",
            "recovery_decision_sha256",
            "volume_deletion_reconciliation_authorization_sha256",
            "volume_deletion_finalization_authorization_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresVolumeDeletionContinueUnavailable
        _current(value, clock=clock)
        return raw, value
    except DisposablePostgresVolumeDeletionContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueUnavailable from None


def _historical_finalization(path: Path) -> tuple[bytes, dict]:
    try:
        raw, value = _json(path, 32_768)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        checked = _finalization_authorization(
            path, clock=lambda: start + (end - start) / 2,
        )
        return raw, checked
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueUnavailable from None


def _binding(current: dict, authorization_raw: bytes) -> dict:
    return {
        "schema_version": 1,
        **{key: current[key] for key in KEYS if key not in {
            "schema_version", "valid_from", "valid_until",
        }},
        "volume_deletion_continuation_authorization_sha256": hashlib.sha256(
            authorization_raw,
        ).hexdigest(),
    }


def _claim(path: Path, binding: dict) -> bool:
    try:
        if not path.exists():
            return False
        metadata = path.stat(follow_symlinks=False)
        value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or type(value) is not dict or set(value) != set(binding) | {"started_at"}
            or any(value[key] != expected for key, expected in binding.items())
            or type(value["started_at"]) is not str
            or datetime.fromisoformat(value["started_at"].replace("Z", "+00:00")).tzinfo is None
        ):
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        return True
    except DisposablePostgresVolumeDeletionContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueUnavailable from None


def _create_claim(path: Path, binding: dict, started_at: str, root_descriptor: int) -> None:
    descriptor = None
    try:
        content = (json.dumps(
            {**binding, "started_at": started_at}, sort_keys=True, separators=(",", ":"),
        ) + "\n").encode()
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
        )
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            if written < 1:
                raise DisposablePostgresVolumeDeletionContinueUnavailable
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.fsync(root_descriptor)
        if not _claim(path, binding):
            raise DisposablePostgresVolumeDeletionContinueUnavailable
    except DisposablePostgresVolumeDeletionContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _existing(path: Path, binding: dict) -> bool:
    try:
        if not path.exists():
            return False
        metadata = path.stat(follow_symlinks=False)
        value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or type(value) is not dict
            or set(value) != set(binding) | {
                "executed_step", "absence_confirmed", "started_at", "completed_at",
                "outcome",
            }
            or any(value[key] != expected for key, expected in binding.items())
            or value["executed_step"] != "remove_exact_volume_once"
            or value["absence_confirmed"] is not True
            or value["outcome"] != "volume_removal_pending_finalization"
        ):
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        for key in ("started_at", "completed_at"):
            if (
                type(value[key]) is not str
                or datetime.fromisoformat(value[key].replace("Z", "+00:00")).tzinfo is None
            ):
                raise DisposablePostgresVolumeDeletionContinueUnavailable
        return True
    except DisposablePostgresVolumeDeletionContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueUnavailable from None


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
                raise DisposablePostgresVolumeDeletionContinueUnavailable
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.link(temporary, final)
        temporary.unlink()
        os.fsync(root_descriptor)
        if not _existing(final, binding):
            raise DisposablePostgresVolumeDeletionContinueUnavailable
    except DisposablePostgresVolumeDeletionContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueUnavailable from None
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
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        os.unlink(path)
        os.fsync(root_descriptor)
    except DisposablePostgresVolumeDeletionContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_volume_deletion_continuation",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def continue_disposable_postgres_volume_deletion(
    *, docker_executable: Path, volume_disposition_file: Path,
    volume_deletion_file: Path, volume_deletion_reconciliation_file: Path,
    volume_deletion_finalization_file: Path,
    volume_deletion_continuation_file: Path, lineage_manifest_file: Path,
    retention_decision_file: Path, legal_hold_decision_file: Path,
    recovery_decision_file: Path, project_name: str, evidence_directory: Path,
    processes=None, clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        processes = processes or LocalBoundedProcessRunner()
        deletion_raw, deletion = _historical_authorization(volume_deletion_file)
        finalization_raw, previous = _historical_finalization(
            volume_deletion_finalization_file,
        )
        authorization_raw, current = _authorization(
            volume_deletion_continuation_file, clock=clock,
        )
        compare = FINALIZATION_KEYS - {
            "schema_version", "operation", "executor_id", "authorizer_id",
            "reviewer_id", "valid_from", "valid_until",
        }
        if (
            project_name != f"liquent-{current['run_id']}"
            or current["retained_volume"] != f"{project_name}-postgres-data"
            or current["volume_deletion_finalization_authorization_sha256"]
            != hashlib.sha256(finalization_raw).hexdigest()
            or any(current[key] != previous[key] for key in compare)
            or len({
                current["executor_id"], current["authorizer_id"], current["reviewer_id"],
                previous["executor_id"], previous["authorizer_id"], previous["reviewer_id"],
                deletion["executor_id"], deletion["authorizer_id"], deletion["reviewer_id"],
            }) != 9
        ):
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        binding = _binding(current, authorization_raw)
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
        final = evidence_directory / f"postgres-volume-deletion-continuation-{evidence_stem}.json"
        claim = evidence_directory / f".postgres-volume-deletion-continuation-{claim_stem}.claim"
        original_claim = evidence_directory / f".postgres-volume-deletion-{original_claim_stem}.claim"
        root_descriptor = _evidence_root(evidence_directory)
        if _existing(final, binding):
            _release_claim(claim, binding, root_descriptor)
            return _result("volume_removal_pending_finalization")
        raw = finalize_disposable_postgres_volume_deletion(
            docker_executable=docker_executable,
            volume_disposition_file=volume_disposition_file,
            volume_deletion_file=volume_deletion_file,
            volume_deletion_reconciliation_file=volume_deletion_reconciliation_file,
            volume_deletion_finalization_file=volume_deletion_finalization_file,
            lineage_manifest_file=lineage_manifest_file,
            retention_decision_file=retention_decision_file,
            legal_hold_decision_file=legal_hold_decision_file,
            recovery_decision_file=recovery_decision_file, project_name=project_name,
            evidence_directory=evidence_directory, processes=processes, clock=clock,
        )
        observed = json.loads(raw, object_pairs_hook=_pairs)
        if (
            type(observed) is not dict
            or set(observed) != {"schema_version", "operation", "outcome"}
            or observed["schema_version"] != 1
            or observed["operation"] != "disposable_postgres_volume_deletion_finalization"
            or observed["outcome"] not in {
                "continuation_required", "volume_removal_finalized",
                "deletion_evidence_confirmed", "not_found", "investigation_required",
            }
        ):
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        outcome = observed["outcome"]
        if outcome in {"volume_removal_finalized", "deletion_evidence_confirmed"}:
            return _result("already_finalized")
        if outcome in {"not_found", "investigation_required"}:
            return _result(outcome)
        if not _deletion_claim(original_claim, deletion_binding):
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        started = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        _create_claim(claim, binding, started, root_descriptor)
        docker, volume = str(docker_executable), current["retained_volume"]
        inspected = _observe(
            processes, (docker, "volume", "inspect", volume), maximum=1_048_576,
        )
        if not _owned_volume(inspected.stdout, name=volume, project=project_name):
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        _observe(processes, (docker, "volume", "rm", volume), maximum=65_536)
        absence = _observe(processes, (
            docker, "volume", "ls", "--filter", f"name=^{volume}$",
            "--format", "{{.Name}}",
        ), maximum=65_536)
        if absence.stdout:
            raise DisposablePostgresVolumeDeletionContinueUnavailable
        completed = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        _write(evidence_directory, root_descriptor, final, {
            **binding, "executed_step": "remove_exact_volume_once",
            "absence_confirmed": True, "started_at": started,
            "completed_at": completed,
            "outcome": "volume_removal_pending_finalization",
        }, binding)
        _release_claim(claim, binding, root_descriptor)
        return _result("volume_removal_pending_finalization")
    except DisposablePostgresVolumeDeletionContinueUnavailable:
        raise
    except (
        DisposablePostgresVolumeDeletionUnavailable,
        DisposablePostgresVolumeDeletionFinalizeUnavailable,
    ):
        raise DisposablePostgresVolumeDeletionContinueUnavailable from None
    except Exception:
        raise DisposablePostgresVolumeDeletionContinueUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        prog="liquent-disposable-postgres-volume-delete-continue", add_help=False,
    )
    for name in (
        "docker-executable", "volume-disposition-file", "volume-deletion-file",
        "volume-deletion-reconciliation-file", "volume-deletion-finalization-file",
        "volume-deletion-continuation-file", "lineage-manifest-file",
        "retention-decision-file", "legal-hold-decision-file",
        "recovery-decision-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        sys.stdout.buffer.write(continue_disposable_postgres_volume_deletion(
            **vars(parser.parse_args(argv)),
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
