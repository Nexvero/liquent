"""Read-only reconciliation of an unknown disposable PostgreSQL start."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from liquent_platform.operators.disposable_postgres import (
    DisposablePostgresUnavailable, _closed_postgres_model, _is_isolated,
)
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, OPAQUE, SHA256, _timestamp, load_staging_run_authorization,
)
from liquent_platform.operators.staging_process_adapter import (
    LocalBoundedProcessRunner, ProcessObservation,
)
from liquent_platform.operators.staging_read_only_probe_cli import (
    ENV_KEYS, _environment_file,
)


KEYS = {
    "schema_version", "reconciliation_id", "run_id", "phase",
    "source_commit", "image_ref", "compose_sha256", "executor_id",
    "authorizer_id", "valid_from", "valid_until",
}


class DisposablePostgresReconcileUnavailable(Exception):
    code = "disposable_postgres_reconcile_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresReconcileUnavailable


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise DisposablePostgresReconcileUnavailable
        result[key] = value
    return result


def _json_private(path: Path) -> dict:
    try:
        value = json.loads(_private_file(path, 32_768), object_pairs_hook=_pairs)
        if type(value) is not dict:
            raise DisposablePostgresReconcileUnavailable
        return value
    except DisposablePostgresReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None


def _reconciliation(path: Path, *, clock) -> dict:
    value = _json_private(path)
    try:
        if set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresReconcileUnavailable
        if value["phase"] != "disposable_postgres":
            raise DisposablePostgresReconcileUnavailable
        for key in ("reconciliation_id", "run_id", "executor_id", "authorizer_id"):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise DisposablePostgresReconcileUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise DisposablePostgresReconcileUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresReconcileUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresReconcileUnavailable
        if type(value["compose_sha256"]) is not str or SHA256.fullmatch(value["compose_sha256"]) is None:
            raise DisposablePostgresReconcileUnavailable
        start, end, now = _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock()
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
            or not start <= now.astimezone(UTC) <= end
        ):
            raise DisposablePostgresReconcileUnavailable
        return value
    except DisposablePostgresReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None


def _historical(path: Path):
    value = _json_private(path)
    try:
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        return load_staging_run_authorization(
            path, clock=lambda: start + (end - start) / 2,
        )
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None


def _observe(runner, argv: tuple[str, ...], *, maximum: int) -> ProcessObservation:
    try:
        with tempfile.TemporaryDirectory(prefix="liquent-postgres-reconcile-") as directory:
            value = runner.run(
                argv, cwd=Path(directory), environment={"LANG": "C", "LC_ALL": "C"},
                timeout_seconds=60.0, maximum_output_bytes=maximum,
                terminate_grace_seconds=5.0,
            )
        if (
            type(value) is not ProcessObservation or value.returncode != 0
            or value.stderr or value.timed_out or value.truncated or value.hard_killed
        ):
            raise DisposablePostgresReconcileUnavailable
        return value
    except DisposablePostgresReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None


def _presence(runner, docker: str, kind: str, name: str) -> bool:
    field = "{{.Names}}" if kind == "container" else "{{.Name}}"
    value = _observe(runner, (
        docker, kind, "ls", "--filter", f"name=^{name}$", "--format", field,
    ), maximum=65_536).stdout
    try:
        lines = value.decode("utf-8").splitlines()
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None
    if not lines:
        return False
    if lines == [name]:
        return True
    raise DisposablePostgresReconcileUnavailable


def _owned_network(raw: bytes, *, name: str, project: str) -> bool:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        if type(value) is not list or len(value) != 1 or type(value[0]) is not dict:
            raise DisposablePostgresReconcileUnavailable
        item = value[0]
        labels = item.get("Labels")
        return (
            item.get("Name") == name and item.get("Internal") is True
            and type(labels) is dict
            and labels.get("com.docker.compose.project") == project
        )
    except DisposablePostgresReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None


def _owned_volume(raw: bytes, *, name: str, project: str) -> bool:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        if type(value) is not list or len(value) != 1 or type(value[0]) is not dict:
            raise DisposablePostgresReconcileUnavailable
        item = value[0]
        labels = item.get("Labels")
        return (
            item.get("Name") == name and type(labels) is dict
            and labels.get("com.docker.compose.project") == project
        )
    except DisposablePostgresReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "inspection": "disposable_postgres_reconciliation",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _evidence_root(path: Path) -> int:
    try:
        if not isinstance(path, Path) or not path.is_absolute() or path.is_symlink():
            raise DisposablePostgresReconcileUnavailable
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            os.close(descriptor)
            raise DisposablePostgresReconcileUnavailable
        return descriptor
    except DisposablePostgresReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None


def _evidence_binding(original, reconciliation: dict) -> dict:
    return {
        "schema_version": 1,
        "reconciliation_id": reconciliation["reconciliation_id"],
        "run_id": original.run_id, "phase": "disposable_postgres",
        "source_commit": original.source_commit, "image_ref": original.image_ref,
        "compose_sha256": original.compose_sha256,
        "executor_id": reconciliation["executor_id"],
        "authorizer_id": reconciliation["authorizer_id"],
    }


def _existing_evidence(path: Path, binding: dict) -> str | None:
    try:
        if not path.exists():
            return None
        metadata = path.stat(follow_symlinks=False)
        value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or type(value) is not dict
            or set(value) != set(binding) | {"outcome", "completed_at"}
            or any(value[key] != expected for key, expected in binding.items())
            or value["outcome"] not in {"absent", "isolated", "conflict"}
            or type(value["completed_at"]) is not str
        ):
            raise DisposablePostgresReconcileUnavailable
        _timestamp(value["completed_at"])
        return value["outcome"]
    except DisposablePostgresReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None


def _valid_claim(path: Path) -> bool:
    try:
        if not path.exists():
            return False
        metadata = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or path.read_bytes() != b"disposable-postgres-reconciliation\n"
        ):
            raise DisposablePostgresReconcileUnavailable
        return True
    except DisposablePostgresReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None


def _store_evidence(
    root: Path, root_descriptor: int, final: Path, record: dict,
) -> None:
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
                raise DisposablePostgresReconcileUnavailable
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.link(temporary, final)
        temporary.unlink()
        os.fsync(root_descriptor)
        binding = {key: record[key] for key in record if key not in {"outcome", "completed_at"}}
        if _existing_evidence(final, binding) != record["outcome"]:
            raise DisposablePostgresReconcileUnavailable
    except DisposablePostgresReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def reconcile_disposable_postgres(
    *, docker_executable: Path, authorization_file: Path,
    reconciliation_file: Path, compose_file: Path,
    runtime_environment_file: Path, image_environment_file: Path,
    project_name: str, processes=None, clock=lambda: datetime.now(UTC),
) -> bytes:
    try:
        original = _historical(authorization_file)
        reconciliation = _reconciliation(reconciliation_file, clock=clock)
        if (
            reconciliation["run_id"] != original.run_id
            or reconciliation["source_commit"] != original.source_commit
            or reconciliation["image_ref"] != original.image_ref
            or reconciliation["compose_sha256"] != original.compose_sha256
            or project_name != f"liquent-{original.run_id}" or len(project_name) > 63
            or not docker_executable.is_absolute() or not docker_executable.is_file()
            or not os.access(docker_executable, os.X_OK)
            or compose_file.is_symlink() or not compose_file.is_file()
            or hashlib.sha256(compose_file.read_bytes()).hexdigest() != original.compose_sha256
        ):
            raise DisposablePostgresReconcileUnavailable
        _private_file(runtime_environment_file, 32_768)
        images = _environment_file(image_environment_file)
        if set(images) != ENV_KEYS or images["LIQUENT_APP_IMAGE"] != original.image_ref:
            raise DisposablePostgresReconcileUnavailable
        runner = processes or LocalBoundedProcessRunner()
        docker = str(docker_executable)
        compose = _observe(runner, (
            docker, "compose", "--env-file", str(runtime_environment_file),
            "--env-file", str(image_environment_file), "--file", str(compose_file),
            "--project-name", project_name, "config", "--format", "json",
        ), maximum=2_097_152).stdout
        model = json.loads(compose, object_pairs_hook=_pairs)
        container, networks, volume = _closed_postgres_model(
            model, project_name=project_name,
            postgres_image=images["LIQUENT_POSTGRES_IMAGE"],
        )
        resources = (("container", container), *(('network', name) for name in networks), ("volume", volume))
        present = [_presence(runner, docker, kind, name) for kind, name in resources]
        if not any(present):
            return _result("absent")
        if not all(present):
            return _result("conflict")
        container_raw = _observe(
            runner, (docker, "container", "inspect", container), maximum=1_048_576,
        ).stdout
        network_raw = [
            _observe(runner, (docker, "network", "inspect", name), maximum=1_048_576).stdout
            for name in networks
        ]
        volume_raw = _observe(
            runner, (docker, "volume", "inspect", volume), maximum=1_048_576,
        ).stdout
        isolated = (
            _is_isolated(
                container_raw, container=container, networks=networks, volume=volume,
                image=images["LIQUENT_POSTGRES_IMAGE"], project_name=project_name,
            )
            and all(
                _owned_network(raw, name=name, project=project_name)
                for raw, name in zip(network_raw, networks, strict=True)
            )
            and _owned_volume(volume_raw, name=volume, project=project_name)
        )
        return _result("isolated" if isolated else "conflict")
    except DisposablePostgresReconcileUnavailable:
        raise
    except DisposablePostgresUnavailable:
        raise DisposablePostgresReconcileUnavailable from None
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None


def reconcile_disposable_postgres_with_evidence(
    *, docker_executable: Path, authorization_file: Path,
    reconciliation_file: Path, compose_file: Path,
    runtime_environment_file: Path, image_environment_file: Path,
    project_name: str, evidence_directory: Path, processes=None,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        original = _historical(authorization_file)
        reconciliation = _reconciliation(reconciliation_file, clock=clock)
        if (
            reconciliation["run_id"] != original.run_id
            or reconciliation["source_commit"] != original.source_commit
            or reconciliation["image_ref"] != original.image_ref
            or reconciliation["compose_sha256"] != original.compose_sha256
            or project_name != f"liquent-{original.run_id}"
        ):
            raise DisposablePostgresReconcileUnavailable
        binding = _evidence_binding(original, reconciliation)
        root_descriptor = _evidence_root(evidence_directory)
        stem = hashlib.sha256(reconciliation["reconciliation_id"].encode()).hexdigest()
        final = evidence_directory / f"postgres-reconciliation-{stem}.json"
        claim = evidence_directory / f".postgres-reconciliation-{stem}.claim"
        existing = _existing_evidence(final, binding)
        if existing is not None:
            if _valid_claim(claim):
                os.unlink(claim)
                os.fsync(root_descriptor)
            return _result(existing)
        descriptor = os.open(
            claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
        )
        try:
            content = b"disposable-postgres-reconciliation\n"
            if os.write(descriptor, content) != len(content):
                raise DisposablePostgresReconcileUnavailable
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(root_descriptor)
        observed = reconcile_disposable_postgres(
            docker_executable=docker_executable,
            authorization_file=authorization_file,
            reconciliation_file=reconciliation_file, compose_file=compose_file,
            runtime_environment_file=runtime_environment_file,
            image_environment_file=image_environment_file,
            project_name=project_name, processes=processes, clock=clock,
        )
        value = json.loads(observed, object_pairs_hook=_pairs)
        if (
            type(value) is not dict
            or set(value) != {"schema_version", "inspection", "outcome"}
            or value["schema_version"] != 1
            or value["inspection"] != "disposable_postgres_reconciliation"
            or value["outcome"] not in {"absent", "isolated", "conflict"}
        ):
            raise DisposablePostgresReconcileUnavailable
        record = dict(binding)
        record.update({
            "outcome": value["outcome"],
            "completed_at": clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
        })
        _store_evidence(evidence_directory, root_descriptor, final, record)
        os.unlink(claim)
        os.fsync(root_descriptor)
        return _result(value["outcome"])
    except DisposablePostgresReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresReconcileUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-disposable-postgres-reconcile", add_help=False)
    for name in (
        "docker-executable", "authorization-file", "reconciliation-file",
        "compose-file", "runtime-env-file", "image-env-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(reconcile_disposable_postgres_with_evidence(
            docker_executable=value["docker_executable"],
            authorization_file=value["authorization_file"],
            reconciliation_file=value["reconciliation_file"],
            compose_file=value["compose_file"],
            runtime_environment_file=value["runtime_env_file"],
            image_environment_file=value["image_env_file"],
            project_name=value["project_name"],
            evidence_directory=value["evidence_directory"],
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
