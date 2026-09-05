"""Owner-controlled read-only-then-write artifact probe recovery composition."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import (
    AUTHORIZATION_KEYS, COMMIT, IMAGE, OPAQUE, SHA256, StagingRunAuthorization,
    _timestamp,
)
from liquent_platform.operators.staging_process_adapter import (
    LocalBoundedProcessRunner, ProcessObservation,
)
from liquent_platform.operators.staging_read_only_probe import evaluate_read_only_phase
from liquent_platform.operators.staging_read_only_probe_cli import (
    ENV_KEYS, _environment_file, _runtime_inputs,
)
from liquent_platform.persistence.migrations import expected_head


RECOVERY_KEYS = {
    "schema_version", "recovery_id", "run_id", "phase", "source_commit",
    "image_ref", "compose_sha256", "executor_id", "authorizer_id",
    "valid_from", "valid_until",
}


class ArtifactProbeRecoveryUnavailable(Exception):
    code = "artifact_probe_recovery_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class RecoveryAuthorization:
    recovery_id: str
    run_id: str
    source_commit: str
    image_ref: str
    compose_sha256: str
    executor_id: str
    authorizer_id: str
    valid_from: datetime
    valid_until: datetime

    def __repr__(self) -> str:
        return "RecoveryAuthorization()"


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise ArtifactProbeRecoveryUnavailable


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ArtifactProbeRecoveryUnavailable
        result[key] = value
    return result


def _json_private(path: Path) -> dict:
    try:
        value = json.loads(_private_file(path, 16_384), object_pairs_hook=_pairs)
        if type(value) is not dict:
            raise ArtifactProbeRecoveryUnavailable
        return value
    except ArtifactProbeRecoveryUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryUnavailable from None


def _historical_authorization(path: Path) -> StagingRunAuthorization:
    value = _json_private(path)
    try:
        if set(value) != AUTHORIZATION_KEYS or value["schema_version"] != 1:
            raise ArtifactProbeRecoveryUnavailable
        if value["environment"] != "staging" or value["migration_head"] != expected_head():
            raise ArtifactProbeRecoveryUnavailable
        for key in ("run_id", "executor_id", "authorizer_id"):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise ArtifactProbeRecoveryUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise ArtifactProbeRecoveryUnavailable
        if COMMIT.fullmatch(value["source_commit"]) is None:
            raise ArtifactProbeRecoveryUnavailable
        if IMAGE.fullmatch(value["image_ref"]) is None:
            raise ArtifactProbeRecoveryUnavailable
        if SHA256.fullmatch(value["compose_sha256"]) is None:
            raise ArtifactProbeRecoveryUnavailable
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        if end <= start:
            raise ArtifactProbeRecoveryUnavailable
        return StagingRunAuthorization(
            value["run_id"], value["source_commit"], value["image_ref"],
            value["compose_sha256"], value["migration_head"], value["executor_id"],
            value["authorizer_id"], start, end,
        )
    except ArtifactProbeRecoveryUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryUnavailable from None


def _recovery_authorization(path: Path, *, clock) -> RecoveryAuthorization:
    value = _json_private(path)
    try:
        if set(value) != RECOVERY_KEYS or value["schema_version"] != 1:
            raise ArtifactProbeRecoveryUnavailable
        if value["phase"] != "artifact_capabilities":
            raise ArtifactProbeRecoveryUnavailable
        for key in ("recovery_id", "run_id", "executor_id", "authorizer_id"):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise ArtifactProbeRecoveryUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise ArtifactProbeRecoveryUnavailable
        if COMMIT.fullmatch(value["source_commit"]) is None:
            raise ArtifactProbeRecoveryUnavailable
        if IMAGE.fullmatch(value["image_ref"]) is None:
            raise ArtifactProbeRecoveryUnavailable
        if SHA256.fullmatch(value["compose_sha256"]) is None:
            raise ArtifactProbeRecoveryUnavailable
        start, end, now = (
            _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock(),
        )
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
        ):
            raise ArtifactProbeRecoveryUnavailable
        now = now.astimezone(UTC)
        if not start <= now <= end:
            raise ArtifactProbeRecoveryUnavailable
        return RecoveryAuthorization(
            value["recovery_id"], value["run_id"], value["source_commit"],
            value["image_ref"], value["compose_sha256"], value["executor_id"],
            value["authorizer_id"], start, end,
        )
    except ArtifactProbeRecoveryUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryUnavailable from None


def _observe(runner, argv: tuple[str, ...], *, maximum: int) -> ProcessObservation:
    with tempfile.TemporaryDirectory(prefix="liquent-artifact-recovery-") as directory:
        value = runner.run(
            argv, cwd=Path(directory), environment={"LANG": "C", "LC_ALL": "C"},
            timeout_seconds=60.0, maximum_output_bytes=maximum,
            terminate_grace_seconds=5.0,
        )
    if (
        type(value) is not ProcessObservation or value.returncode != 0 or value.stderr
        or value.timed_out or value.truncated or value.hard_killed
    ):
        raise ArtifactProbeRecoveryUnavailable
    return value


def _outcome(raw: bytes, *, operation: str, allowed: set[str]) -> str:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        key = "inspection" if operation == "artifact_probe_recovery" else "operation"
        if (
            type(value) is not dict or set(value) != {"schema_version", key, "outcome"}
            or value["schema_version"] != 1 or value[key] != operation
            or value["outcome"] not in allowed
        ):
            raise ArtifactProbeRecoveryUnavailable
        return value["outcome"]
    except ArtifactProbeRecoveryUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryUnavailable from None


def recover_artifact_probe(
    *, docker_executable: Path, authorization_file: Path, recovery_file: Path,
    compose_file: Path, runtime_environment_file: Path,
    image_environment_file: Path, project_name: str, processes=None,
    evidence_directory: Path, clock=lambda: datetime.now(UTC),
) -> bytes:
    lock = None
    try:
        original = _historical_authorization(authorization_file)
        recovery = _recovery_authorization(recovery_file, clock=clock)
        if (
            recovery.run_id != original.run_id
            or recovery.source_commit != original.source_commit
            or recovery.image_ref != original.image_ref
            or recovery.compose_sha256 != original.compose_sha256
            or project_name != f"liquent-{original.run_id}" or len(project_name) > 63
        ):
            raise ArtifactProbeRecoveryUnavailable
        binding = {
            "schema_version": 1, "recovery_id": recovery.recovery_id,
            "run_id": original.run_id, "phase": "artifact_capabilities",
            "source_commit": original.source_commit, "image_ref": original.image_ref,
            "compose_sha256": original.compose_sha256,
            "executor_id": recovery.executor_id,
            "authorizer_id": recovery.authorizer_id,
        }
        evidence_root = _evidence_root(evidence_directory)
        stem = hashlib.sha256(recovery.recovery_id.encode()).hexdigest()
        final = evidence_directory / f"{stem}.json"
        existing = _existing_evidence(final, binding)
        if existing is not None:
            return _result(existing)
        lock = evidence_directory / f".{stem}.claim"
        descriptor = os.open(
            lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
        )
        try:
            os.write(descriptor, b"artifact-probe-recovery\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(evidence_root)
        if (
            not docker_executable.is_absolute() or not docker_executable.is_file()
            or not os.access(docker_executable, os.X_OK) or not compose_file.is_absolute()
            or compose_file.is_symlink() or not compose_file.is_file()
            or hashlib.sha256(compose_file.read_bytes()).hexdigest() != original.compose_sha256
        ):
            raise ArtifactProbeRecoveryUnavailable
        _private_file(runtime_environment_file, 32_768)
        images = _environment_file(image_environment_file)
        if set(images) != ENV_KEYS or images["LIQUENT_APP_IMAGE"] != original.image_ref:
            raise ArtifactProbeRecoveryUnavailable
        runner = processes or LocalBoundedProcessRunner()
        compose_argv = (
            str(docker_executable), "compose", "--env-file", str(runtime_environment_file),
            "--env-file", str(image_environment_file), "--file", str(compose_file),
            "--project-name", project_name, "config", "--format", "json",
        )
        rendered = _observe(runner, compose_argv, maximum=1_048_576).stdout
        for phase in (
            "compose_render", "trading_disabled", "command", "networks", "mounts",
            "secret_mount", "grace",
        ):
            if evaluate_read_only_phase(
                phase, original, compose_model=rendered,
            ).status != "passed":
                raise ArtifactProbeRecoveryUnavailable
        image, _, volume = _runtime_inputs(rendered, original.image_ref)
        token = hashlib.sha256(
            f"{project_name}:artifact_capabilities".encode()
        ).hexdigest()
        base = (
            str(docker_executable), "run", "--rm", "--pull", "never", "--network",
            "none", "--read-only", "--user", "10001:10001", "--security-opt",
            "no-new-privileges", "--cap-drop", "ALL", "--pids-limit", "64",
            "--memory", "128m", "--cpus", "0.25", "--log-driver", "none",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m",
        )
        inspect_argv = base + (
            "--name", "liquent-recovery-inspect-" + token[:20], "--mount",
            f"type=volume,source={volume},target=/var/lib/liquent/artifacts,readonly",
            "--entrypoint", "/opt/liquent/venv/bin/liquent-artifact-probe-recovery-inspect",
            image, "--run-token", token,
        )
        inspected = _outcome(
            _observe(runner, inspect_argv, maximum=65_536).stdout,
            operation="artifact_probe_recovery",
            allowed={"absent", "recoverable", "conflict"},
        )
        if inspected != "recoverable":
            result = "already_absent" if inspected == "absent" else "conflict"
        else:
            remove_argv = base + (
                "--name", "liquent-recovery-remove-" + token[:20], "--mount",
                f"type=volume,source={volume},target=/var/lib/liquent/artifacts",
                "--entrypoint", "/opt/liquent/venv/bin/liquent-artifact-probe-recovery-remove",
                image, "--run-token", token,
            )
            result = _outcome(
                _observe(runner, remove_argv, maximum=65_536).stdout,
                operation="artifact_probe_recovery_remove",
                allowed={"already_absent", "removed", "conflict"},
            )
        record = dict(binding)
        record["outcome"] = result
        record["completed_at"] = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        _store_evidence(evidence_directory, evidence_root, final, record)
        os.unlink(lock)
        lock = None
        os.fsync(evidence_root)
        return _result(result)
    except ArtifactProbeRecoveryUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryUnavailable from None
    finally:
        if "evidence_root" in locals():
            os.close(evidence_root)


def _evidence_root(path: Path) -> int:
    try:
        if not isinstance(path, Path) or not path.is_absolute() or path.is_symlink():
            raise ArtifactProbeRecoveryUnavailable
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            os.close(descriptor)
            raise ArtifactProbeRecoveryUnavailable
        return descriptor
    except ArtifactProbeRecoveryUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryUnavailable from None


def _existing_evidence(path: Path, binding: dict) -> str | None:
    try:
        if not path.exists():
            return None
        metadata = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ArtifactProbeRecoveryUnavailable
        value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
        if (
            type(value) is not dict or set(value) != set(binding) | {"outcome", "completed_at"}
            or any(value[key] != expected for key, expected in binding.items())
            or value["outcome"] not in {
                "already_absent", "removed", "conflict",
                "absence_confirmed_after_unknown",
            }
            or type(value["completed_at"]) is not str
        ):
            raise ArtifactProbeRecoveryUnavailable
        return value["outcome"]
    except ArtifactProbeRecoveryUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryUnavailable from None


def _store_evidence(root: Path, root_descriptor: int, final: Path, record: dict) -> None:
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
                raise ArtifactProbeRecoveryUnavailable
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.link(temporary, final)
        temporary.unlink()
        os.fsync(root_descriptor)
        if _existing_evidence(final, {key: record[key] for key in record if key not in {"outcome", "completed_at"}}) != record["outcome"]:
            raise ArtifactProbeRecoveryUnavailable
    except ArtifactProbeRecoveryUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "artifact_probe_recovery", "outcome": outcome,
        "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-artifact-probe-recovery", add_help=False)
    for name in (
        "docker-executable", "authorization-file", "recovery-file", "compose-file",
        "runtime-env-file", "image-env-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        values = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(recover_artifact_probe(
            docker_executable=values["docker_executable"],
            authorization_file=values["authorization_file"],
            recovery_file=values["recovery_file"], compose_file=values["compose_file"],
            runtime_environment_file=values["runtime_env_file"],
            image_environment_file=values["image_env_file"],
            project_name=values["project_name"],
            evidence_directory=values["evidence_directory"],
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
