"""Owner-controlled single supervisor control-directory cleanup operator."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import stat
import sys
from typing import Any, NoReturn

from sqlalchemy import Engine

from liquent_platform.application.manifest_handoff_supervisor_control_directory_cleanup_composition import (
    compose_manifest_handoff_supervisor_control_directory_cleanup,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    CleanupManifestHandoffSupervisorControlDirectory,
    CompletedManifestHandoffSupervisorControlDirectoryCleanup,
    ManifestHandoffSupervisorControlDirectoryCleanupAttemptId,
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
    ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired,
    ReconcileManifestHandoffSupervisorControlDirectoryCleanup,
    ReconciledManifestHandoffSupervisorControlDirectoryCleanup,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine


class SupervisorControlDirectoryCleanupOperatorInputRejected(Exception):
    code = "supervisor_control_directory_cleanup_operator_input_rejected"

    def __init__(self) -> None:
        super().__init__(self.code)


class SupervisorControlDirectoryCleanupOperatorUnavailable(Exception):
    code = "supervisor_control_directory_cleanup_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


def _private_bytes(path: Path, maximum: int = 65_536) -> bytes:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        status = os.fstat(descriptor)
        if (
            not stat.S_ISREG(status.st_mode)
            or status.st_uid != os.geteuid()
            or status.st_nlink != 1
            or stat.S_IMODE(status.st_mode) not in (0o400, 0o600)
            or status.st_size < 1
            or status.st_size > maximum
        ):
            raise SupervisorControlDirectoryCleanupOperatorUnavailable
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(8192, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        value = b"".join(chunks)
        if not value or len(value) > maximum or len(value) != status.st_size:
            raise SupervisorControlDirectoryCleanupOperatorUnavailable
        return value
    except SupervisorControlDirectoryCleanupOperatorUnavailable:
        raise
    except OSError:
        raise SupervisorControlDirectoryCleanupOperatorUnavailable from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _private_text(path: Path, maximum: int = 65_536) -> str:
    try:
        value = _private_bytes(path, maximum).decode("utf-8")
    except UnicodeError:
        raise SupervisorControlDirectoryCleanupOperatorUnavailable from None
    if "\x00" in value:
        raise SupervisorControlDirectoryCleanupOperatorUnavailable
    return value


def _one_line(path: Path) -> str:
    value = _private_text(path, 8192)
    if value.endswith("\n"):
        value = value[:-1]
    if not value or "\n" in value or "\r" in value or value.strip() != value:
        raise SupervisorControlDirectoryCleanupOperatorInputRejected
    return value


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SupervisorControlDirectoryCleanupOperatorInputRejected
        value[key] = item
    return value


def _request(path: Path, fields: set[str]) -> dict[str, str]:
    try:
        value = json.loads(_private_text(path), object_pairs_hook=_pairs)
    except SupervisorControlDirectoryCleanupOperatorInputRejected:
        raise
    except SupervisorControlDirectoryCleanupOperatorUnavailable:
        raise
    except (TypeError, ValueError, json.JSONDecodeError):
        raise SupervisorControlDirectoryCleanupOperatorInputRejected from None
    if type(value) is not dict or set(value) != fields:
        raise SupervisorControlDirectoryCleanupOperatorInputRejected
    if any(
        type(item) is not str or not item or item.strip() != item
        for item in value.values()
    ):
        raise SupervisorControlDirectoryCleanupOperatorInputRejected
    return value


def load_execute_request(path: Path) -> tuple[UserId, ManifestHandoffSupervisorControlDirectoryId]:
    value = _request(path, {"actor_user_id", "directory_id"})
    try:
        return (
            UserId(value["actor_user_id"]),
            ManifestHandoffSupervisorControlDirectoryId(value["directory_id"]),
        )
    except (TypeError, ValueError):
        raise SupervisorControlDirectoryCleanupOperatorInputRejected from None


def load_reconcile_request(
    path: Path,
) -> ReconcileManifestHandoffSupervisorControlDirectoryCleanup:
    value = _request(path, {"attempt_id", "directory_id"})
    try:
        return ReconcileManifestHandoffSupervisorControlDirectoryCleanup(
            ManifestHandoffSupervisorControlDirectoryCleanupAttemptId(value["attempt_id"]),
            ManifestHandoffSupervisorControlDirectoryId(value["directory_id"]),
        )
    except (TypeError, ValueError):
        raise SupervisorControlDirectoryCleanupOperatorInputRejected from None


def _private_root(path: Path) -> Path:
    if not path.is_absolute():
        raise SupervisorControlDirectoryCleanupOperatorInputRejected
    try:
        resolved = path.resolve(strict=True)
        status = path.stat()
    except OSError:
        raise SupervisorControlDirectoryCleanupOperatorUnavailable from None
    if (
        resolved != path
        or not stat.S_ISDIR(status.st_mode)
        or status.st_uid != os.geteuid()
        or stat.S_IMODE(status.st_mode) != 0o700
    ):
        raise SupervisorControlDirectoryCleanupOperatorUnavailable
    return path


def _configuration(database_url_file: Path, backend_instance_id_file: Path,
                   control_root_file: Path):
    database_url = _one_line(database_url_file)
    try:
        backend = ManifestHandoffSupervisorBackendInstanceId(
            _one_line(backend_instance_id_file)
        )
    except (TypeError, ValueError):
        raise SupervisorControlDirectoryCleanupOperatorInputRejected from None
    root = _private_root(Path(_one_line(control_root_file)))
    return database_url, backend, root


def _composition(engine: Engine, backend, root):
    if not DatabaseReadinessProbe(engine).check().ready:
        raise SupervisorControlDirectoryCleanupOperatorUnavailable
    return compose_manifest_handoff_supervisor_control_directory_cleanup(
        database_engine=engine,
        backend_instance_id=backend,
        control_directory_root=root,
    )


def execute_one(engine: Engine, backend, root: Path, actor: UserId, directory_id):
    composition = _composition(engine, backend, root)
    attempt_id = ManifestHandoffSupervisorControlDirectoryCleanupAttemptId(
        secrets.token_hex(32)
    )
    request = CleanupManifestHandoffSupervisorControlDirectory(
        attempt_id, actor, directory_id
    )
    clearance = composition.clearance_creation.create_control_directory_cleanup_clearance(
        SessionPrincipal(actor), request
    )
    if clearance is None:
        return {"attempt_id": attempt_id.value, "directory_id": directory_id.value,
                "outcome": "not_available"}
    if type(clearance) is ManifestHandoffSupervisorControlDirectoryCleanupConflict:
        return {"attempt_id": attempt_id.value, "directory_id": directory_id.value,
                "outcome": "rejected"}
    if getattr(clearance, "request", None) != request:
        raise SupervisorControlDirectoryCleanupOperatorUnavailable
    result = composition.execution.cleanup_control_directory(request)
    if result is None:
        outcome = "not_available"
    elif type(result) is ManifestHandoffSupervisorControlDirectoryCleanupConflict:
        outcome = "rejected"
    elif type(result) is ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired:
        outcome = "reconciliation_required"
    elif type(result) is CompletedManifestHandoffSupervisorControlDirectoryCleanup:
        outcome = result.outcome.value
    else:
        raise SupervisorControlDirectoryCleanupOperatorUnavailable
    if result is not None and type(result) is not ManifestHandoffSupervisorControlDirectoryCleanupConflict:
        if result.attempt_id != attempt_id or result.directory_id != directory_id:
            raise SupervisorControlDirectoryCleanupOperatorUnavailable
    return {"attempt_id": attempt_id.value, "directory_id": directory_id.value,
            "outcome": outcome}


def reconcile_one(engine: Engine, backend, root: Path, request):
    composition = _composition(engine, backend, root)
    result = composition.reconciliation.reconcile_control_directory_cleanup(request)
    if result is None:
        outcome = "not_available"
    elif type(result) is ManifestHandoffSupervisorControlDirectoryCleanupConflict:
        outcome = "rejected"
    elif type(result) is ReconciledManifestHandoffSupervisorControlDirectoryCleanup:
        if result.attempt_id != request.attempt_id or result.directory_id != request.directory_id:
            raise SupervisorControlDirectoryCleanupOperatorUnavailable
        outcome = result.outcome.value
    else:
        raise SupervisorControlDirectoryCleanupOperatorUnavailable
    return {"attempt_id": request.attempt_id.value,
            "directory_id": request.directory_id.value, "outcome": outcome}


def run_operator(*, command: str, database_url_file: Path,
                 backend_instance_id_file: Path, control_root_file: Path,
                 request_file: Path):
    database_url, backend, root = _configuration(
        database_url_file, backend_instance_id_file, control_root_file
    )
    if command == "execute":
        actor, directory_id = load_execute_request(request_file)
    elif command == "reconcile":
        request = load_reconcile_request(request_file)
    else:
        raise SupervisorControlDirectoryCleanupOperatorInputRejected
    engine: Engine | None = None
    try:
        engine = build_engine(database_url)
        if command == "execute":
            return execute_one(engine, backend, root, actor, directory_id)
        return reconcile_one(engine, backend, root, request)
    except SupervisorControlDirectoryCleanupOperatorInputRejected:
        raise
    except SupervisorControlDirectoryCleanupOperatorUnavailable:
        raise
    except Exception:
        raise SupervisorControlDirectoryCleanupOperatorUnavailable from None
    finally:
        if engine is not None:
            engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="liquent-supervisor-control-directory-cleanup"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("execute", "reconcile"):
        command = commands.add_parser(name)
        command.add_argument("--database-url-file", required=True, type=Path)
        command.add_argument("--backend-instance-id-file", required=True, type=Path)
        command.add_argument("--control-root-file", required=True, type=Path)
        command.add_argument("--request", required=True, type=Path)
    return parser


def _fail(code: str, status: int) -> NoReturn:
    sys.stderr.write(json.dumps({"error": code}, separators=(",", ":")) + "\n")
    raise SystemExit(status)


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = run_operator(
            command=arguments.command,
            database_url_file=arguments.database_url_file,
            backend_instance_id_file=arguments.backend_instance_id_file,
            control_root_file=arguments.control_root_file,
            request_file=arguments.request,
        )
    except SupervisorControlDirectoryCleanupOperatorInputRejected:
        _fail(SupervisorControlDirectoryCleanupOperatorInputRejected.code, 2)
    except Exception:
        _fail(SupervisorControlDirectoryCleanupOperatorUnavailable.code, 4)
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    return 0
