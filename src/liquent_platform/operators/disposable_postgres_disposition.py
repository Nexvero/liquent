"""Strictly read-only disposition of finalized disposable PostgreSQL evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from liquent_platform.operators.disposable_postgres_claim_reconcile import (
    _authorization as _claim_authorization, _binding as _claim_binding,
    _existing as _claim_evidence, _historical_reconciliation,
)
from liquent_platform.operators.disposable_postgres_reconcile import (
    _evidence_binding, _evidence_root, _existing_evidence, _historical,
    _pairs, _timestamp,
)
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, OPAQUE, PHASES, SHA256,
)


KEYS = {
    "schema_version", "disposition_id", "run_id", "phase", "source_commit",
    "image_ref", "compose_sha256", "reconciliation_id",
    "claim_reconciliation_id", "staging_evidence_sha256",
    "reconciliation_evidence_sha256", "claim_reconciliation_evidence_sha256",
    "executor_id", "authorizer_id", "valid_from", "valid_until",
}


class DisposablePostgresDispositionUnavailable(Exception):
    code = "disposable_postgres_disposition_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresDispositionUnavailable


def _private_json(path: Path, maximum: int = 262_144) -> tuple[bytes, dict]:
    try:
        raw = _private_file(path, maximum)
        value = json.loads(raw, object_pairs_hook=_pairs)
        if type(value) is not dict:
            raise DisposablePostgresDispositionUnavailable
        return raw, value
    except DisposablePostgresDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresDispositionUnavailable from None


def _authorization(path: Path, *, clock) -> dict:
    _, value = _private_json(path, 32_768)
    try:
        if set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresDispositionUnavailable
        if value["phase"] != "disposable_postgres":
            raise DisposablePostgresDispositionUnavailable
        for key in (
            "disposition_id", "run_id", "reconciliation_id",
            "claim_reconciliation_id", "executor_id", "authorizer_id",
        ):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise DisposablePostgresDispositionUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise DisposablePostgresDispositionUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresDispositionUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresDispositionUnavailable
        for key in (
            "compose_sha256", "staging_evidence_sha256",
            "reconciliation_evidence_sha256",
            "claim_reconciliation_evidence_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresDispositionUnavailable
        start, end, now = _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock()
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
            or not start <= now.astimezone(UTC) <= end
        ):
            raise DisposablePostgresDispositionUnavailable
        return value
    except DisposablePostgresDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresDispositionUnavailable from None


def _historical_claim_authorization(path: Path) -> dict:
    try:
        _, value = _private_json(path, 32_768)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        return _claim_authorization(path, clock=lambda: start + (end - start) / 2)
    except Exception:
        raise DisposablePostgresDispositionUnavailable from None


def _staging_evidence(path: Path, original, expected_hash: str) -> bool:
    raw, value = _private_json(path)
    try:
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise DisposablePostgresDispositionUnavailable
        required = {
            "schema_version", "run_id", "environment", "source_commit",
            "image_ref", "compose_sha256", "migration_head", "observed_at",
            "review_by", "prepared_by", "reviewed_by", "checks",
        }
        if type(value) is not dict or set(value) != required or value["schema_version"] != 1:
            raise DisposablePostgresDispositionUnavailable
        if (
            value["run_id"] != original.run_id or value["environment"] != "staging"
            or value["source_commit"] != original.source_commit
            or value["image_ref"] != original.image_ref
            or value["compose_sha256"] != original.compose_sha256
            or value["migration_head"] != original.migration_head
            or value["prepared_by"] != original.executor_id
            or value["reviewed_by"] != original.authorizer_id
        ):
            raise DisposablePostgresDispositionUnavailable
        _timestamp(value["observed_at"])
        _timestamp(value["review_by"])
        checks = value["checks"]
        if type(checks) is not dict or set(checks) != set(PHASES):
            raise DisposablePostgresDispositionUnavailable
        for phase, check in checks.items():
            if type(check) is not dict or set(check) != {
                "status", "evidence_ref", "evidence_sha256",
            } or check["status"] not in {"passed", "failed", "unavailable"}:
                raise DisposablePostgresDispositionUnavailable
            if check["status"] == "unavailable":
                if check["evidence_ref"] is not None or check["evidence_sha256"] is not None:
                    raise DisposablePostgresDispositionUnavailable
            elif (
                type(check["evidence_ref"]) is not str
                or OPAQUE.fullmatch(check["evidence_ref"]) is None
                or type(check["evidence_sha256"]) is not str
                or SHA256.fullmatch(check["evidence_sha256"]) is None
            ):
                raise DisposablePostgresDispositionUnavailable
        start = PHASES.index("disposable_postgres")
        return all(
            checks[phase] == {
                "status": "unavailable", "evidence_ref": None,
                "evidence_sha256": None,
            }
            for phase in PHASES[start:]
        )
    except DisposablePostgresDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresDispositionUnavailable from None


def _hash_file(path: Path, expected: str) -> None:
    try:
        raw = _private_file(path, 65_536)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise DisposablePostgresDispositionUnavailable
    except DisposablePostgresDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresDispositionUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_disposition", "outcome": outcome,
        "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def resolve_disposable_postgres_disposition(
    *, authorization_file: Path, reconciliation_file: Path,
    claim_reconciliation_file: Path, disposition_file: Path,
    staging_evidence_file: Path, evidence_directory: Path,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        original = _historical(authorization_file)
        previous = _historical_reconciliation(reconciliation_file)
        claim_authorization = _historical_claim_authorization(claim_reconciliation_file)
        disposition = _authorization(disposition_file, clock=clock)
        if (
            previous["run_id"] != original.run_id
            or previous["source_commit"] != original.source_commit
            or previous["image_ref"] != original.image_ref
            or previous["compose_sha256"] != original.compose_sha256
            or claim_authorization["reconciliation_id"] != previous["reconciliation_id"]
            or claim_authorization["run_id"] != original.run_id
            or claim_authorization["source_commit"] != original.source_commit
            or claim_authorization["image_ref"] != original.image_ref
            or claim_authorization["compose_sha256"] != original.compose_sha256
            or disposition["run_id"] != original.run_id
            or disposition["source_commit"] != original.source_commit
            or disposition["image_ref"] != original.image_ref
            or disposition["compose_sha256"] != original.compose_sha256
            or disposition["reconciliation_id"] != previous["reconciliation_id"]
            or disposition["claim_reconciliation_id"]
            != claim_authorization["claim_reconciliation_id"]
        ):
            raise DisposablePostgresDispositionUnavailable
        root_descriptor = _evidence_root(evidence_directory)
        previous_stem = hashlib.sha256(previous["reconciliation_id"].encode()).hexdigest()
        previous_final = evidence_directory / f"postgres-reconciliation-{previous_stem}.json"
        previous_claim = evidence_directory / f".postgres-reconciliation-{previous_stem}.claim"
        claim_stem = hashlib.sha256(
            claim_authorization["claim_reconciliation_id"].encode()
        ).hexdigest()
        claim_final = evidence_directory / f"postgres-claim-reconciliation-{claim_stem}.json"
        claim_claim = evidence_directory / f".postgres-claim-reconciliation-{claim_stem}.claim"
        if previous_claim.exists() or claim_claim.exists():
            raise DisposablePostgresDispositionUnavailable
        _hash_file(previous_final, disposition["reconciliation_evidence_sha256"])
        _hash_file(claim_final, disposition["claim_reconciliation_evidence_sha256"])
        previous_outcome = _existing_evidence(
            previous_final, _evidence_binding(original, previous),
        )
        claim_outcome = _claim_evidence(
            claim_final, _claim_binding(original, previous, claim_authorization),
        )
        expected_claim = {
            "absent": {"already_finalized", "evidence_confirmed", "absence_finalized"},
            "isolated": {"already_finalized", "evidence_confirmed", "isolation_finalized"},
            "conflict": {"already_finalized", "evidence_confirmed", "conflict_finalized"},
        }[previous_outcome]
        if claim_outcome not in expected_claim:
            raise DisposablePostgresDispositionUnavailable
        no_later_effect = _staging_evidence(
            staging_evidence_file, original, disposition["staging_evidence_sha256"],
        )
        if previous_outcome == "conflict":
            outcome = "investigation_required"
        elif not no_later_effect:
            outcome = "retain"
        elif previous_outcome == "absent":
            outcome = "new_run_eligible"
        else:
            outcome = "cleanup_review_eligible"
        return _result(outcome)
    except DisposablePostgresDispositionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresDispositionUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-disposable-postgres-disposition", add_help=False)
    for name in (
        "authorization-file", "reconciliation-file", "claim-reconciliation-file",
        "disposition-file", "staging-evidence-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(resolve_disposable_postgres_disposition(
            authorization_file=value["authorization_file"],
            reconciliation_file=value["reconciliation_file"],
            claim_reconciliation_file=value["claim_reconciliation_file"],
            disposition_file=value["disposition_file"],
            staging_evidence_file=value["staging_evidence_file"],
            evidence_directory=value["evidence_directory"],
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
