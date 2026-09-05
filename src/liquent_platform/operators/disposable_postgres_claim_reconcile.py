"""Evidence-first reconciliation of a disposable PostgreSQL recovery claim."""

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
    DisposablePostgresReconcileUnavailable, _evidence_binding, _evidence_root,
    _existing_evidence, _historical, _json_private, _pairs, _reconciliation,
    _result as _inspection_result, _store_evidence, _timestamp, _valid_claim,
    reconcile_disposable_postgres,
)
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, OPAQUE, SHA256,
)


KEYS = {
    "schema_version", "claim_reconciliation_id", "reconciliation_id",
    "run_id", "phase", "source_commit", "image_ref", "compose_sha256",
    "reconciliation_executor_id", "reconciliation_authorizer_id",
    "executor_id", "authorizer_id", "valid_from", "valid_until",
}
OUTCOMES = {
    "already_finalized", "evidence_confirmed", "absence_finalized",
    "isolation_finalized", "conflict_finalized", "not_found",
}


class DisposablePostgresClaimReconcileUnavailable(Exception):
    code = "disposable_postgres_claim_reconcile_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresClaimReconcileUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        value = _json_private(path)
        if set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresClaimReconcileUnavailable
        if value["phase"] != "disposable_postgres":
            raise DisposablePostgresClaimReconcileUnavailable
        for key in (
            "claim_reconciliation_id", "reconciliation_id", "run_id",
            "reconciliation_executor_id", "reconciliation_authorizer_id",
            "executor_id", "authorizer_id",
        ):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise DisposablePostgresClaimReconcileUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise DisposablePostgresClaimReconcileUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresClaimReconcileUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresClaimReconcileUnavailable
        if type(value["compose_sha256"]) is not str or SHA256.fullmatch(value["compose_sha256"]) is None:
            raise DisposablePostgresClaimReconcileUnavailable
        start, end, now = _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock()
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
            or not start <= now.astimezone(UTC) <= end
        ):
            raise DisposablePostgresClaimReconcileUnavailable
        return value
    except DisposablePostgresClaimReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresClaimReconcileUnavailable from None


def _historical_reconciliation(path: Path) -> dict:
    try:
        value = _json_private(path)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        return _reconciliation(path, clock=lambda: start + (end - start) / 2)
    except Exception:
        raise DisposablePostgresClaimReconcileUnavailable from None


def _binding(original, previous: dict, current: dict) -> dict:
    return {
        "schema_version": 1,
        "claim_reconciliation_id": current["claim_reconciliation_id"],
        "reconciliation_id": previous["reconciliation_id"],
        "run_id": original.run_id, "phase": "disposable_postgres",
        "source_commit": original.source_commit, "image_ref": original.image_ref,
        "compose_sha256": original.compose_sha256,
        "reconciliation_executor_id": previous["executor_id"],
        "reconciliation_authorizer_id": previous["authorizer_id"],
        "executor_id": current["executor_id"],
        "authorizer_id": current["authorizer_id"],
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
            or set(value) != set(binding) | {"outcome", "completed_at"}
            or any(value[key] != expected for key, expected in binding.items())
            or value["outcome"] not in OUTCOMES
            or type(value["completed_at"]) is not str
        ):
            raise DisposablePostgresClaimReconcileUnavailable
        _timestamp(value["completed_at"])
        return value["outcome"]
    except DisposablePostgresClaimReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresClaimReconcileUnavailable from None


def _write(root: Path, descriptor: int, final: Path, record: dict) -> None:
    temporary = root / f".{final.stem}-{os.getpid()}.tmp"
    opened = None
    try:
        content = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        opened = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
        )
        view = memoryview(content)
        while view:
            written = os.write(opened, view)
            if written < 1:
                raise DisposablePostgresClaimReconcileUnavailable
            view = view[written:]
        os.fsync(opened)
        os.close(opened)
        opened = None
        os.link(temporary, final)
        temporary.unlink()
        os.fsync(descriptor)
        binding = {key: record[key] for key in record if key not in {"outcome", "completed_at"}}
        if _existing(final, binding) != record["outcome"]:
            raise DisposablePostgresClaimReconcileUnavailable
    except DisposablePostgresClaimReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresClaimReconcileUnavailable from None
    finally:
        if opened is not None:
            os.close(opened)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_claim_reconciliation",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def reconcile_disposable_postgres_claim(
    *, docker_executable: Path, authorization_file: Path,
    reconciliation_file: Path, claim_reconciliation_file: Path,
    compose_file: Path, runtime_environment_file: Path,
    image_environment_file: Path, project_name: str,
    evidence_directory: Path, processes=None,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        original = _historical(authorization_file)
        previous = _historical_reconciliation(reconciliation_file)
        current = _authorization(claim_reconciliation_file, clock=clock)
        if (
            current["reconciliation_id"] != previous["reconciliation_id"]
            or current["run_id"] != original.run_id
            or current["source_commit"] != original.source_commit
            or current["image_ref"] != original.image_ref
            or current["compose_sha256"] != original.compose_sha256
            or current["reconciliation_executor_id"] != previous["executor_id"]
            or current["reconciliation_authorizer_id"] != previous["authorizer_id"]
            or previous["run_id"] != original.run_id
            or previous["source_commit"] != original.source_commit
            or previous["image_ref"] != original.image_ref
            or previous["compose_sha256"] != original.compose_sha256
            or project_name != f"liquent-{original.run_id}"
        ):
            raise DisposablePostgresClaimReconcileUnavailable
        root_descriptor = _evidence_root(evidence_directory)
        previous_stem = hashlib.sha256(previous["reconciliation_id"].encode()).hexdigest()
        previous_final = evidence_directory / f"postgres-reconciliation-{previous_stem}.json"
        previous_claim = evidence_directory / f".postgres-reconciliation-{previous_stem}.claim"
        previous_binding = _evidence_binding(original, previous)
        binding = _binding(original, previous, current)
        stem = hashlib.sha256(current["claim_reconciliation_id"].encode()).hexdigest()
        final = evidence_directory / f"postgres-claim-reconciliation-{stem}.json"
        claim = evidence_directory / f".postgres-claim-reconciliation-{stem}.claim"
        existing = _existing(final, binding)
        if existing is not None:
            if claim.exists():
                _claim_exact(claim, b"disposable-postgres-claim-reconciliation\n")
                os.unlink(claim)
                os.fsync(root_descriptor)
            return _result(existing)
        descriptor = os.open(
            claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
        )
        try:
            content = b"disposable-postgres-claim-reconciliation\n"
            if os.write(descriptor, content) != len(content):
                raise DisposablePostgresClaimReconcileUnavailable
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(root_descriptor)
        previous_outcome = _existing_evidence(previous_final, previous_binding)
        previous_claim_exists = _valid_claim(previous_claim)
        if not previous_claim_exists:
            outcome = "already_finalized" if previous_outcome is not None else "not_found"
        elif previous_outcome is not None:
            outcome = "evidence_confirmed"
        else:
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
                raise DisposablePostgresClaimReconcileUnavailable
            original_record = dict(previous_binding)
            original_record.update({
                "outcome": value["outcome"],
                "completed_at": clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
            })
            _store_evidence(
                evidence_directory, root_descriptor, previous_final, original_record,
            )
            outcome = {
                "absent": "absence_finalized", "isolated": "isolation_finalized",
                "conflict": "conflict_finalized",
            }[value["outcome"]]
        record = dict(binding)
        record.update({
            "outcome": outcome,
            "completed_at": clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
        })
        _write(evidence_directory, root_descriptor, final, record)
        if previous_claim_exists and outcome in {
            "evidence_confirmed", "absence_finalized", "isolation_finalized",
            "conflict_finalized",
        }:
            os.unlink(previous_claim)
            os.fsync(root_descriptor)
        os.unlink(claim)
        os.fsync(root_descriptor)
        return _result(outcome)
    except DisposablePostgresClaimReconcileUnavailable:
        raise
    except DisposablePostgresReconcileUnavailable:
        raise DisposablePostgresClaimReconcileUnavailable from None
    except Exception:
        raise DisposablePostgresClaimReconcileUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def _claim_exact(path: Path, content: bytes) -> None:
    try:
        metadata = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or path.read_bytes() != content
        ):
            raise DisposablePostgresClaimReconcileUnavailable
    except DisposablePostgresClaimReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresClaimReconcileUnavailable from None


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-disposable-postgres-claim-reconcile", add_help=False)
    for name in (
        "docker-executable", "authorization-file", "reconciliation-file",
        "claim-reconciliation-file", "compose-file", "runtime-env-file",
        "image-env-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(reconcile_disposable_postgres_claim(
            docker_executable=value["docker_executable"],
            authorization_file=value["authorization_file"],
            reconciliation_file=value["reconciliation_file"],
            claim_reconciliation_file=value["claim_reconciliation_file"],
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
