"""Installed read-only staging probe for image inspect and Compose render."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.disposable_postgres import provision_disposable_postgres
from liquent_platform.operators.rollback_evidence_inspect import (
    inspect as inspect_rollback_evidence,
)
from liquent_platform.operators.research_worker_staging_executor import (
    load_staging_run_authorization,
)
from liquent_platform.operators.staging_process_adapter import (
    LocalBoundedProcessRunner, ProcessObservation, reduce_phase_output,
)
from liquent_platform.operators.staging_read_only_probe import (
    SUPPORTED_PHASES, evaluate_read_only_phase,
)


IMAGE_PHASES = frozenset({"image_digest", "image_revision", "runtime_identity"})
RUNTIME_PHASES = frozenset({"entrypoint", "input_ownership", "data_read_only"})
ARTIFACT_PHASES = frozenset({"artifact_capabilities"})
ROLLBACK_PHASES = frozenset({"rollback"})
POSTGRES_PHASES = frozenset({"disposable_postgres"})
CLI_PHASES = (
    SUPPORTED_PHASES | RUNTIME_PHASES | ARTIFACT_PHASES | ROLLBACK_PHASES
    | POSTGRES_PHASES
)
ENV_KEYS = {
    "LIQUENT_APP_IMAGE", "LIQUENT_POSTGRES_IMAGE", "LIQUENT_PROMETHEUS_IMAGE",
    "LIQUENT_GRAFANA_IMAGE", "LIQUENT_BACKUP_IMAGE", "LIQUENT_SECRETS_DIR",
}
IMAGE = re.compile(r"[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}\Z")


class StagingReadOnlyProbeCliUnavailable(Exception):
    code = "staging_read_only_probe_cli_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise StagingReadOnlyProbeCliUnavailable


def _environment_file(path: Path) -> dict[str, str]:
    raw = _private_file(path, 32_768)
    try:
        values = {}
        for line in raw.decode("utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            if line.count("=") != 1:
                raise StagingReadOnlyProbeCliUnavailable
            key, value = line.split("=", 1)
            if key in values or not key or not value:
                raise StagingReadOnlyProbeCliUnavailable
            values[key] = value
        return values
    except StagingReadOnlyProbeCliUnavailable:
        raise
    except Exception:
        raise StagingReadOnlyProbeCliUnavailable from None


def run_read_only_probe(
    *, phase: str, docker_executable: Path, authorization_file: Path,
    compose_file: Path, runtime_environment_file: Path,
    image_environment_file: Path, project_name: str,
    rollback_expectation_file: Path | None = None,
    rollback_evidence_file: Path | None = None,
    processes=None, clock=lambda: datetime.now(UTC),
):
    try:
        if phase not in CLI_PHASES:
            raise StagingReadOnlyProbeCliUnavailable
        rollback_inputs = (rollback_expectation_file, rollback_evidence_file)
        if (phase == "rollback") != all(value is not None for value in rollback_inputs):
            raise StagingReadOnlyProbeCliUnavailable
        if phase != "rollback" and any(value is not None for value in rollback_inputs):
            raise StagingReadOnlyProbeCliUnavailable
        authorization = load_staging_run_authorization(authorization_file, clock=clock)
        if project_name != f"liquent-{authorization.run_id}" or len(project_name) > 63:
            raise StagingReadOnlyProbeCliUnavailable
        if (
            not isinstance(docker_executable, Path) or not docker_executable.is_absolute()
            or not docker_executable.is_file() or not os.access(docker_executable, os.X_OK)
            or not isinstance(compose_file, Path) or not compose_file.is_absolute()
            or compose_file.is_symlink() or not compose_file.is_file()
        ):
            raise StagingReadOnlyProbeCliUnavailable
        compose_bytes = compose_file.read_bytes()
        if hashlib.sha256(compose_bytes).hexdigest() != authorization.compose_sha256:
            raise StagingReadOnlyProbeCliUnavailable
        _private_file(runtime_environment_file, 32_768)
        image_values = _environment_file(image_environment_file)
        if set(image_values) != ENV_KEYS:
            raise StagingReadOnlyProbeCliUnavailable
        if any(
            IMAGE.fullmatch(image_values[name]) is None
            for name in ENV_KEYS if name.endswith("_IMAGE")
        ) or image_values["LIQUENT_APP_IMAGE"] != authorization.image_ref:
            raise StagingReadOnlyProbeCliUnavailable

        if phase == "rollback":
            content = inspect_rollback_evidence(
                rollback_expectation_file, rollback_evidence_file,
                authorization=authorization, clock=clock,
            )
            return reduce_phase_output(
                "rollback", ProcessObservation(
                    0, content, b"", False, False, False,
                ),
            )

        runner = processes or LocalBoundedProcessRunner()
        with tempfile.TemporaryDirectory(prefix="liquent-staging-probe-") as directory:
            cwd = Path(directory)
            if phase in IMAGE_PHASES:
                argv = (
                    str(docker_executable), "image", "inspect", authorization.image_ref,
                )
                maximum = 1_048_576
            else:
                argv = (
                    str(docker_executable), "compose",
                    "--env-file", str(runtime_environment_file),
                    "--env-file", str(image_environment_file),
                    "--file", str(compose_file),
                    "--project-name", project_name,
                    "config", "--format", "json",
                )
                maximum = 2_097_152
            observation = runner.run(
                argv, cwd=cwd, environment={"LANG": "C", "LC_ALL": "C"},
                timeout_seconds=60.0, maximum_output_bytes=maximum,
                terminate_grace_seconds=5.0,
            )
        if (
            observation.returncode != 0 or observation.stderr or observation.timed_out
            or observation.truncated or observation.hard_killed
        ):
            raise StagingReadOnlyProbeCliUnavailable
        if phase in IMAGE_PHASES:
            return evaluate_read_only_phase(
                phase, authorization, image_inspection=observation.stdout,
            )
        if phase == "disposable_postgres":
            return provision_disposable_postgres(
                docker_executable=docker_executable, compose_file=compose_file,
                runtime_environment_file=runtime_environment_file,
                image_environment_file=image_environment_file,
                project_name=project_name, authorization=authorization,
                postgres_image=image_values["LIQUENT_POSTGRES_IMAGE"],
                compose_model=observation.stdout, runner=runner,
            )
        if phase in RUNTIME_PHASES | ARTIFACT_PHASES:
            for static_phase in (
                "compose_render", "trading_disabled", "command", "networks",
                "mounts", "secret_mount", "grace",
            ):
                if evaluate_read_only_phase(
                    static_phase, authorization, compose_model=observation.stdout,
                ).status != "passed":
                    raise StagingReadOnlyProbeCliUnavailable
            image, sources, artifact_volume = _runtime_inputs(
                observation.stdout, authorization.image_ref,
            )
            container = "liquent-inspect-" + hashlib.sha256(
                f"{project_name}:{phase}".encode()
            ).hexdigest()[:24]
            base = (
                str(docker_executable), "run", "--rm", "--pull", "never",
                "--name", container, "--network", "none", "--read-only",
                "--user", "10001:10001", "--security-opt", "no-new-privileges",
                "--cap-drop", "ALL", "--pids-limit", "64", "--memory", "128m",
                "--cpus", "0.25", "--log-driver", "none",
                "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m",
            )
            if phase in RUNTIME_PHASES:
                run_argv = base + (
                    "--mount", _mount(sources["/run/liquent/research-worker.json"], "/run/liquent/research-worker.json"),
                    "--mount", _mount(sources["/run/liquent/research-worker-id"], "/run/liquent/research-worker-id"),
                    "--mount", _mount(sources["/var/lib/liquent/research-data"], "/var/lib/liquent/research-data"),
                    "--entrypoint", "/opt/liquent/venv/bin/liquent-runtime-inspect",
                    image, "--phase", phase,
                )
            else:
                token = hashlib.sha256(
                    f"{project_name}:artifact_capabilities".encode()
                ).hexdigest()
                run_argv = base + (
                    "--mount", _volume_mount(
                        artifact_volume, "/var/lib/liquent/artifacts",
                    ),
                    "--entrypoint",
                    "/opt/liquent/venv/bin/liquent-artifact-capability-inspect",
                    image, "--run-token", token,
                )
            with tempfile.TemporaryDirectory(prefix="liquent-runtime-inspect-") as directory:
                runtime_observation = runner.run(
                    run_argv, cwd=Path(directory),
                    environment={"LANG": "C", "LC_ALL": "C"},
                    timeout_seconds=60.0, maximum_output_bytes=65_536,
                    terminate_grace_seconds=5.0,
                )
            return reduce_phase_output(phase, runtime_observation)
        return evaluate_read_only_phase(
            phase, authorization, compose_model=observation.stdout,
        )
    except StagingReadOnlyProbeCliUnavailable:
        raise
    except Exception:
        raise StagingReadOnlyProbeCliUnavailable from None


def _runtime_inputs(
    raw: bytes, expected_image: str,
) -> tuple[str, dict[str, str], str]:
    try:
        value = json.loads(raw)
        worker = value["services"]["research-worker"]
        if worker.get("image") != expected_image:
            raise StagingReadOnlyProbeCliUnavailable
        sources = {}
        artifact_volume = None
        expected = {
            "/run/liquent/research-worker.json",
            "/run/liquent/research-worker-id",
            "/var/lib/liquent/research-data",
        }
        for volume in worker["volumes"]:
            target = volume.get("target")
            if target == "/var/lib/liquent/artifacts":
                source = volume.get("source")
                if (
                    artifact_volume is not None or volume.get("type") != "volume"
                    or volume.get("read_only") is not False
                    or type(source) is not str
                    or re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", source) is None
                ):
                    raise StagingReadOnlyProbeCliUnavailable
                artifact_volume = source
            if target in expected:
                source = volume.get("source")
                if (
                    volume.get("type") != "bind" or volume.get("read_only") is not True
                    or type(source) is not str or not Path(source).is_absolute()
                    or any(character in source for character in (",", "\0", "\n", "\r"))
                    or target in sources
                ):
                    raise StagingReadOnlyProbeCliUnavailable
                sources[target] = source
        if set(sources) != expected or artifact_volume is None:
            raise StagingReadOnlyProbeCliUnavailable
        return expected_image, sources, artifact_volume
    except StagingReadOnlyProbeCliUnavailable:
        raise
    except Exception:
        raise StagingReadOnlyProbeCliUnavailable from None


def _mount(source: str, target: str) -> str:
    return f"type=bind,source={source},target={target},readonly"


def _volume_mount(source: str, target: str) -> str:
    return f"type=volume,source={source},target={target}"


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-staging-phase-probe", add_help=False)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--docker-executable", required=True, type=Path)
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--compose-file", required=True, type=Path)
    parser.add_argument("--runtime-env-file", required=True, type=Path)
    parser.add_argument("--image-env-file", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--rollback-expectation-file", type=Path)
    parser.add_argument("--rollback-evidence-file", type=Path)
    try:
        arguments = parser.parse_args(argv)
        result = run_read_only_probe(
            phase=arguments.phase,
            docker_executable=arguments.docker_executable,
            authorization_file=arguments.authorization_file,
            compose_file=arguments.compose_file,
            runtime_environment_file=arguments.runtime_env_file,
            image_environment_file=arguments.image_env_file,
            project_name=arguments.project_name,
            rollback_expectation_file=arguments.rollback_expectation_file,
            rollback_evidence_file=arguments.rollback_evidence_file,
        )
        sys.stdout.buffer.write(result.content)
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
