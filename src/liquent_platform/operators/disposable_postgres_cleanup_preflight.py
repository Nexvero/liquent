"""Read-only preflight for explicitly scoped disposable PostgreSQL cleanup."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from liquent_platform.operators.disposable_postgres_claim_reconcile import (
    _historical_reconciliation,
)
from liquent_platform.operators.disposable_postgres_disposition import (
    DisposablePostgresDispositionUnavailable, _authorization as _disposition,
    resolve_disposable_postgres_disposition,
)
from liquent_platform.operators.disposable_postgres_reconcile import (
    DisposablePostgresReconcileUnavailable, _historical, _pairs, _timestamp,
    reconcile_disposable_postgres,
)
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, OPAQUE, SHA256,
)


KEYS = {
    "schema_version", "cleanup_id", "run_id", "phase", "source_commit",
    "image_ref", "compose_sha256", "reconciliation_id",
    "claim_reconciliation_id", "disposition_id", "staging_evidence_sha256",
    "reconciliation_evidence_sha256", "claim_reconciliation_evidence_sha256",
    "disposition_authorization_sha256", "operation", "scope", "executor_id",
    "authorizer_id", "valid_from", "valid_until",
}


class DisposablePostgresCleanupPreflightUnavailable(Exception):
    code = "disposable_postgres_cleanup_preflight_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresCleanupPreflightUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        raw = _private_file(path, 32_768)
        value = json.loads(raw, object_pairs_hook=_pairs)
        if type(value) is not dict or set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresCleanupPreflightUnavailable
        if (
            value["phase"] != "disposable_postgres"
            or value["operation"] != "remove_disposable_postgres_resources"
            or value["scope"] not in {"runtime_only", "runtime_and_data_volume"}
        ):
            raise DisposablePostgresCleanupPreflightUnavailable
        for key in (
            "cleanup_id", "run_id", "reconciliation_id",
            "claim_reconciliation_id", "disposition_id", "executor_id",
            "authorizer_id",
        ):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise DisposablePostgresCleanupPreflightUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise DisposablePostgresCleanupPreflightUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresCleanupPreflightUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresCleanupPreflightUnavailable
        for key in (
            "compose_sha256", "staging_evidence_sha256",
            "reconciliation_evidence_sha256",
            "claim_reconciliation_evidence_sha256",
            "disposition_authorization_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresCleanupPreflightUnavailable
        start, end, now = _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock()
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
            or not start <= now.astimezone(UTC) <= end
        ):
            raise DisposablePostgresCleanupPreflightUnavailable
        return value
    except DisposablePostgresCleanupPreflightUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupPreflightUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_cleanup_preflight",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def preflight_disposable_postgres_cleanup(
    *, docker_executable: Path, authorization_file: Path,
    reconciliation_file: Path, claim_reconciliation_file: Path,
    disposition_file: Path, cleanup_file: Path, staging_evidence_file: Path,
    compose_file: Path, runtime_environment_file: Path,
    image_environment_file: Path, project_name: str, evidence_directory: Path,
    processes=None, clock=lambda: datetime.now(UTC),
) -> bytes:
    try:
        original = _historical(authorization_file)
        previous = _historical_reconciliation(reconciliation_file)
        disposition = _disposition(disposition_file, clock=clock)
        cleanup = _authorization(cleanup_file, clock=clock)
        disposition_raw = _private_file(disposition_file, 32_768)
        if (
            hashlib.sha256(disposition_raw).hexdigest()
            != cleanup["disposition_authorization_sha256"]
            or cleanup["run_id"] != original.run_id
            or cleanup["source_commit"] != original.source_commit
            or cleanup["image_ref"] != original.image_ref
            or cleanup["compose_sha256"] != original.compose_sha256
            or cleanup["reconciliation_id"] != previous["reconciliation_id"]
            or cleanup["claim_reconciliation_id"]
            != disposition["claim_reconciliation_id"]
            or cleanup["disposition_id"] != disposition["disposition_id"]
            or cleanup["staging_evidence_sha256"]
            != disposition["staging_evidence_sha256"]
            or cleanup["reconciliation_evidence_sha256"]
            != disposition["reconciliation_evidence_sha256"]
            or cleanup["claim_reconciliation_evidence_sha256"]
            != disposition["claim_reconciliation_evidence_sha256"]
            or project_name != f"liquent-{original.run_id}"
        ):
            raise DisposablePostgresCleanupPreflightUnavailable
        cleanup_stem = hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        cleanup_claim = evidence_directory / f".postgres-cleanup-{cleanup_stem}.claim"
        if cleanup_claim.exists():
            raise DisposablePostgresCleanupPreflightUnavailable
        resolved = resolve_disposable_postgres_disposition(
            authorization_file=authorization_file,
            reconciliation_file=reconciliation_file,
            claim_reconciliation_file=claim_reconciliation_file,
            disposition_file=disposition_file,
            staging_evidence_file=staging_evidence_file,
            evidence_directory=evidence_directory, clock=clock,
        )
        resolved_value = json.loads(resolved, object_pairs_hook=_pairs)
        if (
            type(resolved_value) is not dict
            or set(resolved_value) != {"schema_version", "operation", "outcome"}
            or resolved_value["schema_version"] != 1
            or resolved_value["operation"] != "disposable_postgres_disposition"
            or resolved_value["outcome"] != "cleanup_review_eligible"
        ):
            raise DisposablePostgresCleanupPreflightUnavailable
        start, end = _timestamp(previous["valid_from"]), _timestamp(previous["valid_until"])
        observed = reconcile_disposable_postgres(
            docker_executable=docker_executable,
            authorization_file=authorization_file,
            reconciliation_file=reconciliation_file, compose_file=compose_file,
            runtime_environment_file=runtime_environment_file,
            image_environment_file=image_environment_file,
            project_name=project_name, processes=processes,
            clock=lambda: start + (end - start) / 2,
        )
        value = json.loads(observed, object_pairs_hook=_pairs)
        if (
            type(value) is not dict
            or set(value) != {"schema_version", "inspection", "outcome"}
            or value["schema_version"] != 1
            or value["inspection"] != "disposable_postgres_reconciliation"
            or value["outcome"] not in {"absent", "isolated", "conflict"}
        ):
            raise DisposablePostgresCleanupPreflightUnavailable
        if value["outcome"] == "absent":
            outcome = "already_absent"
        elif value["outcome"] == "conflict":
            outcome = "rejected"
        elif cleanup["scope"] == "runtime_and_data_volume":
            # No authoritative retention/legal-hold clearance source exists yet.
            outcome = "rejected"
        else:
            outcome = "ready"
        return _result(outcome)
    except DisposablePostgresCleanupPreflightUnavailable:
        raise
    except (DisposablePostgresDispositionUnavailable, DisposablePostgresReconcileUnavailable):
        raise DisposablePostgresCleanupPreflightUnavailable from None
    except Exception:
        raise DisposablePostgresCleanupPreflightUnavailable from None


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-disposable-postgres-cleanup-preflight", add_help=False)
    for name in (
        "docker-executable", "authorization-file", "reconciliation-file",
        "claim-reconciliation-file", "disposition-file", "cleanup-file",
        "staging-evidence-file", "compose-file", "runtime-env-file",
        "image-env-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(preflight_disposable_postgres_cleanup(
            docker_executable=value["docker_executable"],
            authorization_file=value["authorization_file"],
            reconciliation_file=value["reconciliation_file"],
            claim_reconciliation_file=value["claim_reconciliation_file"],
            disposition_file=value["disposition_file"],
            cleanup_file=value["cleanup_file"],
            staging_evidence_file=value["staging_evidence_file"],
            compose_file=value["compose_file"],
            runtime_environment_file=value["runtime_env_file"],
            image_environment_file=value["image_env_file"],
            project_name=value["project_name"],
            evidence_directory=value["evidence_directory"],
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
