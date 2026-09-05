"""Owner-controlled evidence-first deletion of one PostgreSQL data volume."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

from liquent_platform.operators.disposable_postgres_reconcile import (
    _evidence_root, _observe, _owned_volume, _pairs, _timestamp,
)
from liquent_platform.operators.disposable_postgres_volume_deletion_preflight import (
    DisposablePostgresVolumeDeletionPreflightUnavailable,
    _authorization, preflight_disposable_postgres_volume_deletion,
)
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner


class DisposablePostgresVolumeDeletionUnavailable(Exception):
    code = "disposable_postgres_volume_deletion_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresVolumeDeletionUnavailable


def _historical_authorization(path: Path) -> tuple[bytes, dict]:
    try:
        raw = _private_file(path, 32_768)
        value = json.loads(raw, object_pairs_hook=_pairs)
        start, end = _timestamp(value["valid_from"]), _timestamp(value["valid_until"])
        checked_raw, checked = _authorization(
            path, clock=lambda: start + (end - start) / 2,
        )
        if checked_raw != raw:
            raise DisposablePostgresVolumeDeletionUnavailable
        return raw, checked
    except DisposablePostgresVolumeDeletionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionUnavailable from None


def _binding(current: dict, authorization_raw: bytes) -> dict:
    return {
        "schema_version": 1,
        **{key: current[key] for key in (
            "volume_deletion_id", "volume_deletion_claim_id", "volume_disposition_id",
            "retention_decision_id", "legal_hold_decision_id", "recovery_decision_id",
            "run_id", "phase", "source_commit", "image_ref", "compose_sha256",
            "retained_volume", "volume_disposition_authorization_sha256",
            "lineage_manifest_sha256", "retention_decision_sha256",
            "legal_hold_decision_sha256", "recovery_decision_sha256", "operation",
            "scope", "executor_id", "authorizer_id", "reviewer_id",
        )},
        "volume_deletion_authorization_sha256": hashlib.sha256(authorization_raw).hexdigest(),
    }


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
            or datetime.fromisoformat(value["started_at"].replace("Z", "+00:00")).tzinfo is None
        ):
            raise DisposablePostgresVolumeDeletionUnavailable
        return True
    except DisposablePostgresVolumeDeletionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionUnavailable from None


def _create_claim(path: Path, binding: dict, started_at: str, root_descriptor: int) -> None:
    descriptor = None
    try:
        content = (json.dumps(
            {**binding, "started_at": started_at},
            sort_keys=True, separators=(",", ":"),
        ) + "\n").encode()
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
        )
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            if written < 1:
                raise DisposablePostgresVolumeDeletionUnavailable
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.fsync(root_descriptor)
        if not _claim(path, binding):
            raise DisposablePostgresVolumeDeletionUnavailable
    except DisposablePostgresVolumeDeletionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _existing(path: Path, binding: dict) -> bool:
    try:
        if not path.exists():
            return False
        metadata = path.stat(follow_symlinks=False)
        value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
        if (
            not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1 or stat.S_IMODE(metadata.st_mode) != 0o600
            or type(value) is not dict
            or set(value) != set(binding) | {
                "executed_step", "absence_confirmed", "started_at", "completed_at",
                "outcome",
            }
            or any(value[key] != expected for key, expected in binding.items())
            or value["executed_step"] != "remove_exact_volume_once"
            or value["absence_confirmed"] is not True
            or value["outcome"] != "volume_removed"
        ):
            raise DisposablePostgresVolumeDeletionUnavailable
        for key in ("started_at", "completed_at"):
            if (
                type(value[key]) is not str
                or datetime.fromisoformat(value[key].replace("Z", "+00:00")).tzinfo is None
            ):
                raise DisposablePostgresVolumeDeletionUnavailable
        return True
    except DisposablePostgresVolumeDeletionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionUnavailable from None


def _write_evidence(
    root: Path, root_descriptor: int, final: Path, record: dict, binding: dict,
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
                raise DisposablePostgresVolumeDeletionUnavailable
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.link(temporary, final)
        temporary.unlink()
        os.fsync(root_descriptor)
        if not _existing(final, binding):
            raise DisposablePostgresVolumeDeletionUnavailable
    except DisposablePostgresVolumeDeletionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _release_claim(path: Path, binding: dict, root_descriptor: int) -> None:
    try:
        if not path.exists():
            return
        if not _claim(path, binding):
            raise DisposablePostgresVolumeDeletionUnavailable
        os.unlink(path)
        os.fsync(root_descriptor)
    except DisposablePostgresVolumeDeletionUnavailable:
        raise
    except Exception:
        raise DisposablePostgresVolumeDeletionUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_volume_deletion", "outcome": outcome,
        "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def delete_disposable_postgres_volume(
    *, docker_executable: Path, volume_disposition_file: Path,
    volume_deletion_file: Path, lineage_manifest_file: Path,
    retention_decision_file: Path, legal_hold_decision_file: Path,
    recovery_decision_file: Path, project_name: str, evidence_directory: Path,
    processes=None, clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        processes = processes or LocalBoundedProcessRunner()
        authorization_raw, current = _historical_authorization(volume_deletion_file)
        if (
            project_name != f"liquent-{current['run_id']}"
            or current["retained_volume"] != f"{project_name}-postgres-data"
        ):
            raise DisposablePostgresVolumeDeletionUnavailable
        binding = _binding(current, authorization_raw)
        evidence_stem = hashlib.sha256(current["volume_deletion_id"].encode()).hexdigest()
        claim_stem = hashlib.sha256(current["volume_deletion_claim_id"].encode()).hexdigest()
        final = evidence_directory / f"postgres-volume-deletion-{evidence_stem}.json"
        claim = evidence_directory / f".postgres-volume-deletion-{claim_stem}.claim"
        root_descriptor = _evidence_root(evidence_directory)
        if _existing(final, binding):
            _release_claim(claim, binding, root_descriptor)
            return _result("volume_removed")
        preflight_raw = preflight_disposable_postgres_volume_deletion(
            docker_executable=docker_executable,
            volume_disposition_file=volume_disposition_file,
            volume_deletion_file=volume_deletion_file,
            lineage_manifest_file=lineage_manifest_file,
            retention_decision_file=retention_decision_file,
            legal_hold_decision_file=legal_hold_decision_file,
            recovery_decision_file=recovery_decision_file,
            project_name=project_name, evidence_directory=evidence_directory,
            processes=processes, clock=clock,
        )
        preflight = json.loads(preflight_raw, object_pairs_hook=_pairs)
        if (
            type(preflight) is not dict
            or set(preflight) != {"schema_version", "operation", "outcome"}
            or preflight["schema_version"] != 1
            or preflight["operation"] != "disposable_postgres_volume_deletion_preflight"
            or preflight["outcome"] not in {"ready", "rejected", "investigation_required"}
        ):
            raise DisposablePostgresVolumeDeletionUnavailable
        if preflight["outcome"] != "ready":
            return _result(preflight["outcome"])
        started = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        _create_claim(claim, binding, started, root_descriptor)
        docker = str(docker_executable)
        volume = current["retained_volume"]
        observed = _observe(
            processes, (docker, "volume", "inspect", volume), maximum=1_048_576,
        )
        if not _owned_volume(observed.stdout, name=volume, project=project_name):
            raise DisposablePostgresVolumeDeletionUnavailable
        _observe(processes, (docker, "volume", "rm", volume), maximum=65_536)
        absence = _observe(processes, (
            docker, "volume", "ls", "--filter", f"name=^{volume}$",
            "--format", "{{.Name}}",
        ), maximum=65_536)
        if absence.stdout:
            raise DisposablePostgresVolumeDeletionUnavailable
        completed = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        _write_evidence(evidence_directory, root_descriptor, final, {
            **binding, "executed_step": "remove_exact_volume_once",
            "absence_confirmed": True, "started_at": started,
            "completed_at": completed, "outcome": "volume_removed",
        }, binding)
        _release_claim(claim, binding, root_descriptor)
        return _result("volume_removed")
    except DisposablePostgresVolumeDeletionUnavailable:
        raise
    except DisposablePostgresVolumeDeletionPreflightUnavailable:
        raise DisposablePostgresVolumeDeletionUnavailable from None
    except Exception:
        raise DisposablePostgresVolumeDeletionUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-disposable-postgres-volume-delete", add_help=False)
    for name in (
        "docker-executable", "volume-disposition-file", "volume-deletion-file",
        "lineage-manifest-file", "retention-decision-file",
        "legal-hold-decision-file", "recovery-decision-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        sys.stdout.buffer.write(delete_disposable_postgres_volume(
            **vars(parser.parse_args(argv)),
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
