from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import liquent_platform.operators.staging_read_only_probe_cli as cli
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from tests.test_lq312_staging_read_only_probe_cli import _setup


NOW = datetime(2026, 8, 20, 14, tzinfo=UTC)
PROJECT = "liquent-lq312-run"
POSTGRES_IMAGE = "postgres@sha256:" + "1" * 64


def _observation(
    stdout: bytes = b"", *, returncode: int = 0, stderr: bytes = b"",
    timed_out: bool = False,
) -> ProcessObservation:
    return ProcessObservation(returncode, stdout, stderr, timed_out, False, False)


class Processes:
    def __init__(self, observations):
        self.observations = list(observations)
        self.calls = []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.observations.pop(0)


def _model(*, external: bool = False) -> bytes:
    services = {name: {} for name in (
        "migration-gate", "control-plane", "research-worker", "prometheus",
        "grafana", "backup",
    )}
    services["postgres"] = {
        "image": POSTGRES_IMAGE,
        "environment": {
            "POSTGRES_DB": "liquent", "POSTGRES_USER": "liquent",
            "POSTGRES_PASSWORD_FILE": "/run/secrets/postgres_password",
        },
        "secrets": [{"source": "postgres_password", "target": "postgres_password"}],
        "networks": {"application": None, "data": None},
        "healthcheck": {"test": ["CMD-SHELL", "pg_isready -U liquent -d liquent"]},
        "security_opt": ["no-new-privileges:true"], "cap_drop": ["ALL"],
        "cap_add": ["CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"],
        "volumes": [{
            "type": "volume", "source": "postgres-data",
            "target": "/var/lib/postgresql/data",
        }],
    }
    return json.dumps({
        "services": services,
        "networks": {
            "application": {
                "name": f"{PROJECT}-application", "internal": True,
                "external": external,
            },
            "data": {"name": f"{PROJECT}-data", "internal": True},
        },
        "volumes": {
            "postgres-data": {"name": f"{PROJECT}-postgres-data"},
        },
    }).encode()


def _inspection(*, healthy: bool = True) -> bytes:
    return json.dumps([{
        "State": {"Status": "running", "Health": {
            "Status": "healthy" if healthy else "starting",
        }},
        "Config": {"Image": POSTGRES_IMAGE, "Labels": {
            "com.docker.compose.project": PROJECT,
            "com.docker.compose.service": "postgres",
        }},
        "HostConfig": {"PortBindings": {}},
        "NetworkSettings": {"Networks": {
            f"{PROJECT}-application": {}, f"{PROJECT}-data": {},
        }},
        "Mounts": [{
            "Type": "volume", "Name": f"{PROJECT}-postgres-data",
            "Destination": "/var/lib/postgresql/data",
        }],
    }]).encode()


def _run(tmp_path: Path, processes: Processes):
    docker, authorization, compose, runtime, images = _setup(tmp_path)
    return cli.run_read_only_probe(
        phase="disposable_postgres", docker_executable=docker,
        authorization_file=authorization, compose_file=compose,
        runtime_environment_file=runtime, image_environment_file=images,
        project_name=PROJECT, processes=processes, clock=lambda: NOW,
    )


def test_absent_resources_are_created_once_and_isolation_is_observed(
    tmp_path: Path,
) -> None:
    processes = Processes([
        _observation(_model()), *[_observation() for _ in range(4)],
        _observation(), _observation(_inspection()),
    ])
    result = _run(tmp_path, processes)
    assert result.status == "passed"
    assert json.loads(result.content)["facts"] == {"database_isolated": True}
    commands = [call[0] for call in processes.calls]
    up = [command for command in commands if "up" in command]
    assert len(up) == 1
    assert up[0][-5:] == (
        "up", "--detach", "--no-build", "--no-recreate", "postgres",
    )
    assert all(call[1]["environment"] == {"LANG": "C", "LC_ALL": "C"} for call in processes.calls)


def test_existing_run_resource_fails_before_mutation(tmp_path: Path) -> None:
    processes = Processes([
        _observation(_model()), _observation(f"{PROJECT}-postgres-1\n".encode()),
    ])
    with pytest.raises(cli.StagingReadOnlyProbeCliUnavailable):
        _run(tmp_path, processes)
    assert not any("up" in call[0] for call in processes.calls)


def test_external_network_fails_before_absence_checks(tmp_path: Path) -> None:
    processes = Processes([_observation(_model(external=True))])
    with pytest.raises(cli.StagingReadOnlyProbeCliUnavailable):
        _run(tmp_path, processes)
    assert len(processes.calls) == 1


def test_unknown_create_outcome_is_not_retried_or_inspected(tmp_path: Path) -> None:
    processes = Processes([
        _observation(_model()), *[_observation() for _ in range(4)],
        _observation(timed_out=True),
    ])
    with pytest.raises(cli.StagingReadOnlyProbeCliUnavailable):
        _run(tmp_path, processes)
    assert sum("up" in call[0] for call in processes.calls) == 1
    assert not any(call[0][1:3] == ("container", "inspect") for call in processes.calls)


def test_observed_unhealthy_instance_is_neutral_failed(tmp_path: Path) -> None:
    processes = Processes([
        _observation(_model()), *[_observation() for _ in range(4)],
        _observation(), _observation(_inspection(healthy=False)),
    ])
    result = _run(tmp_path, processes)
    assert result.status == "failed"
    assert json.loads(result.content)["facts"] == {"database_isolated": False}
