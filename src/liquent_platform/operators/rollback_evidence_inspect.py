"""Read-only current rollback evidence inspection for one authorized staging run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import (
    StagingRunAuthorization,
)


OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
IMAGE = re.compile(r"[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}\Z")
EXPECTATION_KEYS = {
    "schema_version", "run_id", "environment", "source_commit",
    "candidate_image_ref", "rollback_evidence_sha256", "executor_id",
    "authorizer_id", "valid_from", "valid_until",
}
EVIDENCE_KEYS = {
    "schema_version", "environment", "source_commit", "candidate_image_ref",
    "previous_healthy_image_ref", "rollback_target_image_ref",
    "backup_snapshot_ref", "backup_evidence_sha256", "restore_evidence_sha256",
    "created_at", "verified_at", "valid_until", "prepared_by", "reviewed_by",
    "status",
}


class RollbackEvidenceInspectUnavailable(Exception):
    code = "rollback_evidence_inspect_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise RollbackEvidenceInspectUnavailable


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise RollbackEvidenceInspectUnavailable
        result[key] = value
    return result


def _timestamp(value: object) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise RollbackEvidenceInspectUnavailable
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise RollbackEvidenceInspectUnavailable from None
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise RollbackEvidenceInspectUnavailable
    return parsed


def _load(path: Path, maximum: int) -> tuple[bytes, dict]:
    try:
        raw = _private_file(path, maximum)
        value = json.loads(raw, object_pairs_hook=_pairs)
        if type(value) is not dict:
            raise RollbackEvidenceInspectUnavailable
        return raw, value
    except RollbackEvidenceInspectUnavailable:
        raise
    except Exception:
        raise RollbackEvidenceInspectUnavailable from None


def inspect_rollback_evidence(
    expectation_file: Path, evidence_file: Path,
    *, authorization: StagingRunAuthorization | None = None,
    clock=lambda: datetime.now(UTC),
) -> bool:
    """Return one explicit currency fact; malformed private input is unavailable."""

    try:
        _, expectation = _load(expectation_file, 16_384)
        raw, evidence = _load(evidence_file, 65_536)
        if set(expectation) != EXPECTATION_KEYS or expectation["schema_version"] != 1:
            raise RollbackEvidenceInspectUnavailable
        if expectation["environment"] != "staging":
            raise RollbackEvidenceInspectUnavailable
        for key in ("run_id", "executor_id", "authorizer_id"):
            if type(expectation[key]) is not str or OPAQUE.fullmatch(expectation[key]) is None:
                raise RollbackEvidenceInspectUnavailable
        if expectation["executor_id"] == expectation["authorizer_id"]:
            raise RollbackEvidenceInspectUnavailable
        if type(expectation["source_commit"]) is not str or COMMIT.fullmatch(expectation["source_commit"]) is None:
            raise RollbackEvidenceInspectUnavailable
        if type(expectation["candidate_image_ref"]) is not str or IMAGE.fullmatch(expectation["candidate_image_ref"]) is None:
            raise RollbackEvidenceInspectUnavailable
        if type(expectation["rollback_evidence_sha256"]) is not str or SHA256.fullmatch(expectation["rollback_evidence_sha256"]) is None:
            raise RollbackEvidenceInspectUnavailable
        start, expectation_end = (
            _timestamp(expectation["valid_from"]), _timestamp(expectation["valid_until"]),
        )
        if authorization is not None and (
            type(authorization) is not StagingRunAuthorization
            or expectation["run_id"] != authorization.run_id
            or expectation["source_commit"] != authorization.source_commit
            or expectation["candidate_image_ref"] != authorization.image_ref
            or expectation["executor_id"] != authorization.executor_id
            or expectation["authorizer_id"] != authorization.authorizer_id
            or start != authorization.valid_from.astimezone(UTC)
            or expectation_end != authorization.valid_until.astimezone(UTC)
        ):
            return False
        now = clock()
        if type(now) is not datetime or now.tzinfo is None or expectation_end <= start:
            raise RollbackEvidenceInspectUnavailable
        now = now.astimezone(UTC)
        if not start <= now <= expectation_end:
            return False
        if hashlib.sha256(raw).hexdigest() != expectation["rollback_evidence_sha256"]:
            return False
        if set(evidence) != EVIDENCE_KEYS or evidence["schema_version"] != 1:
            raise RollbackEvidenceInspectUnavailable
        if evidence["environment"] != "staging" or evidence["status"] != "verified":
            return False
        if (
            evidence["source_commit"] != expectation["source_commit"]
            or evidence["candidate_image_ref"] != expectation["candidate_image_ref"]
        ):
            return False
        for key in ("previous_healthy_image_ref", "rollback_target_image_ref"):
            if type(evidence[key]) is not str or IMAGE.fullmatch(evidence[key]) is None:
                raise RollbackEvidenceInspectUnavailable
        if (
            evidence["previous_healthy_image_ref"]
            != evidence["rollback_target_image_ref"]
            or evidence["previous_healthy_image_ref"] == evidence["candidate_image_ref"]
        ):
            return False
        for key in ("backup_snapshot_ref", "prepared_by", "reviewed_by"):
            if type(evidence[key]) is not str or OPAQUE.fullmatch(evidence[key]) is None:
                raise RollbackEvidenceInspectUnavailable
        if evidence["prepared_by"] == evidence["reviewed_by"]:
            return False
        for key in ("backup_evidence_sha256", "restore_evidence_sha256"):
            if type(evidence[key]) is not str or SHA256.fullmatch(evidence[key]) is None:
                raise RollbackEvidenceInspectUnavailable
        created, verified, evidence_end = (
            _timestamp(evidence["created_at"]), _timestamp(evidence["verified_at"]),
            _timestamp(evidence["valid_until"]),
        )
        return created <= verified <= now <= evidence_end <= expectation_end
    except RollbackEvidenceInspectUnavailable:
        raise
    except Exception:
        raise RollbackEvidenceInspectUnavailable from None


def inspect(
    expectation_file: Path, evidence_file: Path,
    *, authorization: StagingRunAuthorization | None = None,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    result = inspect_rollback_evidence(
        expectation_file, evidence_file, authorization=authorization, clock=clock,
    )
    return (json.dumps({
        "schema_version": 1, "phase": "rollback",
        "facts": {"rollback_current": result},
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-rollback-evidence-inspect", add_help=False)
    parser.add_argument("--expectation-file", required=True, type=Path)
    parser.add_argument("--evidence-file", required=True, type=Path)
    try:
        values = parser.parse_args(argv)
        sys.stdout.buffer.write(inspect(values.expectation_file, values.evidence_file))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
