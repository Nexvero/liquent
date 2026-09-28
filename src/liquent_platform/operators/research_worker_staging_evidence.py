"""Offline, detail-free verifier for one research-worker staging evidence set."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.persistence.migrations import expected_head


CHECKS = {
    "image_digest", "image_revision", "entrypoint", "runtime_identity",
    "disposable_postgres", "rollback", "trading_disabled", "compose_render",
    "command", "networks", "mounts", "secret_mount", "grace",
    "input_ownership", "data_read_only", "artifact_capabilities",
    "migration_gate", "migration_head", "idle_start", "idle_no_mutation",
    "log_redaction", "authorized_acceptance", "claim_heartbeat",
    "terminal_outcome", "artifact_integrity", "revocation", "idle_sigterm",
    "running_sigterm", "no_sigkill",
}
ROOT_KEYS = {
    "schema_version", "run_id", "environment", "source_commit", "image_ref",
    "compose_sha256", "migration_head", "observed_at", "review_by",
    "prepared_by", "reviewed_by", "checks",
}
CHECK_KEYS = {"status", "evidence_ref", "evidence_sha256"}
OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
IMAGE = re.compile(r"[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}\Z")
FORBIDDEN = re.compile(
    r"(?:postgres(?:ql)?(?:\+psycopg)?://|https?://|/Users/|/home/|/run/secrets/|"
    r"/srv/|-----BEGIN|authorization|password|credential|database_url)",
    re.IGNORECASE,
)


class StagingEvidenceUnavailable(Exception):
    code = "unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


def _timestamp(value: object) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise StagingEvidenceUnavailable
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise StagingEvidenceUnavailable from None
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise StagingEvidenceUnavailable
    return parsed


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise StagingEvidenceUnavailable
        result[key] = value
    return result


def verify_staging_evidence(
    path: Path, *, clock=lambda: datetime.now(UTC),
) -> str:
    """Return only approved, rejected, or unavailable for one closed record."""

    try:
        raw = _private_file(path, 65_536)
        if FORBIDDEN.search(raw.decode("utf-8")):
            raise StagingEvidenceUnavailable
        value = json.loads(raw, object_pairs_hook=_pairs)
        if type(value) is not dict or set(value) != ROOT_KEYS:
            raise StagingEvidenceUnavailable
        if value["schema_version"] != 1 or value["environment"] != "staging":
            raise StagingEvidenceUnavailable
        if not all(
            type(value[name]) is str and OPAQUE.fullmatch(value[name])
            for name in ("run_id", "prepared_by", "reviewed_by")
        ):
            raise StagingEvidenceUnavailable
        if value["prepared_by"] == value["reviewed_by"]:
            raise StagingEvidenceUnavailable
        if type(value["source_commit"]) is not str or not COMMIT.fullmatch(value["source_commit"]):
            raise StagingEvidenceUnavailable
        if type(value["image_ref"]) is not str or not IMAGE.fullmatch(value["image_ref"]):
            raise StagingEvidenceUnavailable
        if type(value["compose_sha256"]) is not str or not SHA256.fullmatch(value["compose_sha256"]):
            raise StagingEvidenceUnavailable
        if value["migration_head"] != expected_head():
            raise StagingEvidenceUnavailable
        observed, review_by, now = (
            _timestamp(value["observed_at"]), _timestamp(value["review_by"]), clock()
        )
        if type(now) is not datetime or now.tzinfo is None:
            raise StagingEvidenceUnavailable
        now = now.astimezone(UTC)
        if observed > now or review_by < now or review_by <= observed:
            raise StagingEvidenceUnavailable
        checks = value["checks"]
        if type(checks) is not dict or set(checks) != CHECKS:
            raise StagingEvidenceUnavailable
        statuses = []
        for check in checks.values():
            if type(check) is not dict or set(check) != CHECK_KEYS:
                raise StagingEvidenceUnavailable
            status = check["status"]
            if status not in {"passed", "failed", "unavailable"}:
                raise StagingEvidenceUnavailable
            reference, digest = check["evidence_ref"], check["evidence_sha256"]
            if status == "unavailable":
                if reference is not None or digest is not None:
                    raise StagingEvidenceUnavailable
            elif (
                type(reference) is not str or not OPAQUE.fullmatch(reference)
                or type(digest) is not str or not SHA256.fullmatch(digest)
            ):
                raise StagingEvidenceUnavailable
            statuses.append(status)
        if "failed" in statuses:
            return "rejected"
        if "unavailable" in statuses:
            return "unavailable"
        return "approved"
    except StagingEvidenceUnavailable:
        return "unavailable"
    except Exception:
        return "unavailable"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="liquent-research-worker-staging-evidence")
    parser.add_argument("--evidence", required=True, type=Path)
    arguments = parser.parse_args(argv)
    decision = verify_staging_evidence(arguments.evidence)
    print(decision)
    return {"approved": 0, "rejected": 1, "unavailable": 2}[decision]


if __name__ == "__main__":
    raise SystemExit(main())
