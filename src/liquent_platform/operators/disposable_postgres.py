"""One-shot composition for an isolated disposable staging PostgreSQL service."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from liquent_platform.operators.research_worker_staging_executor import (
    StagingRunAuthorization,
)
from liquent_platform.operators.staging_process_adapter import (
    ProcessObservation, ReducedPhaseOutput,
)


NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,62}\Z")


class DisposablePostgresUnavailable(Exception):
    code = "disposable_postgres_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


def _json(raw: bytes, maximum: int):
    if type(raw) is not bytes or not raw or len(raw) > maximum:
        raise DisposablePostgresUnavailable
    try:
        def pairs(values):
            result = {}
            for key, value in values:
                if key in result:
                    raise DisposablePostgresUnavailable
                result[key] = value
            return result

        return json.loads(raw, object_pairs_hook=pairs)
    except Exception:
        raise DisposablePostgresUnavailable from None


def _successful(observation: object) -> ProcessObservation:
    if (
        type(observation) is not ProcessObservation
        or observation.returncode != 0 or observation.stderr
        or observation.timed_out or observation.truncated
        or observation.hard_killed
    ):
        raise DisposablePostgresUnavailable
    return observation


def _run(runner, argv: tuple[str, ...], *, maximum: int) -> ProcessObservation:
    with tempfile.TemporaryDirectory(prefix="liquent-disposable-postgres-") as directory:
        try:
            observation = runner.run(
                argv, cwd=Path(directory), environment={"LANG": "C", "LC_ALL": "C"},
                timeout_seconds=300.0, maximum_output_bytes=maximum,
                terminate_grace_seconds=5.0,
            )
        except Exception:
            raise DisposablePostgresUnavailable from None
    return _successful(observation)


def _closed_postgres_model(
    model: object, *, project_name: str, postgres_image: str,
) -> tuple[str, tuple[str, str], str]:
    try:
        if type(model) is not dict or type(model.get("services")) is not dict:
            raise DisposablePostgresUnavailable
        services = model["services"]
        if set(services) != {
            "migration-gate", "control-plane", "research-worker", "postgres",
            "prometheus", "grafana", "backup",
        } or type(services["postgres"]) is not dict:
            raise DisposablePostgresUnavailable
        postgres = services["postgres"]
        if postgres.get("image") != postgres_image or postgres.get("ports") not in (None, []):
            raise DisposablePostgresUnavailable
        if postgres.get("environment") != {
            "POSTGRES_DB": "liquent", "POSTGRES_USER": "liquent",
            "POSTGRES_PASSWORD_FILE": "/run/secrets/postgres_password",
        }:
            raise DisposablePostgresUnavailable
        if postgres.get("security_opt") != ["no-new-privileges:true"]:
            raise DisposablePostgresUnavailable
        if set(postgres.get("cap_drop", [])) != {"ALL"} or set(postgres.get("cap_add", [])) != {
            "CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID",
        }:
            raise DisposablePostgresUnavailable
        health = postgres.get("healthcheck")
        if type(health) is not dict or health.get("test") != [
            "CMD-SHELL", "pg_isready -U liquent -d liquent",
        ]:
            raise DisposablePostgresUnavailable
        network_value = postgres.get("networks")
        network_keys = set(network_value) if type(network_value) in (dict, list) else set()
        if network_keys != {"application", "data"}:
            raise DisposablePostgresUnavailable
        networks, names = model.get("networks"), []
        if type(networks) is not dict:
            raise DisposablePostgresUnavailable
        for key in ("application", "data"):
            value = networks.get(key)
            expected = f"{project_name}-{key}"
            if (
                type(value) is not dict or value.get("name") != expected
                or value.get("internal") is not True or value.get("external") not in (None, False)
            ):
                raise DisposablePostgresUnavailable
            names.append(expected)
        volumes = postgres.get("volumes")
        if type(volumes) is not list or len(volumes) != 1 or type(volumes[0]) is not dict:
            raise DisposablePostgresUnavailable
        mount = volumes[0]
        if mount.get("type") != "volume" or mount.get("target") != "/var/lib/postgresql/data":
            raise DisposablePostgresUnavailable
        source = mount.get("source")
        volume_definitions = model.get("volumes")
        expected_volume = f"{project_name}-postgres-data"
        if (
            type(source) is not str or type(volume_definitions) is not dict
            or type(volume_definitions.get(source)) is not dict
            or volume_definitions[source].get("name") != expected_volume
            or volume_definitions[source].get("external") not in (None, False)
        ):
            raise DisposablePostgresUnavailable
        secrets = postgres.get("secrets")
        if type(secrets) is not list or len(secrets) != 1:
            raise DisposablePostgresUnavailable
        secret = secrets[0]
        if type(secret) is str:
            valid_secret = secret == "postgres_password"
        else:
            valid_secret = type(secret) is dict and secret.get("source") == "postgres_password" and secret.get(
                "target", "postgres_password"
            ) == "postgres_password"
        if not valid_secret:
            raise DisposablePostgresUnavailable
        container = f"{project_name}-postgres-1"
        if any(NAME.fullmatch(value) is None for value in (container, *names, expected_volume)):
            raise DisposablePostgresUnavailable
        return container, (names[0], names[1]), expected_volume
    except DisposablePostgresUnavailable:
        raise
    except Exception:
        raise DisposablePostgresUnavailable from None


def _assert_absent(runner, docker: str, kind: str, name: str) -> None:
    noun = {"container": "container", "network": "network", "volume": "volume"}[kind]
    field = "{{.Names}}" if kind == "container" else "{{.Name}}"
    observation = _run(runner, (
        docker, noun, "ls", "--filter", f"name=^{name}$", "--format", field,
    ), maximum=65_536)
    if observation.stdout.strip():
        raise DisposablePostgresUnavailable


def _is_isolated(
    raw: bytes, *, container: str, networks: tuple[str, str], volume: str,
    image: str, project_name: str,
) -> bool:
    value = _json(raw, 1_048_576)
    if type(value) is not list or len(value) != 1 or type(value[0]) is not dict:
        raise DisposablePostgresUnavailable
    item = value[0]
    state, config, host, network = (
        item.get("State"), item.get("Config"), item.get("HostConfig"),
        item.get("NetworkSettings"),
    )
    if not all(type(part) is dict for part in (state, config, host, network)):
        raise DisposablePostgresUnavailable
    labels = config.get("Labels")
    mounts = item.get("Mounts")
    return (
        state.get("Status") == "running"
        and type(state.get("Health")) is dict
        and state["Health"].get("Status") == "healthy"
        and config.get("Image") == image
        and type(labels) is dict
        and labels.get("com.docker.compose.project") == project_name
        and labels.get("com.docker.compose.service") == "postgres"
        and host.get("PortBindings") in (None, {})
        and type(network.get("Networks")) is dict
        and set(network["Networks"]) == set(networks)
        and type(mounts) is list and len(mounts) == 1
        and type(mounts[0]) is dict and mounts[0].get("Type") == "volume"
        and mounts[0].get("Name") == volume
        and mounts[0].get("Destination") == "/var/lib/postgresql/data"
    )


def provision_disposable_postgres(
    *, docker_executable: Path, compose_file: Path,
    runtime_environment_file: Path, image_environment_file: Path,
    project_name: str, authorization: StagingRunAuthorization,
    postgres_image: str, compose_model: bytes, runner,
) -> ReducedPhaseOutput:
    """Create once after absence proof, then inspect without retry or cleanup."""

    try:
        if type(authorization) is not StagingRunAuthorization:
            raise DisposablePostgresUnavailable
        model = _json(compose_model, 2_097_152)
        container, networks, volume = _closed_postgres_model(
            model, project_name=project_name, postgres_image=postgres_image,
        )
        docker = str(docker_executable)
        _assert_absent(runner, docker, "container", container)
        for network_name in networks:
            _assert_absent(runner, docker, "network", network_name)
        _assert_absent(runner, docker, "volume", volume)
        prefix = (
            docker, "compose", "--env-file", str(runtime_environment_file),
            "--env-file", str(image_environment_file), "--file", str(compose_file),
            "--project-name", project_name,
        )
        _run(runner, prefix + (
            "up", "--detach", "--no-build", "--no-recreate", "postgres",
        ), maximum=65_536)
        inspection = _run(
            runner, (docker, "container", "inspect", container), maximum=1_048_576,
        )
        result = _is_isolated(
            inspection.stdout, container=container, networks=networks,
            volume=volume, image=postgres_image, project_name=project_name,
        )
        content = (json.dumps({
            "schema_version": 1, "phase": "disposable_postgres",
            "facts": {"database_isolated": result},
        }, sort_keys=True, separators=(",", ":")) + "\n").encode()
        return ReducedPhaseOutput(
            "disposable_postgres", "passed" if result else "failed", content,
        )
    except DisposablePostgresUnavailable:
        raise
    except Exception:
        raise DisposablePostgresUnavailable from None
