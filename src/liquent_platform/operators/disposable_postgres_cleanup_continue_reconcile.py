"""Read-only reconciliation of one open PostgreSQL cleanup continuation claim."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from liquent_platform.operators.disposable_postgres_cleanup_continue import (
    DisposablePostgresCleanupContinueUnavailable, _authorization as _continuation_authorization,
    _continuation_claim, _evidence_binding, _existing,
)
from liquent_platform.operators.disposable_postgres_cleanup_finalize import (
    _historical_reconciliation,
)
from liquent_platform.operators.disposable_postgres_cleanup_reconcile import (
    DisposablePostgresCleanupReconcileUnavailable, _claim, _historical_cleanup,
    reconcile_disposable_postgres_cleanup,
)
from liquent_platform.operators.disposable_postgres_reconcile import (
    DisposablePostgresReconcileUnavailable, _historical, _pairs, _timestamp,
)
from liquent_platform.operators.disposable_postgres_runtime_cleanup import _binding
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import COMMIT, IMAGE, OPAQUE, SHA256


ORDER = {
    "container_stopped": 0,
    "container_removed": 1,
    "application_network_removed": 2,
    "runtime_removed_evidence_missing": 3,
}
KEYS = {
    "schema_version", "continuation_reconciliation_id", "cleanup_continuation_id",
    "cleanup_reconciliation_id", "cleanup_id", "run_id", "phase", "source_commit",
    "image_ref", "compose_sha256", "reconciliation_id", "claim_reconciliation_id",
    "disposition_id", "staging_evidence_sha256", "reconciliation_evidence_sha256",
    "claim_reconciliation_evidence_sha256", "disposition_authorization_sha256",
    "cleanup_authorization_sha256", "cleanup_reconciliation_authorization_sha256",
    "continuation_authorization_sha256", "operation", "scope", "resume_from",
    "executor_id", "authorizer_id", "valid_from", "valid_until",
}


class DisposablePostgresCleanupContinueReconcileUnavailable(Exception):
    code = "disposable_postgres_cleanup_continue_reconcile_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresCleanupContinueReconcileUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        value = json.loads(_private_file(path, 32_768), object_pairs_hook=_pairs)
        if type(value) is not dict or set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresCleanupContinueReconcileUnavailable
        if (
            value["phase"] != "disposable_postgres" or value["scope"] != "runtime_only"
            or value["operation"] != "inspect_disposable_postgres_cleanup_continuation"
            or value["resume_from"] not in ORDER
            or value["resume_from"] == "runtime_removed_evidence_missing"
        ):
            raise DisposablePostgresCleanupContinueReconcileUnavailable
        for key in (
            "continuation_reconciliation_id", "cleanup_continuation_id",
            "cleanup_reconciliation_id", "cleanup_id", "run_id", "reconciliation_id",
            "claim_reconciliation_id", "disposition_id", "executor_id", "authorizer_id",
        ):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise DisposablePostgresCleanupContinueReconcileUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise DisposablePostgresCleanupContinueReconcileUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresCleanupContinueReconcileUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresCleanupContinueReconcileUnavailable
        for key in (
            "compose_sha256", "staging_evidence_sha256", "reconciliation_evidence_sha256",
            "claim_reconciliation_evidence_sha256", "disposition_authorization_sha256",
            "cleanup_authorization_sha256", "cleanup_reconciliation_authorization_sha256",
            "continuation_authorization_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresCleanupContinueReconcileUnavailable
        start, end, now = _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock()
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
            or not start <= now.astimezone(UTC) <= end
        ):
            raise DisposablePostgresCleanupContinueReconcileUnavailable
        return value
    except DisposablePostgresCleanupContinueReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupContinueReconcileUnavailable from None


def _historical_continuation(path: Path) -> dict:
    try:
        value = json.loads(_private_file(path, 32_768), object_pairs_hook=_pairs)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        return _continuation_authorization(path, clock=lambda: start + (end - start) / 2)
    except Exception:
        raise DisposablePostgresCleanupContinueReconcileUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_cleanup_continuation_reconciliation",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def reconcile_disposable_postgres_cleanup_continuation(
    *, docker_executable: Path, authorization_file: Path,
    reconciliation_file: Path, claim_reconciliation_file: Path,
    disposition_file: Path, cleanup_file: Path, cleanup_reconciliation_file: Path,
    cleanup_continuation_file: Path, continuation_reconciliation_file: Path,
    staging_evidence_file: Path, compose_file: Path,
    runtime_environment_file: Path, image_environment_file: Path,
    project_name: str, evidence_directory: Path, processes=None,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    try:
        original = _historical(authorization_file)
        cleanup = _historical_cleanup(cleanup_file)
        previous_reconciliation = _historical_reconciliation(cleanup_reconciliation_file)
        continuation = _historical_continuation(cleanup_continuation_file)
        current = _authorization(continuation_reconciliation_file, clock=clock)
        continuation_raw = _private_file(cleanup_continuation_file, 32_768)
        compared = (
            "cleanup_continuation_id", "cleanup_reconciliation_id", "cleanup_id", "run_id",
            "source_commit", "image_ref", "compose_sha256", "reconciliation_id",
            "claim_reconciliation_id", "disposition_id", "staging_evidence_sha256",
            "reconciliation_evidence_sha256", "claim_reconciliation_evidence_sha256",
            "disposition_authorization_sha256", "cleanup_authorization_sha256",
            "cleanup_reconciliation_authorization_sha256", "resume_from",
        )
        if (
            current["continuation_authorization_sha256"]
            != hashlib.sha256(continuation_raw).hexdigest()
            or any(current[key] != continuation[key] for key in compared)
            or cleanup["cleanup_id"] != current["cleanup_id"]
            or previous_reconciliation["cleanup_reconciliation_id"]
            != current["cleanup_reconciliation_id"]
            or original.run_id != current["run_id"]
            or project_name != f"liquent-{original.run_id}"
        ):
            raise DisposablePostgresCleanupContinueReconcileUnavailable

        cleanup_binding = _binding(original, cleanup, cleanup_file, project_name)
        cleanup_stem = hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        cleanup_claim = evidence_directory / f".postgres-cleanup-{cleanup_stem}.claim"
        if not _claim(cleanup_claim, cleanup_binding):
            return _result("conflict")

        continuation_binding = _evidence_binding(
            continuation, cleanup_continuation_file, project_name,
        )
        stem = hashlib.sha256(continuation["cleanup_continuation_id"].encode()).hexdigest()
        claim = evidence_directory / f".postgres-cleanup-continuation-{stem}.claim"
        final = evidence_directory / f"postgres-cleanup-continuation-{stem}.json"
        if _existing(final, continuation_binding):
            return _result("continuation_evidence_present")
        if not _continuation_claim(claim, continuation_binding):
            return _result("not_found")

        start = _timestamp(previous_reconciliation["valid_from"])
        end = _timestamp(previous_reconciliation["valid_until"])
        raw = reconcile_disposable_postgres_cleanup(
            docker_executable=docker_executable, authorization_file=authorization_file,
            reconciliation_file=reconciliation_file,
            claim_reconciliation_file=claim_reconciliation_file,
            disposition_file=disposition_file, cleanup_file=cleanup_file,
            cleanup_reconciliation_file=cleanup_reconciliation_file,
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
            or observed["operation"] != "disposable_postgres_runtime_cleanup_reconciliation"
        ):
            raise DisposablePostgresCleanupContinueReconcileUnavailable
        outcome = observed["outcome"]
        if outcome not in ORDER or ORDER[outcome] < ORDER[current["resume_from"]]:
            return _result("conflict")
        if outcome == current["resume_from"]:
            return _result("continuation_not_started")
        return _result(outcome)
    except DisposablePostgresCleanupContinueReconcileUnavailable:
        raise
    except (
        DisposablePostgresCleanupContinueUnavailable,
        DisposablePostgresCleanupReconcileUnavailable,
        DisposablePostgresReconcileUnavailable,
    ):
        raise DisposablePostgresCleanupContinueReconcileUnavailable from None
    except Exception:
        raise DisposablePostgresCleanupContinueReconcileUnavailable from None


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        prog="liquent-disposable-postgres-cleanup-continue-reconcile", add_help=False,
    )
    for name in (
        "docker-executable", "authorization-file", "reconciliation-file",
        "claim-reconciliation-file", "disposition-file", "cleanup-file",
        "cleanup-reconciliation-file", "cleanup-continuation-file",
        "continuation-reconciliation-file", "staging-evidence-file", "compose-file",
        "runtime-env-file", "image-env-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(reconcile_disposable_postgres_cleanup_continuation(
            docker_executable=value["docker_executable"],
            authorization_file=value["authorization_file"],
            reconciliation_file=value["reconciliation_file"],
            claim_reconciliation_file=value["claim_reconciliation_file"],
            disposition_file=value["disposition_file"], cleanup_file=value["cleanup_file"],
            cleanup_reconciliation_file=value["cleanup_reconciliation_file"],
            cleanup_continuation_file=value["cleanup_continuation_file"],
            continuation_reconciliation_file=value["continuation_reconciliation_file"],
            staging_evidence_file=value["staging_evidence_file"],
            compose_file=value["compose_file"],
            runtime_environment_file=value["runtime_env_file"],
            image_environment_file=value["image_env_file"],
            project_name=value["project_name"], evidence_directory=value["evidence_directory"],
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
