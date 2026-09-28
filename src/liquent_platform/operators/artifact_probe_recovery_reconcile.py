"""Owner-only evidence-first reconciliation of an artifact recovery claim."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from liquent_platform.operators.artifact_probe_recovery import (
    ArtifactProbeRecoveryUnavailable, _evidence_root, _existing_evidence,
    _historical_authorization, _json_private, _observe, _outcome,
    _recovery_authorization,
)
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, OPAQUE, SHA256, _timestamp,
)
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner
from liquent_platform.operators.staging_read_only_probe import evaluate_read_only_phase
from liquent_platform.operators.staging_read_only_probe_cli import (
    ENV_KEYS, _environment_file, _runtime_inputs,
)


KEYS = {
    "schema_version", "reconciliation_id", "recovery_id", "run_id", "phase",
    "source_commit", "image_ref", "compose_sha256", "recovery_executor_id",
    "recovery_authorizer_id", "executor_id", "authorizer_id", "valid_from",
    "valid_until",
}


class ArtifactProbeRecoveryReconcileUnavailable(Exception):
    code = "artifact_probe_recovery_reconcile_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise ArtifactProbeRecoveryReconcileUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        value = _json_private(path)
        if set(value) != KEYS or value["schema_version"] != 1:
            raise ArtifactProbeRecoveryReconcileUnavailable
        if value["phase"] != "artifact_capabilities":
            raise ArtifactProbeRecoveryReconcileUnavailable
        for key in (
            "reconciliation_id", "recovery_id", "run_id", "recovery_executor_id",
            "recovery_authorizer_id", "executor_id", "authorizer_id",
        ):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise ArtifactProbeRecoveryReconcileUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise ArtifactProbeRecoveryReconcileUnavailable
        if COMMIT.fullmatch(value["source_commit"]) is None:
            raise ArtifactProbeRecoveryReconcileUnavailable
        if IMAGE.fullmatch(value["image_ref"]) is None:
            raise ArtifactProbeRecoveryReconcileUnavailable
        if SHA256.fullmatch(value["compose_sha256"]) is None:
            raise ArtifactProbeRecoveryReconcileUnavailable
        start, end, now = (
            _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock(),
        )
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
        ):
            raise ArtifactProbeRecoveryReconcileUnavailable
        if not start <= now.astimezone(UTC) <= end:
            raise ArtifactProbeRecoveryReconcileUnavailable
        return value
    except ArtifactProbeRecoveryReconcileUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryReconcileUnavailable from None


def _claim(path: Path) -> bool:
    try:
        if not path.exists():
            return False
        metadata = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or path.read_bytes() != b"artifact-probe-recovery\n"
        ):
            raise ArtifactProbeRecoveryReconcileUnavailable
        return True
    except ArtifactProbeRecoveryReconcileUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryReconcileUnavailable from None


def _reconciliation_existing(path: Path, binding: dict) -> str | None:
    try:
        if not path.exists():
            return None
        metadata = path.stat(follow_symlinks=False)
        value = json.loads(path.read_bytes())
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or type(value) is not dict
            or set(value) != set(binding) | {"outcome", "completed_at"}
            or any(value[key] != expected for key, expected in binding.items())
            or value["outcome"] not in {
                "already_finalized", "evidence_confirmed", "absence_finalized",
                "retained", "not_found",
            }
        ):
            raise ArtifactProbeRecoveryReconcileUnavailable
        return value["outcome"]
    except ArtifactProbeRecoveryReconcileUnavailable:
        raise
    except Exception:
        raise ArtifactProbeRecoveryReconcileUnavailable from None


def _write_record(root: Path, descriptor: int, final: Path, record: dict) -> None:
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
                raise ArtifactProbeRecoveryReconcileUnavailable
            view = view[written:]
        os.fsync(opened)
        os.close(opened)
        opened = None
        os.link(temporary, final)
        temporary.unlink()
        os.fsync(descriptor)
        metadata = final.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or final.read_bytes() != content
        ):
            raise ArtifactProbeRecoveryReconcileUnavailable
    except Exception:
        raise ArtifactProbeRecoveryReconcileUnavailable from None
    finally:
        if opened is not None:
            os.close(opened)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "artifact_probe_recovery_reconcile", "outcome": outcome,
        "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def reconcile_artifact_probe_claim(
    *, docker_executable: Path, authorization_file: Path, recovery_file: Path,
    reconciliation_file: Path, compose_file: Path,
    runtime_environment_file: Path, image_environment_file: Path,
    project_name: str, evidence_directory: Path, processes=None,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    evidence_root = None
    try:
        original = _historical_authorization(authorization_file)
        reconciliation = _authorization(reconciliation_file, clock=clock)
        recovery_raw = _json_private(recovery_file)
        # Historical recovery validity may be expired; validate at its own midpoint.
        recovery_start = _timestamp(recovery_raw["valid_from"])
        recovery_end = _timestamp(recovery_raw["valid_until"])
        recovery = _recovery_authorization(
            recovery_file, clock=lambda: recovery_start + (recovery_end - recovery_start) / 2,
        )
        if (
            reconciliation["recovery_id"] != recovery.recovery_id
            or reconciliation["run_id"] != original.run_id
            or reconciliation["source_commit"] != original.source_commit
            or reconciliation["image_ref"] != original.image_ref
            or reconciliation["compose_sha256"] != original.compose_sha256
            or reconciliation["recovery_executor_id"] != recovery.executor_id
            or reconciliation["recovery_authorizer_id"] != recovery.authorizer_id
            or recovery.run_id != original.run_id
            or recovery.source_commit != original.source_commit
            or recovery.image_ref != original.image_ref
            or recovery.compose_sha256 != original.compose_sha256
            or project_name != f"liquent-{original.run_id}" or len(project_name) > 63
        ):
            raise ArtifactProbeRecoveryReconcileUnavailable
        evidence_root = _evidence_root(evidence_directory)
        recovery_stem = hashlib.sha256(recovery.recovery_id.encode()).hexdigest()
        recovery_final = evidence_directory / f"{recovery_stem}.json"
        recovery_claim = evidence_directory / f".{recovery_stem}.claim"
        binding = {
            "schema_version": 1,
            "reconciliation_id": reconciliation["reconciliation_id"],
            "recovery_id": recovery.recovery_id, "run_id": original.run_id,
            "phase": "artifact_capabilities", "source_commit": original.source_commit,
            "image_ref": original.image_ref, "compose_sha256": original.compose_sha256,
            "recovery_executor_id": recovery.executor_id,
            "recovery_authorizer_id": recovery.authorizer_id,
            "executor_id": reconciliation["executor_id"],
            "authorizer_id": reconciliation["authorizer_id"],
        }
        recon_stem = hashlib.sha256(reconciliation["reconciliation_id"].encode()).hexdigest()
        recon_final = evidence_directory / f"reconciliation-{recon_stem}.json"
        recon_claim = evidence_directory / f".reconciliation-{recon_stem}.claim"
        existing_recon = _reconciliation_existing(recon_final, binding)
        if existing_recon is not None:
            changed = False
            if existing_recon in {"evidence_confirmed", "absence_finalized"} and _claim(recovery_claim):
                os.unlink(recovery_claim)
                changed = True
            if recon_claim.exists():
                metadata = recon_claim.stat(follow_symlinks=False)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != os.geteuid() or metadata.st_nlink != 1
                    or stat.S_IMODE(metadata.st_mode) != 0o600
                    or recon_claim.read_bytes()
                    != b"artifact-probe-recovery-reconciliation\n"
                ):
                    raise ArtifactProbeRecoveryReconcileUnavailable
                os.unlink(recon_claim)
                changed = True
            if changed:
                os.fsync(evidence_root)
            return _result(existing_recon)
        claim_descriptor = os.open(
            recon_claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
        )
        try:
            os.write(claim_descriptor, b"artifact-probe-recovery-reconciliation\n")
            os.fsync(claim_descriptor)
        finally:
            os.close(claim_descriptor)
        os.fsync(evidence_root)
        claim_exists = _claim(recovery_claim)
        recovery_binding = {
            "schema_version": 1, "recovery_id": recovery.recovery_id,
            "run_id": original.run_id, "phase": "artifact_capabilities",
            "source_commit": original.source_commit, "image_ref": original.image_ref,
            "compose_sha256": original.compose_sha256,
            "executor_id": recovery.executor_id, "authorizer_id": recovery.authorizer_id,
        }
        recovered = _existing_evidence(recovery_final, recovery_binding)
        if not claim_exists:
            outcome = "already_finalized" if recovered is not None else "not_found"
        elif recovered is not None:
            outcome = "evidence_confirmed"
        else:
            if (
                not docker_executable.is_absolute() or not docker_executable.is_file()
                or not os.access(docker_executable, os.X_OK) or compose_file.is_symlink()
                or hashlib.sha256(compose_file.read_bytes()).hexdigest() != original.compose_sha256
            ):
                raise ArtifactProbeRecoveryReconcileUnavailable
            _private_file(runtime_environment_file, 32_768)
            images = _environment_file(image_environment_file)
            if set(images) != ENV_KEYS or images["LIQUENT_APP_IMAGE"] != original.image_ref:
                raise ArtifactProbeRecoveryReconcileUnavailable
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
                if evaluate_read_only_phase(phase, original, compose_model=rendered).status != "passed":
                    raise ArtifactProbeRecoveryReconcileUnavailable
            image, _, volume = _runtime_inputs(rendered, original.image_ref)
            token = hashlib.sha256(f"{project_name}:artifact_capabilities".encode()).hexdigest()
            inspect_argv = (
                str(docker_executable), "run", "--rm", "--pull", "never", "--network",
                "none", "--read-only", "--user", "10001:10001", "--security-opt",
                "no-new-privileges", "--cap-drop", "ALL", "--pids-limit", "64",
                "--memory", "128m", "--cpus", "0.25", "--log-driver", "none",
                "--mount", f"type=volume,source={volume},target=/var/lib/liquent/artifacts,readonly",
                "--entrypoint", "/opt/liquent/venv/bin/liquent-artifact-probe-recovery-inspect",
                image, "--run-token", token,
            )
            inspected = _outcome(
                _observe(runner, inspect_argv, maximum=65_536).stdout,
                operation="artifact_probe_recovery",
                allowed={"absent", "recoverable", "conflict"},
            )
            if inspected == "absent":
                record = dict(recovery_binding)
                record.update({
                    "outcome": "absence_confirmed_after_unknown",
                    "completed_at": clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
                })
                _write_record(evidence_directory, evidence_root, recovery_final, record)
                outcome = "absence_finalized"
            else:
                outcome = "retained"
        recon_record = dict(binding)
        recon_record.update({
            "outcome": outcome,
            "completed_at": clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
        })
        _write_record(evidence_directory, evidence_root, recon_final, recon_record)
        if claim_exists and outcome in {"evidence_confirmed", "absence_finalized"}:
            os.unlink(recovery_claim)
            os.fsync(evidence_root)
        os.unlink(recon_claim)
        os.fsync(evidence_root)
        return _result(outcome)
    except ArtifactProbeRecoveryReconcileUnavailable:
        raise
    except ArtifactProbeRecoveryUnavailable:
        raise ArtifactProbeRecoveryReconcileUnavailable from None
    except Exception:
        raise ArtifactProbeRecoveryReconcileUnavailable from None
    finally:
        if evidence_root is not None:
            os.close(evidence_root)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-artifact-probe-recovery-reconcile", add_help=False)
    for name in (
        "docker-executable", "authorization-file", "recovery-file",
        "reconciliation-file", "compose-file", "runtime-env-file",
        "image-env-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(reconcile_artifact_probe_claim(
            docker_executable=value["docker_executable"],
            authorization_file=value["authorization_file"],
            recovery_file=value["recovery_file"],
            reconciliation_file=value["reconciliation_file"],
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
