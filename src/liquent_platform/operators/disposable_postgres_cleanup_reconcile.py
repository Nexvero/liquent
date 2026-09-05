"""Read-only reconciliation of one open runtime-only PostgreSQL cleanup claim."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from liquent_platform.operators.disposable_postgres import (
    DisposablePostgresUnavailable, _closed_postgres_model, _is_isolated,
)
from liquent_platform.operators.disposable_postgres_claim_reconcile import (
    _historical_reconciliation,
)
from liquent_platform.operators.disposable_postgres_cleanup_preflight import (
    DisposablePostgresCleanupPreflightUnavailable, _authorization as _cleanup_authorization,
)
from liquent_platform.operators.disposable_postgres_disposition import (
    DisposablePostgresDispositionUnavailable, _authorization as _disposition,
    resolve_disposable_postgres_disposition,
)
from liquent_platform.operators.disposable_postgres_reconcile import (
    DisposablePostgresReconcileUnavailable, _historical, _observe,
    _owned_network, _owned_volume, _pairs, _presence, _timestamp,
)
from liquent_platform.operators.disposable_postgres_runtime_cleanup import (
    _binding, _existing, _network_exclusive, _stopped,
)
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, OPAQUE, SHA256,
)
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner
from liquent_platform.operators.staging_read_only_probe_cli import (
    ENV_KEYS, _environment_file,
)


KEYS = {
    "schema_version", "cleanup_reconciliation_id", "cleanup_id", "run_id",
    "phase", "source_commit", "image_ref", "compose_sha256",
    "reconciliation_id", "claim_reconciliation_id", "disposition_id",
    "staging_evidence_sha256", "reconciliation_evidence_sha256",
    "claim_reconciliation_evidence_sha256", "disposition_authorization_sha256",
    "cleanup_authorization_sha256", "operation", "scope", "executor_id",
    "authorizer_id", "valid_from", "valid_until",
}


class DisposablePostgresCleanupReconcileUnavailable(Exception):
    code = "disposable_postgres_cleanup_reconcile_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresCleanupReconcileUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        value = json.loads(_private_file(path, 32_768), object_pairs_hook=_pairs)
        if type(value) is not dict or set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresCleanupReconcileUnavailable
        if (
            value["phase"] != "disposable_postgres" or value["scope"] != "runtime_only"
            or value["operation"] != "inspect_disposable_postgres_runtime_cleanup"
        ):
            raise DisposablePostgresCleanupReconcileUnavailable
        for key in (
            "cleanup_reconciliation_id", "cleanup_id", "run_id", "reconciliation_id",
            "claim_reconciliation_id", "disposition_id", "executor_id", "authorizer_id",
        ):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise DisposablePostgresCleanupReconcileUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise DisposablePostgresCleanupReconcileUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresCleanupReconcileUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresCleanupReconcileUnavailable
        for key in (
            "compose_sha256", "staging_evidence_sha256", "reconciliation_evidence_sha256",
            "claim_reconciliation_evidence_sha256", "disposition_authorization_sha256",
            "cleanup_authorization_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresCleanupReconcileUnavailable
        start, end, now = _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock()
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
            or not start <= now.astimezone(UTC) <= end
        ):
            raise DisposablePostgresCleanupReconcileUnavailable
        return value
    except DisposablePostgresCleanupReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupReconcileUnavailable from None


def _historical_cleanup(path: Path) -> dict:
    try:
        value = json.loads(_private_file(path, 32_768), object_pairs_hook=_pairs)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        return _cleanup_authorization(path, clock=lambda: start + (end - start) / 2)
    except Exception:
        raise DisposablePostgresCleanupReconcileUnavailable from None


def _historical_disposition(path: Path) -> dict:
    try:
        value = json.loads(_private_file(path, 32_768), object_pairs_hook=_pairs)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        return _disposition(path, clock=lambda: start + (end - start) / 2)
    except Exception:
        raise DisposablePostgresCleanupReconcileUnavailable from None


def _claim(path: Path, binding: dict) -> bool:
    try:
        if not path.exists():
            return False
        metadata = path.stat(follow_symlinks=False)
        value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or type(value) is not dict or set(value) != set(binding) | {"started_at"}
            or any(value[key] != expected for key, expected in binding.items())
            or type(value["started_at"]) is not str
        ):
            raise DisposablePostgresCleanupReconcileUnavailable
        started = datetime.fromisoformat(value["started_at"].replace("Z", "+00:00"))
        if started.tzinfo is None:
            raise DisposablePostgresCleanupReconcileUnavailable
        return True
    except DisposablePostgresCleanupReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupReconcileUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_runtime_cleanup_reconciliation",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _network_empty(raw: bytes, *, name: str, project: str) -> bool:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        return (
            _owned_network(raw, name=name, project=project)
            and type(value[0].get("Containers")) is dict
            and value[0]["Containers"] == {}
        )
    except Exception:
        raise DisposablePostgresCleanupReconcileUnavailable from None


def _running(raw: bytes, *, container: str) -> bool:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        return (
            type(value) is list and len(value) == 1 and type(value[0]) is dict
            and value[0].get("Name") == f"/{container}"
            and type(value[0].get("State")) is dict
            and value[0]["State"].get("Running") is True
            and value[0]["State"].get("Status") == "running"
        )
    except Exception:
        raise DisposablePostgresCleanupReconcileUnavailable from None


def _static_isolated(
    raw: bytes, *, container: str, networks: tuple[str, str], volume: str,
    image: str, project_name: str,
) -> bool:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs)
        if type(value) is not list or len(value) != 1 or type(value[0]) is not dict:
            raise DisposablePostgresCleanupReconcileUnavailable
        normalized = dict(value[0])
        normalized["State"] = {"Status": "running", "Health": {"Status": "healthy"}}
        return _is_isolated(
            json.dumps([normalized], separators=(",", ":")).encode(),
            container=container, networks=networks, volume=volume,
            image=image, project_name=project_name,
        )
    except DisposablePostgresCleanupReconcileUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupReconcileUnavailable from None


def reconcile_disposable_postgres_cleanup(
    *, docker_executable: Path, authorization_file: Path,
    reconciliation_file: Path, claim_reconciliation_file: Path,
    disposition_file: Path, cleanup_file: Path,
    cleanup_reconciliation_file: Path, staging_evidence_file: Path,
    compose_file: Path, runtime_environment_file: Path,
    image_environment_file: Path, project_name: str, evidence_directory: Path,
    processes=None, clock=lambda: datetime.now(UTC),
) -> bytes:
    try:
        original = _historical(authorization_file)
        previous = _historical_reconciliation(reconciliation_file)
        disposition = _historical_disposition(disposition_file)
        cleanup = _historical_cleanup(cleanup_file)
        current = _authorization(cleanup_reconciliation_file, clock=clock)
        cleanup_raw = _private_file(cleanup_file, 32_768)
        if (
            cleanup["scope"] != "runtime_only"
            or current["cleanup_authorization_sha256"] != hashlib.sha256(cleanup_raw).hexdigest()
            or any(current[key] != cleanup[key] for key in (
                "cleanup_id", "run_id", "source_commit", "image_ref", "compose_sha256",
                "reconciliation_id", "claim_reconciliation_id", "disposition_id",
                "staging_evidence_sha256", "reconciliation_evidence_sha256",
                "claim_reconciliation_evidence_sha256", "disposition_authorization_sha256",
            ))
            or cleanup["run_id"] != original.run_id
            or cleanup["reconciliation_id"] != previous["reconciliation_id"]
            or cleanup["claim_reconciliation_id"] != disposition["claim_reconciliation_id"]
            or project_name != f"liquent-{original.run_id}"
        ):
            raise DisposablePostgresCleanupReconcileUnavailable
        disposition_start = _timestamp(disposition["valid_from"])
        disposition_end = _timestamp(disposition["valid_until"])
        resolved = resolve_disposable_postgres_disposition(
            authorization_file=authorization_file, reconciliation_file=reconciliation_file,
            claim_reconciliation_file=claim_reconciliation_file,
            disposition_file=disposition_file, staging_evidence_file=staging_evidence_file,
            evidence_directory=evidence_directory,
            clock=lambda: disposition_start + (disposition_end - disposition_start) / 2,
        )
        resolved_value = json.loads(resolved, object_pairs_hook=_pairs)
        if resolved_value.get("outcome") != "cleanup_review_eligible":
            raise DisposablePostgresCleanupReconcileUnavailable

        binding = _binding(original, cleanup, cleanup_file, project_name)
        stem = hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        claim_path = evidence_directory / f".postgres-cleanup-{stem}.claim"
        final = evidence_directory / f"postgres-cleanup-{stem}.json"
        if _existing(final, binding) is not None:
            return _result("final_evidence_present")
        if not _claim(claim_path, binding):
            return _result("not_found")

        if (
            not docker_executable.is_absolute() or not docker_executable.is_file()
            or not os.access(docker_executable, os.X_OK)
            or compose_file.is_symlink() or not compose_file.is_file()
            or hashlib.sha256(compose_file.read_bytes()).hexdigest() != original.compose_sha256
        ):
            raise DisposablePostgresCleanupReconcileUnavailable
        _private_file(runtime_environment_file, 32_768)
        images = _environment_file(image_environment_file)
        if set(images) != ENV_KEYS or images["LIQUENT_APP_IMAGE"] != original.image_ref:
            raise DisposablePostgresCleanupReconcileUnavailable
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
        present = {
            "container": _presence(runner, docker, "container", container),
            "application": _presence(runner, docker, "network", networks[0]),
            "data": _presence(runner, docker, "network", networks[1]),
            "volume": _presence(runner, docker, "volume", volume),
        }
        if not present["volume"]:
            return _result("conflict")
        volume_raw = _observe(runner, (docker, "volume", "inspect", volume), maximum=1_048_576).stdout
        if not _owned_volume(volume_raw, name=volume, project=project_name):
            return _result("conflict")
        if present["container"]:
            if not present["application"] or not present["data"]:
                return _result("conflict")
            container_raw = _observe(runner, (docker, "container", "inspect", container), maximum=1_048_576).stdout
            network_raw = [
                _observe(runner, (docker, "network", "inspect", name), maximum=1_048_576).stdout
                for name in networks
            ]
            isolated = _static_isolated(
                container_raw, container=container, networks=networks, volume=volume,
                image=images["LIQUENT_POSTGRES_IMAGE"], project_name=project_name,
            ) and all(
                _network_exclusive(raw, name=name, project=project_name, container=container)
                for raw, name in zip(network_raw, networks, strict=True)
            )
            if not isolated:
                return _result("conflict")
            if _running(container_raw, container=container):
                return _result("runtime_intact")
            if _stopped(container_raw, container=container):
                return _result("container_stopped")
            return _result("conflict")
        if present["application"] and not present["data"]:
            return _result("conflict")
        for key, name in (("application", networks[0]), ("data", networks[1])):
            if present[key]:
                raw = _observe(runner, (docker, "network", "inspect", name), maximum=1_048_576).stdout
                if not _network_empty(raw, name=name, project=project_name):
                    return _result("conflict")
        if present["application"] and present["data"]:
            return _result("container_removed")
        if not present["application"] and present["data"]:
            return _result("application_network_removed")
        return _result("runtime_removed_evidence_missing")
    except DisposablePostgresCleanupReconcileUnavailable:
        raise
    except (
        DisposablePostgresCleanupPreflightUnavailable,
        DisposablePostgresDispositionUnavailable, DisposablePostgresReconcileUnavailable,
        DisposablePostgresUnavailable,
    ):
        raise DisposablePostgresCleanupReconcileUnavailable from None
    except Exception:
        raise DisposablePostgresCleanupReconcileUnavailable from None


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-disposable-postgres-cleanup-reconcile", add_help=False)
    for name in (
        "docker-executable", "authorization-file", "reconciliation-file",
        "claim-reconciliation-file", "disposition-file", "cleanup-file",
        "cleanup-reconciliation-file", "staging-evidence-file", "compose-file",
        "runtime-env-file", "image-env-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(reconcile_disposable_postgres_cleanup(
            docker_executable=value["docker_executable"], authorization_file=value["authorization_file"],
            reconciliation_file=value["reconciliation_file"],
            claim_reconciliation_file=value["claim_reconciliation_file"],
            disposition_file=value["disposition_file"], cleanup_file=value["cleanup_file"],
            cleanup_reconciliation_file=value["cleanup_reconciliation_file"],
            staging_evidence_file=value["staging_evidence_file"], compose_file=value["compose_file"],
            runtime_environment_file=value["runtime_env_file"],
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
