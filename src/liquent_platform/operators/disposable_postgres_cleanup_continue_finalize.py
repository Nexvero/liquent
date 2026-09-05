"""Evidence-first finalization of a reconciled cleanup continuation claim."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from liquent_platform.operators.disposable_postgres_cleanup_continue import (
    DisposablePostgresCleanupContinueUnavailable, _continuation_claim,
    _evidence_binding as _continuation_binding,
)
from liquent_platform.operators.disposable_postgres_cleanup_continue_reconcile import (
    DisposablePostgresCleanupContinueReconcileUnavailable,
    _authorization as _reconciliation_authorization,
    _historical_continuation, reconcile_disposable_postgres_cleanup_continuation,
)
from liquent_platform.operators.disposable_postgres_cleanup_reconcile import (
    DisposablePostgresCleanupReconcileUnavailable, _claim, _historical_cleanup,
)
from liquent_platform.operators.disposable_postgres_reconcile import (
    DisposablePostgresReconcileUnavailable, _evidence_root, _historical, _pairs, _timestamp,
)
from liquent_platform.operators.disposable_postgres_runtime_cleanup import _binding
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import COMMIT, IMAGE, OPAQUE, SHA256


KEYS = {
    "schema_version", "continuation_finalization_id", "continuation_reconciliation_id",
    "cleanup_continuation_id", "cleanup_reconciliation_id", "cleanup_id", "run_id",
    "phase", "source_commit", "image_ref", "compose_sha256", "reconciliation_id",
    "claim_reconciliation_id", "disposition_id", "staging_evidence_sha256",
    "reconciliation_evidence_sha256", "claim_reconciliation_evidence_sha256",
    "disposition_authorization_sha256", "cleanup_authorization_sha256",
    "cleanup_reconciliation_authorization_sha256", "continuation_authorization_sha256",
    "continuation_reconciliation_authorization_sha256", "operation", "scope",
    "resume_from", "executor_id", "authorizer_id", "valid_from", "valid_until",
}
FINAL = {
    "continuation_evidence_present": "continuation_evidence_confirmed",
    "continuation_not_started": "continuation_attempt_finalized",
    "container_removed": "later_prefix_finalized",
    "application_network_removed": "later_prefix_finalized",
    "runtime_removed_evidence_missing": "runtime_removal_ready_for_cleanup_finalization",
}


class DisposablePostgresCleanupContinueFinalizeUnavailable(Exception):
    code = "disposable_postgres_cleanup_continue_finalize_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresCleanupContinueFinalizeUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        value = json.loads(_private_file(path, 32_768), object_pairs_hook=_pairs)
        if type(value) is not dict or set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
        if (
            value["phase"] != "disposable_postgres" or value["scope"] != "runtime_only"
            or value["operation"] != "finalize_disposable_postgres_cleanup_continuation"
            or value["resume_from"] not in {
                "container_stopped", "container_removed", "application_network_removed",
            }
        ):
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
        for key in (
            "continuation_finalization_id", "continuation_reconciliation_id",
            "cleanup_continuation_id", "cleanup_reconciliation_id", "cleanup_id", "run_id",
            "reconciliation_id", "claim_reconciliation_id", "disposition_id",
            "executor_id", "authorizer_id",
        ):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise DisposablePostgresCleanupContinueFinalizeUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
        for key in (
            "compose_sha256", "staging_evidence_sha256", "reconciliation_evidence_sha256",
            "claim_reconciliation_evidence_sha256", "disposition_authorization_sha256",
            "cleanup_authorization_sha256", "cleanup_reconciliation_authorization_sha256",
            "continuation_authorization_sha256",
            "continuation_reconciliation_authorization_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresCleanupContinueFinalizeUnavailable
        start, end, now = _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock()
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
            or not start <= now.astimezone(UTC) <= end
        ):
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
        return value
    except DisposablePostgresCleanupContinueFinalizeUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupContinueFinalizeUnavailable from None


def _historical_reconciliation(path: Path) -> dict:
    try:
        value = json.loads(_private_file(path, 32_768), object_pairs_hook=_pairs)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        return _reconciliation_authorization(path, clock=lambda: start + (end - start) / 2)
    except Exception:
        raise DisposablePostgresCleanupContinueFinalizeUnavailable from None


def _evidence_binding(current: dict, finalization_file: Path) -> dict:
    return {
        "schema_version": 1,
        **{key: current[key] for key in (
            "continuation_finalization_id", "continuation_reconciliation_id",
            "cleanup_continuation_id", "cleanup_reconciliation_id", "cleanup_id", "run_id",
            "phase", "source_commit", "image_ref", "compose_sha256", "reconciliation_id",
            "claim_reconciliation_id", "disposition_id", "staging_evidence_sha256",
            "reconciliation_evidence_sha256", "claim_reconciliation_evidence_sha256",
            "disposition_authorization_sha256", "cleanup_authorization_sha256",
            "cleanup_reconciliation_authorization_sha256", "continuation_authorization_sha256",
            "continuation_reconciliation_authorization_sha256", "scope", "resume_from",
            "executor_id", "authorizer_id",
        )},
        "finalization_authorization_sha256": hashlib.sha256(
            _private_file(finalization_file, 32_768)
        ).hexdigest(),
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
            or set(value) != set(binding) | {"observed_state", "outcome", "started_at", "completed_at"}
            or any(value[key] != expected for key, expected in binding.items())
            or value["observed_state"] not in FINAL
            or value["outcome"] != FINAL[value["observed_state"]]
        ):
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
        for key in ("started_at", "completed_at"):
            parsed = datetime.fromisoformat(value[key].replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise DisposablePostgresCleanupContinueFinalizeUnavailable
        return value["outcome"]
    except DisposablePostgresCleanupContinueFinalizeUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupContinueFinalizeUnavailable from None


def _write(root: Path, descriptor: int, final: Path, record: dict) -> None:
    temporary = root / f".{final.stem}-{os.getpid()}.tmp"
    opened = None
    try:
        content = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        opened = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        view = memoryview(content)
        while view:
            written = os.write(opened, view)
            if written < 1:
                raise DisposablePostgresCleanupContinueFinalizeUnavailable
            view = view[written:]
        os.fsync(opened)
        os.close(opened)
        opened = None
        os.link(temporary, final)
        temporary.unlink()
        os.fsync(descriptor)
        excluded = {"observed_state", "outcome", "started_at", "completed_at"}
        if _existing(final, {key: value for key, value in record.items() if key not in excluded}) != record["outcome"]:
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
    except DisposablePostgresCleanupContinueFinalizeUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupContinueFinalizeUnavailable from None
    finally:
        if opened is not None:
            os.close(opened)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _release(path: Path, binding: dict, descriptor: int) -> None:
    try:
        if not path.exists():
            return
        if not _continuation_claim(path, binding):
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
        os.unlink(path)
        os.fsync(descriptor)
    except DisposablePostgresCleanupContinueFinalizeUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupContinueFinalizeUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_cleanup_continuation_finalization",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def finalize_disposable_postgres_cleanup_continuation(
    *, docker_executable: Path, authorization_file: Path, reconciliation_file: Path,
    claim_reconciliation_file: Path, disposition_file: Path, cleanup_file: Path,
    cleanup_reconciliation_file: Path, cleanup_continuation_file: Path,
    continuation_reconciliation_file: Path, continuation_finalization_file: Path,
    staging_evidence_file: Path, compose_file: Path, runtime_environment_file: Path,
    image_environment_file: Path, project_name: str, evidence_directory: Path,
    processes=None, clock=lambda: datetime.now(UTC),
) -> bytes:
    descriptor = None
    try:
        original = _historical(authorization_file)
        cleanup = _historical_cleanup(cleanup_file)
        continuation = _historical_continuation(cleanup_continuation_file)
        reconciliation = _historical_reconciliation(continuation_reconciliation_file)
        current = _authorization(continuation_finalization_file, clock=clock)
        reconciliation_raw = _private_file(continuation_reconciliation_file, 32_768)
        compared = (
            "continuation_reconciliation_id", "cleanup_continuation_id",
            "cleanup_reconciliation_id", "cleanup_id", "run_id", "source_commit", "image_ref",
            "compose_sha256", "reconciliation_id", "claim_reconciliation_id", "disposition_id",
            "staging_evidence_sha256", "reconciliation_evidence_sha256",
            "claim_reconciliation_evidence_sha256", "disposition_authorization_sha256",
            "cleanup_authorization_sha256", "cleanup_reconciliation_authorization_sha256",
            "continuation_authorization_sha256", "resume_from",
        )
        if (
            current["continuation_reconciliation_authorization_sha256"]
            != hashlib.sha256(reconciliation_raw).hexdigest()
            or any(current[key] != reconciliation[key] for key in compared)
            or cleanup["cleanup_id"] != current["cleanup_id"]
            or continuation["cleanup_continuation_id"] != current["cleanup_continuation_id"]
            or original.run_id != current["run_id"]
            or project_name != f"liquent-{original.run_id}"
        ):
            raise DisposablePostgresCleanupContinueFinalizeUnavailable

        cleanup_binding = _binding(original, cleanup, cleanup_file, project_name)
        cleanup_stem = hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        cleanup_claim = evidence_directory / f".postgres-cleanup-{cleanup_stem}.claim"
        if not _claim(cleanup_claim, cleanup_binding):
            return _result("investigation_required")

        continuation_evidence_binding = _continuation_binding(
            continuation, cleanup_continuation_file, project_name,
        )
        continuation_stem = hashlib.sha256(current["cleanup_continuation_id"].encode()).hexdigest()
        continuation_claim = evidence_directory / f".postgres-cleanup-continuation-{continuation_stem}.claim"
        evidence_binding = _evidence_binding(current, continuation_finalization_file)
        final_stem = hashlib.sha256(current["continuation_finalization_id"].encode()).hexdigest()
        final = evidence_directory / f"postgres-cleanup-continuation-finalization-{final_stem}.json"
        descriptor = _evidence_root(evidence_directory)
        existing = _existing(final, evidence_binding)
        if existing is not None:
            _release(continuation_claim, continuation_evidence_binding, descriptor)
            return _result(existing)

        start = _timestamp(reconciliation["valid_from"])
        end = _timestamp(reconciliation["valid_until"])
        raw = reconcile_disposable_postgres_cleanup_continuation(
            docker_executable=docker_executable, authorization_file=authorization_file,
            reconciliation_file=reconciliation_file,
            claim_reconciliation_file=claim_reconciliation_file,
            disposition_file=disposition_file, cleanup_file=cleanup_file,
            cleanup_reconciliation_file=cleanup_reconciliation_file,
            cleanup_continuation_file=cleanup_continuation_file,
            continuation_reconciliation_file=continuation_reconciliation_file,
            staging_evidence_file=staging_evidence_file, compose_file=compose_file,
            runtime_environment_file=runtime_environment_file,
            image_environment_file=image_environment_file, project_name=project_name,
            evidence_directory=evidence_directory, processes=processes,
            clock=lambda: start + (end - start) / 2,
        )
        observed = json.loads(raw, object_pairs_hook=_pairs)
        if (
            type(observed) is not dict
            or set(observed) != {"schema_version", "operation", "outcome"}
            or observed["schema_version"] != 1
            or observed["operation"] != "disposable_postgres_cleanup_continuation_reconciliation"
        ):
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
        state = observed["outcome"]
        if state == "not_found":
            return _result("not_found")
        if state == "conflict":
            return _result("investigation_required")
        if state not in FINAL:
            raise DisposablePostgresCleanupContinueFinalizeUnavailable
        outcome = FINAL[state]
        started = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        record = dict(evidence_binding, observed_state=state, outcome=outcome, started_at=started)
        record["completed_at"] = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        _write(evidence_directory, descriptor, final, record)
        _release(continuation_claim, continuation_evidence_binding, descriptor)
        return _result(outcome)
    except DisposablePostgresCleanupContinueFinalizeUnavailable:
        raise
    except (
        DisposablePostgresCleanupContinueUnavailable,
        DisposablePostgresCleanupContinueReconcileUnavailable,
        DisposablePostgresCleanupReconcileUnavailable,
        DisposablePostgresReconcileUnavailable,
    ):
        raise DisposablePostgresCleanupContinueFinalizeUnavailable from None
    except Exception:
        raise DisposablePostgresCleanupContinueFinalizeUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-disposable-postgres-cleanup-continue-finalize", add_help=False)
    for name in (
        "docker-executable", "authorization-file", "reconciliation-file",
        "claim-reconciliation-file", "disposition-file", "cleanup-file",
        "cleanup-reconciliation-file", "cleanup-continuation-file",
        "continuation-reconciliation-file", "continuation-finalization-file",
        "staging-evidence-file", "compose-file", "runtime-env-file", "image-env-file",
        "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(finalize_disposable_postgres_cleanup_continuation(
            docker_executable=value["docker_executable"], authorization_file=value["authorization_file"],
            reconciliation_file=value["reconciliation_file"],
            claim_reconciliation_file=value["claim_reconciliation_file"],
            disposition_file=value["disposition_file"], cleanup_file=value["cleanup_file"],
            cleanup_reconciliation_file=value["cleanup_reconciliation_file"],
            cleanup_continuation_file=value["cleanup_continuation_file"],
            continuation_reconciliation_file=value["continuation_reconciliation_file"],
            continuation_finalization_file=value["continuation_finalization_file"],
            staging_evidence_file=value["staging_evidence_file"], compose_file=value["compose_file"],
            runtime_environment_file=value["runtime_env_file"],
            image_environment_file=value["image_env_file"], project_name=value["project_name"],
            evidence_directory=value["evidence_directory"],
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
