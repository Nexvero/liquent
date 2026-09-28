"""Owner-controlled runtime-only cleanup for disposable PostgreSQL resources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

from liquent_platform.operators.disposable_postgres import (
    DisposablePostgresUnavailable, _closed_postgres_model, _is_isolated,
)
from liquent_platform.operators.disposable_postgres_cleanup_preflight import (
    DisposablePostgresCleanupPreflightUnavailable, _authorization,
    preflight_disposable_postgres_cleanup,
)
from liquent_platform.operators.disposable_postgres_reconcile import (
    DisposablePostgresReconcileUnavailable, _evidence_root, _historical,
    _observe, _owned_network, _owned_volume, _pairs,
)
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner
from liquent_platform.operators.staging_read_only_probe_cli import (
    ENV_KEYS, _environment_file,
)


class DisposablePostgresRuntimeCleanupUnavailable(Exception):
    code = "disposable_postgres_runtime_cleanup_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresRuntimeCleanupUnavailable


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_runtime_cleanup",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _decode_result(raw: bytes, operation: str, outcomes: set[str]) -> str:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        if (
            type(value) is not dict
            or set(value) != {"schema_version", "operation", "outcome"}
            or value["schema_version"] != 1 or value["operation"] != operation
            or value["outcome"] not in outcomes
        ):
            raise DisposablePostgresRuntimeCleanupUnavailable
        return value["outcome"]
    except DisposablePostgresRuntimeCleanupUnavailable:
        raise
    except Exception:
        raise DisposablePostgresRuntimeCleanupUnavailable from None


def _network_exclusive(raw: bytes, *, name: str, project: str, container: str) -> bool:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        if not _owned_network(raw, name=name, project=project):
            return False
        endpoints = value[0].get("Containers")
        if type(endpoints) is not dict or len(endpoints) != 1:
            return False
        endpoint = next(iter(endpoints.values()))
        return type(endpoint) is dict and endpoint.get("Name") == container
    except DisposablePostgresReconcileUnavailable:
        raise DisposablePostgresRuntimeCleanupUnavailable from None
    except Exception:
        raise DisposablePostgresRuntimeCleanupUnavailable from None


def _stopped(raw: bytes, *, container: str) -> bool:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        if type(value) is not list or len(value) != 1 or type(value[0]) is not dict:
            raise DisposablePostgresRuntimeCleanupUnavailable
        item, state = value[0], value[0].get("State")
        return (
            item.get("Name") == f"/{container}" and type(state) is dict
            and state.get("Running") is False
            and state.get("Status") in {"exited", "created", "dead"}
        )
    except DisposablePostgresRuntimeCleanupUnavailable:
        raise
    except Exception:
        raise DisposablePostgresRuntimeCleanupUnavailable from None


def _absent(raw: bytes) -> bool:
    try:
        return raw.decode("utf-8").splitlines() == []
    except Exception:
        raise DisposablePostgresRuntimeCleanupUnavailable from None


def _existing(path: Path, binding: dict) -> str | None:
    try:
        if not path.exists():
            return None
        metadata = path.stat(follow_symlinks=False)
        value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or type(value) is not dict
            or set(value) != set(binding) | {"outcome", "started_at", "completed_at"}
            or any(value[key] != expected for key, expected in binding.items())
            or value["outcome"] != "removed_runtime"
            or type(value["started_at"]) is not str or type(value["completed_at"]) is not str
        ):
            raise DisposablePostgresRuntimeCleanupUnavailable
        datetime.fromisoformat(value["started_at"].replace("Z", "+00:00"))
        datetime.fromisoformat(value["completed_at"].replace("Z", "+00:00"))
        return value["outcome"]
    except DisposablePostgresRuntimeCleanupUnavailable:
        raise
    except Exception:
        raise DisposablePostgresRuntimeCleanupUnavailable from None


def _binding(original, cleanup: dict, cleanup_file: Path, project_name: str) -> dict:
    return {
        "schema_version": 1, "cleanup_id": cleanup["cleanup_id"],
        "run_id": original.run_id, "phase": "disposable_postgres",
        "source_commit": original.source_commit, "image_ref": original.image_ref,
        "compose_sha256": original.compose_sha256, "scope": "runtime_only",
        "operation": "remove_disposable_postgres_resources",
        "reconciliation_id": cleanup["reconciliation_id"],
        "claim_reconciliation_id": cleanup["claim_reconciliation_id"],
        "disposition_id": cleanup["disposition_id"],
        "staging_evidence_sha256": cleanup["staging_evidence_sha256"],
        "reconciliation_evidence_sha256": cleanup["reconciliation_evidence_sha256"],
        "claim_reconciliation_evidence_sha256": cleanup["claim_reconciliation_evidence_sha256"],
        "disposition_authorization_sha256": cleanup["disposition_authorization_sha256"],
        "cleanup_authorization_sha256": hashlib.sha256(
            _private_file(cleanup_file, 32_768)
        ).hexdigest(),
        "executor_id": cleanup["executor_id"], "authorizer_id": cleanup["authorizer_id"],
        "container": f"{project_name}-postgres-1",
        "application_network": f"{project_name}-application",
        "data_network": f"{project_name}-data",
        "retained_volume": f"{project_name}-postgres-data",
        "confirmed_steps": [
            "container_stopped", "container_absent",
            "application_network_absent", "data_network_absent",
            "data_volume_retained",
        ],
    }


def _write_evidence(root: Path, descriptor: int, final: Path, record: dict) -> None:
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
                raise DisposablePostgresRuntimeCleanupUnavailable
            view = view[written:]
        os.fsync(opened)
        os.close(opened)
        opened = None
        os.link(temporary, final)
        temporary.unlink()
        os.fsync(descriptor)
        if _existing(final, {k: v for k, v in record.items() if k not in {"outcome", "started_at", "completed_at"}}) != "removed_runtime":
            raise DisposablePostgresRuntimeCleanupUnavailable
    except DisposablePostgresRuntimeCleanupUnavailable:
        raise
    except Exception:
        raise DisposablePostgresRuntimeCleanupUnavailable from None
    finally:
        if opened is not None:
            os.close(opened)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def cleanup_disposable_postgres_runtime(
    *, docker_executable: Path, authorization_file: Path,
    reconciliation_file: Path, claim_reconciliation_file: Path,
    disposition_file: Path, cleanup_file: Path, staging_evidence_file: Path,
    compose_file: Path, runtime_environment_file: Path,
    image_environment_file: Path, project_name: str, evidence_directory: Path,
    processes=None, clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        original = _historical(authorization_file)
        cleanup = _authorization(cleanup_file, clock=clock)
        if (
            cleanup["scope"] != "runtime_only" or cleanup["run_id"] != original.run_id
            or project_name != f"liquent-{original.run_id}"
        ):
            raise DisposablePostgresRuntimeCleanupUnavailable
        stem = hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        claim = evidence_directory / f".postgres-cleanup-{stem}.claim"
        final = evidence_directory / f"postgres-cleanup-{stem}.json"
        binding = _binding(original, cleanup, cleanup_file, project_name)
        root_descriptor = _evidence_root(evidence_directory)
        existing = _existing(final, binding)
        if existing is not None:
            if claim.exists():
                raise DisposablePostgresRuntimeCleanupUnavailable
            return _result(existing)
        if claim.exists():
            raise DisposablePostgresRuntimeCleanupUnavailable
        preflight = preflight_disposable_postgres_cleanup(
            docker_executable=docker_executable, authorization_file=authorization_file,
            reconciliation_file=reconciliation_file,
            claim_reconciliation_file=claim_reconciliation_file,
            disposition_file=disposition_file, cleanup_file=cleanup_file,
            staging_evidence_file=staging_evidence_file, compose_file=compose_file,
            runtime_environment_file=runtime_environment_file,
            image_environment_file=image_environment_file,
            project_name=project_name, evidence_directory=evidence_directory,
            processes=processes, clock=clock,
        )
        outcome = _decode_result(
            preflight, "disposable_postgres_cleanup_preflight",
            {"ready", "already_absent", "rejected"},
        )
        if outcome != "ready":
            return _result(outcome)

        images = _environment_file(image_environment_file)
        if set(images) != ENV_KEYS:
            raise DisposablePostgresRuntimeCleanupUnavailable
        runner = processes or LocalBoundedProcessRunner()
        docker = str(docker_executable)
        model_raw = _observe(runner, (
            docker, "compose", "--env-file", str(runtime_environment_file),
            "--env-file", str(image_environment_file), "--file", str(compose_file),
            "--project-name", project_name, "config", "--format", "json",
        ), maximum=2_097_152).stdout
        model = json.loads(model_raw, object_pairs_hook=_pairs)
        container, networks, volume = _closed_postgres_model(
            model, project_name=project_name,
            postgres_image=images["LIQUENT_POSTGRES_IMAGE"],
        )
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
        if (
            not _is_isolated(
                container_raw, container=container, networks=networks, volume=volume,
                image=images["LIQUENT_POSTGRES_IMAGE"], project_name=project_name,
            )
            or not all(
                _network_exclusive(raw, name=name, project=project_name, container=container)
                for raw, name in zip(network_raw, networks, strict=True)
            )
            or not _owned_volume(volume_raw, name=volume, project=project_name)
        ):
            return _result("rejected")

        claim_record = dict(binding)
        claim_record["started_at"] = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        claim_content = (json.dumps(claim_record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        opened = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            if os.write(opened, claim_content) != len(claim_content):
                raise DisposablePostgresRuntimeCleanupUnavailable
            os.fsync(opened)
        finally:
            os.close(opened)
        os.fsync(root_descriptor)

        _observe(runner, (docker, "container", "stop", "--time", "30", container), maximum=65_536)
        stopped = _observe(runner, (docker, "container", "inspect", container), maximum=1_048_576).stdout
        if not _stopped(stopped, container=container):
            raise DisposablePostgresRuntimeCleanupUnavailable
        _observe(runner, (docker, "container", "rm", container), maximum=65_536)
        if not _absent(_observe(runner, (
            docker, "container", "ls", "--filter", f"name=^{container}$", "--format", "{{.Names}}",
        ), maximum=65_536).stdout):
            raise DisposablePostgresRuntimeCleanupUnavailable
        for name in networks:
            _observe(runner, (docker, "network", "rm", name), maximum=65_536)
            if not _absent(_observe(runner, (
                docker, "network", "ls", "--filter", f"name=^{name}$", "--format", "{{.Name}}",
            ), maximum=65_536).stdout):
                raise DisposablePostgresRuntimeCleanupUnavailable
        retained = _observe(runner, (docker, "volume", "inspect", volume), maximum=1_048_576).stdout
        if not _owned_volume(retained, name=volume, project=project_name):
            raise DisposablePostgresRuntimeCleanupUnavailable

        record = dict(binding)
        record.update({
            "outcome": "removed_runtime",
            "started_at": claim_record["started_at"],
            "completed_at": clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
        })
        _write_evidence(evidence_directory, root_descriptor, final, record)
        os.unlink(claim)
        os.fsync(root_descriptor)
        return _result("removed_runtime")
    except DisposablePostgresRuntimeCleanupUnavailable:
        raise
    except (
        DisposablePostgresCleanupPreflightUnavailable,
        DisposablePostgresReconcileUnavailable, DisposablePostgresUnavailable,
    ):
        raise DisposablePostgresRuntimeCleanupUnavailable from None
    except Exception:
        raise DisposablePostgresRuntimeCleanupUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-disposable-postgres-runtime-cleanup", add_help=False)
    for name in (
        "docker-executable", "authorization-file", "reconciliation-file",
        "claim-reconciliation-file", "disposition-file", "cleanup-file",
        "staging-evidence-file", "compose-file", "runtime-env-file",
        "image-env-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(cleanup_disposable_postgres_runtime(
            docker_executable=value["docker_executable"],
            authorization_file=value["authorization_file"],
            reconciliation_file=value["reconciliation_file"],
            claim_reconciliation_file=value["claim_reconciliation_file"],
            disposition_file=value["disposition_file"], cleanup_file=value["cleanup_file"],
            staging_evidence_file=value["staging_evidence_file"],
            compose_file=value["compose_file"], runtime_environment_file=value["runtime_env_file"],
            image_environment_file=value["image_env_file"], project_name=value["project_name"],
            evidence_directory=value["evidence_directory"],
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
