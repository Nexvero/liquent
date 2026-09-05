"""Owner-controlled terminal supervisor control-directory retirement."""

from __future__ import annotations

import argparse
from datetime import timezone
import json
from pathlib import Path
import sys

from sqlalchemy import Engine

from liquent_platform.application.manifest_handoff_supervisor_control_directory_retirement import (
    PersistentManifestHandoffSupervisorControlDirectoryRetirement,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    ManifestHandoffSupervisorControlDirectoryConflict,
    RetiredManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.operators.initial_bootstrap import _read_private, _write_result
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_control_directories import (
    DatabaseManifestHandoffSupervisorControlDirectories,
)
from liquent_platform.persistence.manifest_handoff_supervisor_journal import (
    DatabaseManifestHandoffSupervisorJournal,
)


class SupervisorControlDirectoryRetirementOperatorUnavailable(Exception):
    """Detail-free private process-boundary failure."""


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _one_line(value: str) -> str:
    if value.endswith("\n"):
        value = value[:-1]
    if not value or "\n" in value or "\r" in value or value.strip() != value:
        raise SupervisorControlDirectoryRetirementOperatorUnavailable
    return value


def load_request(path: Path) -> ManifestHandoffSupervisorControlDirectoryId:
    try:
        value = json.loads(_read_private(path), object_pairs_hook=_pairs)
        if type(value) is not dict or set(value) != {"directory_id"}:
            raise ValueError
        directory = value["directory_id"]
        if type(directory) is not str or not directory or directory.strip() != directory:
            raise ValueError
        return ManifestHandoffSupervisorControlDirectoryId(directory)
    except Exception:
        raise SupervisorControlDirectoryRetirementOperatorUnavailable from None


def execute_one(
    engine: Engine,
    backend: ManifestHandoffSupervisorBackendInstanceId,
    directory_id: ManifestHandoffSupervisorControlDirectoryId,
) -> dict[str, str] | None:
    if not DatabaseReadinessProbe(engine).check().ready:
        raise SupervisorControlDirectoryRetirementOperatorUnavailable
    retirement = PersistentManifestHandoffSupervisorControlDirectoryRetirement(
        registry=DatabaseManifestHandoffSupervisorControlDirectories(engine),
        journal=DatabaseManifestHandoffSupervisorJournal(
            engine, backend_instance_id=backend,
        ),
    )
    result = retirement.retire(directory_id)
    if result is None or type(result) is ManifestHandoffSupervisorControlDirectoryConflict:
        return None
    if (
        type(result) is not RetiredManifestHandoffSupervisorControlDirectory
        or result.directory_id != directory_id
    ):
        raise SupervisorControlDirectoryRetirementOperatorUnavailable
    retired_at = result.retired_at.astimezone(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    return {
        "directory_id": result.directory_id.value,
        "handle_id": result.handle_id.value,
        "retired_at": retired_at,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="liquent-supervisor-control-directory-retire"
    )
    parser.add_argument("--database-url-file", required=True, type=Path)
    parser.add_argument("--backend-instance-id-file", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--result-file", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    engine: Engine | None = None
    try:
        database_url = _one_line(_read_private(args.database_url_file))
        backend = ManifestHandoffSupervisorBackendInstanceId(
            _one_line(_read_private(args.backend_instance_id_file))
        )
        directory_id = load_request(args.request)
        engine = build_engine(database_url)
        result = execute_one(engine, backend, directory_id)
        if result is None:
            sys.stdout.write('{"outcome":"rejected"}\n')
            return 1
        _write_result(args.result_file, result)
        sys.stdout.write('{"outcome":"applied"}\n')
        return 0
    except (
        SupervisorControlDirectoryRetirementOperatorUnavailable,
        ManifestHandoffRegistryUnavailable,
        TypeError,
        ValueError,
    ):
        sys.stderr.write('{"error":"operator_unavailable"}\n')
        return 2
    except Exception:
        sys.stderr.write('{"error":"operator_unavailable"}\n')
        return 2
    finally:
        if engine is not None:
            engine.dispose()
