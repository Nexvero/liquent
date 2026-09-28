"""Controlled state machine for one authorized staging evidence run."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.persistence.migrations import expected_head


PHASES = (
    "image_digest", "image_revision", "entrypoint", "runtime_identity",
    "disposable_postgres", "rollback", "trading_disabled", "compose_render",
    "command", "networks", "mounts", "secret_mount", "grace",
    "input_ownership", "data_read_only", "artifact_capabilities",
    "migration_gate", "migration_head", "idle_start", "idle_no_mutation",
    "log_redaction", "authorized_acceptance", "claim_heartbeat",
    "terminal_outcome", "artifact_integrity", "revocation", "idle_sigterm",
    "running_sigterm", "no_sigkill",
)
AUTHORIZATION_KEYS = {
    "schema_version", "run_id", "environment", "source_commit", "image_ref",
    "compose_sha256", "migration_head", "executor_id", "authorizer_id",
    "valid_from", "valid_until",
}
OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
IMAGE = re.compile(r"[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}\Z")


class StagingExecutorUnavailable(Exception):
    code = "research_worker_staging_executor_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class StagingRunAuthorization:
    run_id: str
    source_commit: str
    image_ref: str
    compose_sha256: str
    migration_head: str
    executor_id: str
    authorizer_id: str
    valid_from: datetime
    valid_until: datetime

    def __repr__(self) -> str:
        return "StagingRunAuthorization()"


@dataclass(frozen=True, slots=True)
class StagingPhaseEvidence:
    status: str
    evidence_ref: str | None
    evidence_sha256: str | None

    def __post_init__(self) -> None:
        if self.status not in {"passed", "failed", "unavailable"}:
            raise ValueError("invalid staging evidence status")
        if self.status == "unavailable":
            if self.evidence_ref is not None or self.evidence_sha256 is not None:
                raise ValueError("unavailable evidence must have no reference")
        elif (
            type(self.evidence_ref) is not str
            or OPAQUE.fullmatch(self.evidence_ref) is None
            or type(self.evidence_sha256) is not str
            or SHA256.fullmatch(self.evidence_sha256) is None
        ):
            raise ValueError("executed evidence must be opaque and hashed")


class StagingPhaseRunner(Protocol):
    def run(self, phase: str, authorization: StagingRunAuthorization) -> StagingPhaseEvidence: ...


def _timestamp(value: object) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise StagingExecutorUnavailable
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise StagingExecutorUnavailable from None
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise StagingExecutorUnavailable
    return parsed


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise StagingExecutorUnavailable
        result[key] = value
    return result


def load_staging_run_authorization(
    path: Path, *, clock=lambda: datetime.now(UTC),
) -> StagingRunAuthorization:
    try:
        value = json.loads(_private_file(path, 16_384), object_pairs_hook=_pairs)
        if type(value) is not dict or set(value) != AUTHORIZATION_KEYS:
            raise StagingExecutorUnavailable
        if value["schema_version"] != 1 or value["environment"] != "staging":
            raise StagingExecutorUnavailable
        for name in ("run_id", "executor_id", "authorizer_id"):
            if type(value[name]) is not str or OPAQUE.fullmatch(value[name]) is None:
                raise StagingExecutorUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise StagingExecutorUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise StagingExecutorUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise StagingExecutorUnavailable
        if type(value["compose_sha256"]) is not str or SHA256.fullmatch(value["compose_sha256"]) is None:
            raise StagingExecutorUnavailable
        if value["migration_head"] != expected_head():
            raise StagingExecutorUnavailable
        valid_from, valid_until, now = (
            _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock()
        )
        if type(now) is not datetime or now.tzinfo is None:
            raise StagingExecutorUnavailable
        now = now.astimezone(UTC)
        if valid_from > now or valid_until < now or valid_until <= valid_from:
            raise StagingExecutorUnavailable
        return StagingRunAuthorization(
            value["run_id"], value["source_commit"], value["image_ref"],
            value["compose_sha256"], value["migration_head"],
            value["executor_id"], value["authorizer_id"], valid_from, valid_until,
        )
    except StagingExecutorUnavailable:
        raise
    except Exception:
        raise StagingExecutorUnavailable from None


def execute_staging_run(
    authorization: StagingRunAuthorization,
    runner: StagingPhaseRunner,
    output_directory: Path,
    *,
    clock=lambda: datetime.now(UTC),
) -> Path:
    """Run phases once and atomically create an undecided evidence record."""

    try:
        if type(authorization) is not StagingRunAuthorization:
            raise StagingExecutorUnavailable
        now = clock()
        if type(now) is not datetime or now.tzinfo is None:
            raise StagingExecutorUnavailable
        now = now.astimezone(UTC)
        if now < authorization.valid_from or now > authorization.valid_until:
            raise StagingExecutorUnavailable
        if not isinstance(output_directory, Path) or not output_directory.is_absolute():
            raise StagingExecutorUnavailable
        metadata = output_directory.stat()
        if not output_directory.is_dir() or metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
            raise StagingExecutorUnavailable
        if any(output_directory.iterdir()):
            raise StagingExecutorUnavailable

        checks: dict[str, dict[str, object]] = {}
        stopped = False
        for phase in PHASES:
            if stopped:
                evidence = StagingPhaseEvidence("unavailable", None, None)
            else:
                try:
                    evidence = runner.run(phase, authorization)
                    if type(evidence) is not StagingPhaseEvidence:
                        raise StagingExecutorUnavailable
                except Exception:
                    evidence = StagingPhaseEvidence("unavailable", None, None)
                stopped = evidence.status != "passed"
            checks[phase] = {
                "status": evidence.status,
                "evidence_ref": evidence.evidence_ref,
                "evidence_sha256": evidence.evidence_sha256,
            }

        observed = now.isoformat().replace("+00:00", "Z")
        review_by = authorization.valid_until.isoformat().replace("+00:00", "Z")
        record = {
            "schema_version": 1, "run_id": authorization.run_id,
            "environment": "staging", "source_commit": authorization.source_commit,
            "image_ref": authorization.image_ref,
            "compose_sha256": authorization.compose_sha256,
            "migration_head": authorization.migration_head,
            "observed_at": observed, "review_by": review_by,
            "prepared_by": authorization.executor_id,
            "reviewed_by": authorization.authorizer_id, "checks": checks,
        }
        content = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        temporary = output_directory / f".{authorization.run_id}-{uuid.uuid4().hex}.tmp"
        final = output_directory / f"{authorization.run_id}.json"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            remaining = memoryview(content)
            while remaining:
                written = os.write(descriptor, remaining)
                if written < 1:
                    raise StagingExecutorUnavailable
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        try:
            os.link(temporary, final)
            directory = os.open(output_directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            os.unlink(temporary)
        return final
    except StagingExecutorUnavailable:
        raise
    except Exception:
        raise StagingExecutorUnavailable from None
