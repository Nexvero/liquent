from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

import liquent_platform.operators.staging_read_only_probe_cli as cli
from liquent_platform.operators.staging_process_adapter import (
    FACT_KEYS, ProcessObservation, ReducedPhaseOutput,
)
from liquent_platform.persistence.migrations import expected_head


NOW = datetime(2026, 8, 20, 14, tzinfo=UTC)
APP_IMAGE = "registry.example/liquent@sha256:" + "b" * 64


def _private(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _setup(tmp_path: Path):
    docker = tmp_path / "docker"
    docker.write_text("executable")
    os.chmod(docker, 0o700)
    compose = tmp_path / "compose.yaml"
    compose.write_text("name: bound\n")
    runtime = _private(tmp_path / "runtime.env", "LIQUENT_JOB_CONCURRENCY=1\n")
    images = _private(tmp_path / "images.env", "\n".join((
        f"LIQUENT_APP_IMAGE={APP_IMAGE}",
        "LIQUENT_POSTGRES_IMAGE=postgres@sha256:" + "1" * 64,
        "LIQUENT_PROMETHEUS_IMAGE=prom/prometheus@sha256:" + "2" * 64,
        "LIQUENT_GRAFANA_IMAGE=grafana/grafana@sha256:" + "3" * 64,
        "LIQUENT_BACKUP_IMAGE=registry.example/backup@sha256:" + "4" * 64,
        "LIQUENT_SECRETS_DIR=/private/not-emitted",
    )) + "\n")
    authorization = {
        "schema_version": 1, "run_id": "lq312-run", "environment": "staging",
        "source_commit": "a" * 40, "image_ref": APP_IMAGE,
        "compose_sha256": hashlib.sha256(compose.read_bytes()).hexdigest(),
        "migration_head": expected_head(), "executor_id": "executor-312",
        "authorizer_id": "authorizer-312", "valid_from": "2026-08-20T13:00:00Z",
        "valid_until": "2026-08-20T15:00:00Z",
    }
    auth = _private(tmp_path / "authorization.json", json.dumps(authorization))
    return docker, auth, compose, runtime, images


class Processes:
    def __init__(self, output): self.output, self.calls = output, []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return ProcessObservation(0, self.output, b"", False, False, False)


def _image_output() -> bytes:
    return json.dumps([{"RepoDigests": [APP_IMAGE], "Config": {
        "User": "10001:10001",
        "Labels": {"org.opencontainers.image.revision": "a" * 40},
    }}]).encode()


def _compose_output() -> bytes:
    worker = {
        "image": APP_IMAGE,
        "command": ["liquent-research-worker", "--configuration", "/run/liquent/research-worker.json", "--database-url-file", "/run/secrets/database_url"],
        "networks": {"application": None, "data": None, "observability": None},
        "volumes": [
            {"type": "bind", "source": "/private/a", "target": "/run/liquent/research-worker.json", "read_only": True, "bind": {}},
            {"type": "bind", "source": "/private/b", "target": "/run/liquent/research-worker-id", "read_only": True, "bind": {}},
            {"type": "bind", "source": "/private/c", "target": "/var/lib/liquent/research-data", "read_only": True, "bind": {}},
            {"type": "volume", "source": "artifacts", "target": "/var/lib/liquent/artifacts", "read_only": False, "volume": {}},
        ],
        "secrets": [{"source": "database_url", "target": "database_url", "uid": "10001", "gid": "10001", "mode": 256}],
        "stop_grace_period": "60s",
        "environment": {"LIQUENT_JOB_CONCURRENCY": "1", "LIQUENT_TRADING_CONNECTIVITY": "disabled"},
    }
    services = {name: {} for name in ("migration-gate", "control-plane", "postgres", "prometheus", "grafana", "backup")}
    services["research-worker"] = worker
    return json.dumps({"services": services}).encode()


@pytest.mark.parametrize("phase", ["image_digest", "image_revision", "runtime_identity"])
def test_image_phases_execute_only_exact_image_inspect(tmp_path: Path, phase: str) -> None:
    docker, auth, compose, runtime, images = _setup(tmp_path)
    processes = Processes(_image_output())
    result = cli.run_read_only_probe(
        phase=phase, docker_executable=docker, authorization_file=auth,
        compose_file=compose, runtime_environment_file=runtime,
        image_environment_file=images, project_name="liquent-lq312-run",
        processes=processes, clock=lambda: NOW,
    )
    argv, options = processes.calls[0]
    assert argv == (str(docker), "image", "inspect", APP_IMAGE)
    assert options["environment"] == {"LANG": "C", "LC_ALL": "C"}
    assert options["maximum_output_bytes"] == 1_048_576
    assert result.status == "passed"


@pytest.mark.parametrize("phase", [
    "compose_render", "trading_disabled", "command", "networks", "mounts",
    "secret_mount", "grace",
])
def test_compose_phases_execute_only_bound_config_json(tmp_path: Path, phase: str) -> None:
    docker, auth, compose, runtime, images = _setup(tmp_path)
    processes = Processes(_compose_output())
    result = cli.run_read_only_probe(
        phase=phase, docker_executable=docker, authorization_file=auth,
        compose_file=compose, runtime_environment_file=runtime,
        image_environment_file=images, project_name="liquent-lq312-run",
        processes=processes, clock=lambda: NOW,
    )
    argv, options = processes.calls[0]
    assert argv == (
        str(docker), "compose", "--env-file", str(runtime), "--env-file", str(images),
        "--file", str(compose), "--project-name", "liquent-lq312-run",
        "config", "--format", "json",
    )
    assert options["maximum_output_bytes"] == 2_097_152
    assert result.status == "passed"


def test_binding_mismatch_stops_before_process_access(tmp_path: Path) -> None:
    docker, auth, compose, runtime, images = _setup(tmp_path)
    processes = Processes(_image_output())
    compose.write_text("changed\n")
    with pytest.raises(cli.StagingReadOnlyProbeCliUnavailable):
        cli.run_read_only_probe(
            phase="image_digest", docker_executable=docker, authorization_file=auth,
            compose_file=compose, runtime_environment_file=runtime,
            image_environment_file=images, project_name="liquent-lq312-run",
            processes=processes, clock=lambda: NOW,
        )
    assert processes.calls == []


@pytest.mark.parametrize("phase", ["migration_gate", "running_sigterm"])
def test_unimplemented_phase_is_unavailable_before_docker(tmp_path: Path, phase: str) -> None:
    docker, auth, compose, runtime, images = _setup(tmp_path)
    processes = Processes(b"private")
    with pytest.raises(cli.StagingReadOnlyProbeCliUnavailable):
        cli.run_read_only_probe(
            phase=phase, docker_executable=docker, authorization_file=auth,
            compose_file=compose, runtime_environment_file=runtime,
            image_environment_file=images, project_name="liquent-lq312-run",
            processes=processes, clock=lambda: NOW,
        )
    assert processes.calls == []


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    reduced = ReducedPhaseOutput(
        "image_digest", "passed",
        json.dumps({"schema_version": 1, "phase": "image_digest", "facts": {FACT_KEYS["image_digest"]: True}}, sort_keys=True, separators=(",", ":")).encode() + b"\n",
    )
    monkeypatch.setattr(cli, "run_read_only_probe", lambda **_: reduced)
    arguments = [
        "--phase", "image_digest", "--docker-executable", "/x/docker",
        "--authorization-file", "/x/auth", "--compose-file", "/x/compose",
        "--runtime-env-file", "/x/runtime", "--image-env-file", "/x/images",
        "--project-name", "liquent-run",
    ]
    assert cli.main(arguments) == 0
    assert capsys.readouterr().out.encode() == reduced.content
    assert cli.main(["--phase", "image_digest"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
