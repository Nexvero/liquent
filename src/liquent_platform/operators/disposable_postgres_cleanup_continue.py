"""Owner-controlled continuation of one reconciled PostgreSQL runtime cleanup."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from liquent_platform.operators.disposable_postgres_cleanup_finalize import (
    _historical_reconciliation,
)
from liquent_platform.operators.disposable_postgres_cleanup_reconcile import (
    DisposablePostgresCleanupReconcileUnavailable, _claim, _historical_cleanup,
    reconcile_disposable_postgres_cleanup,
)
from liquent_platform.operators.disposable_postgres_reconcile import (
    DisposablePostgresReconcileUnavailable, _evidence_root, _historical,
    _observe, _owned_volume, _pairs, _timestamp,
)
from liquent_platform.operators.disposable_postgres_runtime_cleanup import (
    _absent, _binding,
)
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import (
    COMMIT, IMAGE, OPAQUE, SHA256,
)
from liquent_platform.operators.staging_process_adapter import LocalBoundedProcessRunner


STATES = {"container_stopped", "container_removed", "application_network_removed"}
STEPS = {
    "container_stopped": ["container_absent", "application_network_absent", "data_network_absent"],
    "container_removed": ["application_network_absent", "data_network_absent"],
    "application_network_removed": ["data_network_absent"],
}
KEYS = {
    "schema_version", "cleanup_continuation_id", "cleanup_reconciliation_id",
    "cleanup_id", "run_id", "phase", "source_commit", "image_ref",
    "compose_sha256", "reconciliation_id", "claim_reconciliation_id",
    "disposition_id", "staging_evidence_sha256", "reconciliation_evidence_sha256",
    "claim_reconciliation_evidence_sha256", "disposition_authorization_sha256",
    "cleanup_authorization_sha256", "cleanup_reconciliation_authorization_sha256",
    "operation", "scope", "resume_from", "executor_id", "authorizer_id",
    "valid_from", "valid_until",
}


class DisposablePostgresCleanupContinueUnavailable(Exception):
    code = "disposable_postgres_cleanup_continue_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise DisposablePostgresCleanupContinueUnavailable


def _authorization(path: Path, *, clock) -> dict:
    try:
        value = json.loads(_private_file(path, 32_768), object_pairs_hook=_pairs)
        if type(value) is not dict or set(value) != KEYS or value["schema_version"] != 1:
            raise DisposablePostgresCleanupContinueUnavailable
        if (
            value["phase"] != "disposable_postgres" or value["scope"] != "runtime_only"
            or value["operation"] != "continue_disposable_postgres_runtime_cleanup"
            or value["resume_from"] not in STATES
        ):
            raise DisposablePostgresCleanupContinueUnavailable
        for key in (
            "cleanup_continuation_id", "cleanup_reconciliation_id", "cleanup_id",
            "run_id", "reconciliation_id", "claim_reconciliation_id", "disposition_id",
            "executor_id", "authorizer_id",
        ):
            if type(value[key]) is not str or OPAQUE.fullmatch(value[key]) is None:
                raise DisposablePostgresCleanupContinueUnavailable
        if value["executor_id"] == value["authorizer_id"]:
            raise DisposablePostgresCleanupContinueUnavailable
        if type(value["source_commit"]) is not str or COMMIT.fullmatch(value["source_commit"]) is None:
            raise DisposablePostgresCleanupContinueUnavailable
        if type(value["image_ref"]) is not str or IMAGE.fullmatch(value["image_ref"]) is None:
            raise DisposablePostgresCleanupContinueUnavailable
        for key in (
            "compose_sha256", "staging_evidence_sha256", "reconciliation_evidence_sha256",
            "claim_reconciliation_evidence_sha256", "disposition_authorization_sha256",
            "cleanup_authorization_sha256", "cleanup_reconciliation_authorization_sha256",
        ):
            if type(value[key]) is not str or SHA256.fullmatch(value[key]) is None:
                raise DisposablePostgresCleanupContinueUnavailable
        start, end, now = _timestamp(value["valid_from"]), _timestamp(value["valid_until"]), clock()
        if (
            type(now) is not datetime or now.tzinfo is None or end <= start
            or end - start > timedelta(hours=1)
            or not start <= now.astimezone(UTC) <= end
        ):
            raise DisposablePostgresCleanupContinueUnavailable
        return value
    except DisposablePostgresCleanupContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupContinueUnavailable from None


def _evidence_binding(current: dict, authorization_file: Path, project: str) -> dict:
    return {
        "schema_version": 1,
        "cleanup_continuation_id": current["cleanup_continuation_id"],
        "cleanup_reconciliation_id": current["cleanup_reconciliation_id"],
        "cleanup_id": current["cleanup_id"], "run_id": current["run_id"],
        "phase": "disposable_postgres", "source_commit": current["source_commit"],
        "image_ref": current["image_ref"], "compose_sha256": current["compose_sha256"],
        "scope": "runtime_only", "resume_from": current["resume_from"],
        "reconciliation_id": current["reconciliation_id"],
        "claim_reconciliation_id": current["claim_reconciliation_id"],
        "disposition_id": current["disposition_id"],
        "staging_evidence_sha256": current["staging_evidence_sha256"],
        "reconciliation_evidence_sha256": current["reconciliation_evidence_sha256"],
        "claim_reconciliation_evidence_sha256": current["claim_reconciliation_evidence_sha256"],
        "disposition_authorization_sha256": current["disposition_authorization_sha256"],
        "cleanup_authorization_sha256": current["cleanup_authorization_sha256"],
        "cleanup_reconciliation_authorization_sha256": current["cleanup_reconciliation_authorization_sha256"],
        "continuation_authorization_sha256": hashlib.sha256(
            _private_file(authorization_file, 32_768)
        ).hexdigest(),
        "executor_id": current["executor_id"], "authorizer_id": current["authorizer_id"],
        "container": f"{project}-postgres-1",
        "application_network": f"{project}-application",
        "data_network": f"{project}-data", "retained_volume": f"{project}-postgres-data",
        "remaining_steps": STEPS[current["resume_from"]] + ["data_volume_retained"],
    }


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
            or set(value) != set(binding) | {"outcome", "started_at", "completed_at"}
            or any(value[key] != expected for key, expected in binding.items())
            or value["outcome"] != "runtime_removed_pending_finalization"
        ):
            raise DisposablePostgresCleanupContinueUnavailable
        for key in ("started_at", "completed_at"):
            parsed = datetime.fromisoformat(value[key].replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise DisposablePostgresCleanupContinueUnavailable
        return True
    except DisposablePostgresCleanupContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupContinueUnavailable from None


def _continuation_claim(path: Path, binding: dict) -> bool:
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
            raise DisposablePostgresCleanupContinueUnavailable
        return True
    except DisposablePostgresCleanupContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupContinueUnavailable from None


def _write(root: Path, root_descriptor: int, final: Path, record: dict) -> None:
    temporary = root / f".{final.stem}-{os.getpid()}.tmp"
    opened = None
    try:
        content = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        opened = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        view = memoryview(content)
        while view:
            written = os.write(opened, view)
            if written < 1:
                raise DisposablePostgresCleanupContinueUnavailable
            view = view[written:]
        os.fsync(opened)
        os.close(opened)
        opened = None
        os.link(temporary, final)
        temporary.unlink()
        os.fsync(root_descriptor)
        binding = {key: record[key] for key in record if key not in {"outcome", "started_at", "completed_at"}}
        if not _existing(final, binding):
            raise DisposablePostgresCleanupContinueUnavailable
    except DisposablePostgresCleanupContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupContinueUnavailable from None
    finally:
        if opened is not None:
            os.close(opened)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _release(path: Path, binding: dict, root_descriptor: int) -> None:
    try:
        if not path.exists():
            return
        if not _continuation_claim(path, binding):
            raise DisposablePostgresCleanupContinueUnavailable
        os.unlink(path)
        os.fsync(root_descriptor)
    except DisposablePostgresCleanupContinueUnavailable:
        raise
    except Exception:
        raise DisposablePostgresCleanupContinueUnavailable from None


def _result(outcome: str) -> bytes:
    return (json.dumps({
        "operation": "disposable_postgres_runtime_cleanup_continuation",
        "outcome": outcome, "schema_version": 1,
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()


def continue_disposable_postgres_cleanup(
    *, docker_executable: Path, authorization_file: Path,
    reconciliation_file: Path, claim_reconciliation_file: Path,
    disposition_file: Path, cleanup_file: Path,
    cleanup_reconciliation_file: Path, cleanup_continuation_file: Path,
    staging_evidence_file: Path, compose_file: Path,
    runtime_environment_file: Path, image_environment_file: Path,
    project_name: str, evidence_directory: Path, processes=None,
    clock=lambda: datetime.now(UTC),
) -> bytes:
    root_descriptor = None
    try:
        original = _historical(authorization_file)
        cleanup = _historical_cleanup(cleanup_file)
        previous = _historical_reconciliation(cleanup_reconciliation_file)
        current = _authorization(cleanup_continuation_file, clock=clock)
        previous_raw = _private_file(cleanup_reconciliation_file, 32_768)
        if (
            current["cleanup_reconciliation_authorization_sha256"]
            != hashlib.sha256(previous_raw).hexdigest()
            or any(current[key] != previous[key] for key in (
                "cleanup_reconciliation_id", "cleanup_id", "run_id", "source_commit",
                "image_ref", "compose_sha256", "reconciliation_id",
                "claim_reconciliation_id", "disposition_id", "staging_evidence_sha256",
                "reconciliation_evidence_sha256", "claim_reconciliation_evidence_sha256",
                "disposition_authorization_sha256", "cleanup_authorization_sha256",
            ))
            or cleanup["cleanup_id"] != current["cleanup_id"]
            or original.run_id != current["run_id"]
            or project_name != f"liquent-{original.run_id}"
            or not docker_executable.is_absolute() or not docker_executable.is_file()
            or not os.access(docker_executable, os.X_OK)
        ):
            raise DisposablePostgresCleanupContinueUnavailable
        cleanup_binding = _binding(original, cleanup, cleanup_file, project_name)
        cleanup_stem = hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        cleanup_claim = evidence_directory / f".postgres-cleanup-{cleanup_stem}.claim"
        if not _claim(cleanup_claim, cleanup_binding):
            raise DisposablePostgresCleanupContinueUnavailable
        binding = _evidence_binding(current, cleanup_continuation_file, project_name)
        stem = hashlib.sha256(current["cleanup_continuation_id"].encode()).hexdigest()
        claim = evidence_directory / f".postgres-cleanup-continuation-{stem}.claim"
        final = evidence_directory / f"postgres-cleanup-continuation-{stem}.json"
        root_descriptor = _evidence_root(evidence_directory)
        if _existing(final, binding):
            _release(claim, binding, root_descriptor)
            return _result("runtime_removed_pending_finalization")
        if claim.exists():
            raise DisposablePostgresCleanupContinueUnavailable
        start, end = _timestamp(previous["valid_from"]), _timestamp(previous["valid_until"])
        observed_raw = reconcile_disposable_postgres_cleanup(
            docker_executable=docker_executable, authorization_file=authorization_file,
            reconciliation_file=reconciliation_file,
            claim_reconciliation_file=claim_reconciliation_file,
            disposition_file=disposition_file, cleanup_file=cleanup_file,
            cleanup_reconciliation_file=cleanup_reconciliation_file,
            staging_evidence_file=staging_evidence_file, compose_file=compose_file,
            runtime_environment_file=runtime_environment_file,
            image_environment_file=image_environment_file, project_name=project_name,
            evidence_directory=evidence_directory, processes=processes,
            clock=lambda: start + (end - start) / 2,
        )
        observed = json.loads(observed_raw, object_pairs_hook=_pairs)
        if (
            type(observed) is not dict
            or set(observed) != {"schema_version", "operation", "outcome"}
            or observed["schema_version"] != 1
            or observed["operation"] != "disposable_postgres_runtime_cleanup_reconciliation"
        ):
            raise DisposablePostgresCleanupContinueUnavailable
        if observed["outcome"] != current["resume_from"]:
            return _result("rejected")
        started = clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        claim_content = (json.dumps(dict(binding, started_at=started), sort_keys=True, separators=(",", ":")) + "\n").encode()
        opened = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            if os.write(opened, claim_content) != len(claim_content):
                raise DisposablePostgresCleanupContinueUnavailable
            os.fsync(opened)
        finally:
            os.close(opened)
        os.fsync(root_descriptor)

        runner = processes or LocalBoundedProcessRunner()
        docker = str(docker_executable)
        container = binding["container"]
        networks = (binding["application_network"], binding["data_network"])
        volume = binding["retained_volume"]
        if current["resume_from"] == "container_stopped":
            _observe(runner, (docker, "container", "rm", container), maximum=65_536)
            if not _absent(_observe(runner, (
                docker, "container", "ls", "--filter", f"name=^{container}$", "--format", "{{.Names}}",
            ), maximum=65_536).stdout):
                raise DisposablePostgresCleanupContinueUnavailable
        first = 0 if current["resume_from"] in {"container_stopped", "container_removed"} else 1
        for name in networks[first:]:
            _observe(runner, (docker, "network", "rm", name), maximum=65_536)
            if not _absent(_observe(runner, (
                docker, "network", "ls", "--filter", f"name=^{name}$", "--format", "{{.Name}}",
            ), maximum=65_536).stdout):
                raise DisposablePostgresCleanupContinueUnavailable
        retained = _observe(runner, (docker, "volume", "inspect", volume), maximum=1_048_576).stdout
        if not _owned_volume(retained, name=volume, project=project_name):
            raise DisposablePostgresCleanupContinueUnavailable
        record = dict(binding)
        record.update({
            "outcome": "runtime_removed_pending_finalization", "started_at": started,
            "completed_at": clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
        })
        _write(evidence_directory, root_descriptor, final, record)
        _release(claim, binding, root_descriptor)
        return _result("runtime_removed_pending_finalization")
    except DisposablePostgresCleanupContinueUnavailable:
        raise
    except (
        DisposablePostgresCleanupReconcileUnavailable,
        DisposablePostgresReconcileUnavailable,
    ):
        raise DisposablePostgresCleanupContinueUnavailable from None
    except Exception:
        raise DisposablePostgresCleanupContinueUnavailable from None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(prog="liquent-disposable-postgres-cleanup-continue", add_help=False)
    for name in (
        "docker-executable", "authorization-file", "reconciliation-file",
        "claim-reconciliation-file", "disposition-file", "cleanup-file",
        "cleanup-reconciliation-file", "cleanup-continuation-file",
        "staging-evidence-file", "compose-file", "runtime-env-file",
        "image-env-file", "evidence-directory",
    ):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--project-name", required=True)
    try:
        value = vars(parser.parse_args(argv))
        sys.stdout.buffer.write(continue_disposable_postgres_cleanup(
            docker_executable=value["docker_executable"], authorization_file=value["authorization_file"],
            reconciliation_file=value["reconciliation_file"], claim_reconciliation_file=value["claim_reconciliation_file"],
            disposition_file=value["disposition_file"], cleanup_file=value["cleanup_file"],
            cleanup_reconciliation_file=value["cleanup_reconciliation_file"],
            cleanup_continuation_file=value["cleanup_continuation_file"],
            staging_evidence_file=value["staging_evidence_file"], compose_file=value["compose_file"],
            runtime_environment_file=value["runtime_env_file"], image_environment_file=value["image_env_file"],
            project_name=value["project_name"], evidence_directory=value["evidence_directory"],
        ))
        return 0
    except SystemExit:
        return 2
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
