from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_volume_disposition as disposition
from liquent_platform.operators.staging_process_adapter import ProcessObservation


NOW = datetime(2026, 8, 23, 14, tzinfo=UTC)
RUN = "volume-run-390"
PROJECT = f"liquent-{RUN}"
VOLUME = f"{PROJECT}-postgres-data"


def _private(path: Path, value: dict | bytes) -> Path:
    if isinstance(value, dict):
        value = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(value)
    os.chmod(path, 0o600)
    return path


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _current(**values) -> dict:
    return {
        **values, "valid_from": "2026-08-23T13:30:00Z",
        "valid_until": "2026-08-23T14:30:00Z",
    }


class Processes:
    def __init__(self, stdout: bytes):
        self.stdout, self.calls = stdout, []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return ProcessObservation(0, self.stdout, b"", False, False, False)


def _volume(*, project: str = PROJECT, name: str = VOLUME) -> bytes:
    return json.dumps([{
        "Name": name, "Labels": {"com.docker.compose.project": project},
    }]).encode()


def _inputs(
    tmp_path: Path, *, retention: str = "cleared", hold: str = "clear",
    backup: str = "verified", restore: str = "verified", later_use: bool = False,
    volume: bytes | None = None,
):
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    artifacts = []
    for kind in (
        "staging_evidence", "recovery_disposition", "cleanup_authorization",
        "cleanup_finalization_evidence",
    ):
        path = _private(tmp_path / f"{kind}.json", f"{kind}\n".encode())
        artifacts.append({"kind": kind, "path": str(path), "sha256": _hash(path)})
    lineage = _private(tmp_path / "lineage.json", {
        "schema_version": 1, "run_id": RUN, "phase": "disposable_postgres",
        "source_commit": "a" * 40,
        "image_ref": "registry.example/liquent@sha256:" + "b" * 64,
        "compose_sha256": "c" * 64, "retained_volume": VOLUME,
        "cleanup_finalized": True, "later_use": later_use, "artifacts": artifacts,
    })
    retention_file = _private(tmp_path / "retention.json", _current(
        schema_version=1, retention_decision_id="retention-390", run_id=RUN,
        retained_volume=VOLUME, policy_version="retention-v1", outcome=retention,
        authorizer_id="retention-authorizer",
    ))
    hold_file = _private(tmp_path / "hold.json", _current(
        schema_version=1, legal_hold_decision_id="hold-390", run_id=RUN,
        retained_volume=VOLUME, outcome=hold, authorizer_id="hold-authorizer",
    ))
    recovery_file = _private(tmp_path / "recovery.json", _current(
        schema_version=1, recovery_decision_id="recovery-390", run_id=RUN,
        retained_volume=VOLUME, policy_version="recovery-v1",
        backup_required=True, backup_outcome=backup, backup_id="backup-390",
        backup_integrity_sha256="d" * 64, restore_required=True,
        restore_outcome=restore, restore_id="restore-390",
        authorizer_id="recovery-authorizer",
    ))
    authorization = _private(tmp_path / "volume-disposition.json", _current(
        schema_version=1, volume_disposition_id="volume-disposition-390",
        run_id=RUN, phase="disposable_postgres", source_commit="a" * 40,
        image_ref="registry.example/liquent@sha256:" + "b" * 64,
        compose_sha256="c" * 64, lineage_manifest_sha256=_hash(lineage),
        retention_decision_sha256=_hash(retention_file),
        legal_hold_decision_sha256=_hash(hold_file),
        recovery_decision_sha256=_hash(recovery_file),
        operation="resolve_disposable_postgres_volume_disposition",
        executor_id="volume-executor", authorizer_id="volume-authorizer",
        reviewer_id="volume-reviewer",
    ))
    docker = _private(tmp_path / "docker", b"binary\n")
    processes = Processes(_volume() if volume is None else volume)
    return {
        "docker_executable": docker, "volume_disposition_file": authorization,
        "lineage_manifest_file": lineage, "retention_decision_file": retention_file,
        "legal_hold_decision_file": hold_file, "recovery_decision_file": recovery_file,
        "project_name": PROJECT, "evidence_directory": evidence,
        "processes": processes, "clock": lambda: NOW,
    }, processes


def test_all_positive_facts_allow_only_deletion_review(tmp_path: Path) -> None:
    values, processes = _inputs(tmp_path)
    result = disposition.resolve_disposable_postgres_volume_disposition(**values)
    assert json.loads(result) == {
        "operation": "disposable_postgres_volume_disposition",
        "outcome": "deletion_review_eligible", "schema_version": 1,
    }
    assert [call[0] for call in processes.calls] == [
        (str(values["docker_executable"]), "volume", "inspect", VOLUME),
    ]
    assert not any(set(call[0]) & {"rm", "remove", "prune", "mount"} for call in processes.calls)


@pytest.mark.parametrize("changes", [
    {"retention": "retain"}, {"hold": "active"}, {"backup": "pending"},
    {"restore": "pending"}, {"later_use": True},
])
def test_negative_complete_facts_retain(tmp_path: Path, changes: dict) -> None:
    values, _ = _inputs(tmp_path, **changes)
    result = disposition.resolve_disposable_postgres_volume_disposition(**values)
    assert json.loads(result)["outcome"] == "retain"


@pytest.mark.parametrize("changes", [
    {"hold": "conflict"}, {"volume": b""},
    {"volume": _volume(project="foreign-project")},
])
def test_conflict_or_volume_absence_requires_investigation(
    tmp_path: Path, changes: dict,
) -> None:
    values, _ = _inputs(tmp_path, **changes)
    result = disposition.resolve_disposable_postgres_volume_disposition(**values)
    assert json.loads(result)["outcome"] == "investigation_required"


def test_hash_mismatch_stops_before_docker(tmp_path: Path) -> None:
    values, processes = _inputs(tmp_path)
    values["retention_decision_file"].write_bytes(
        values["retention_decision_file"].read_bytes() + b" "
    )
    with pytest.raises(disposition.DisposablePostgresVolumeDispositionUnavailable):
        disposition.resolve_disposable_postgres_volume_disposition(**values)
    assert processes.calls == []


def test_open_cleanup_claim_is_unavailable_without_mutation(tmp_path: Path) -> None:
    values, processes = _inputs(tmp_path)
    claim = _private(values["evidence_directory"] / ".postgres-cleanup-open.claim", b"claim\n")
    with pytest.raises(disposition.DisposablePostgresVolumeDispositionUnavailable):
        disposition.resolve_disposable_postgres_volume_disposition(**values)
    assert claim.exists() and processes.calls == []


def test_stale_authority_and_duplicate_json_fail_closed(tmp_path: Path) -> None:
    values, processes = _inputs(tmp_path)
    raw = values["volume_disposition_file"].read_text()
    values["volume_disposition_file"].write_text(
        raw.replace('"schema_version":1', '"schema_version":1,"schema_version":1')
    )
    with pytest.raises(disposition.DisposablePostgresVolumeDispositionUnavailable):
        disposition.resolve_disposable_postgres_volume_disposition(**values)
    assert processes.calls == []


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_volume_disposition",'
        b'"outcome":"retain","schema_version":1}\n'
    )
    monkeypatch.setattr(
        disposition, "resolve_disposable_postgres_volume_disposition", lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--volume-disposition-file", "/x/auth",
        "--lineage-manifest-file", "/x/lineage", "--retention-decision-file", "/x/retention",
        "--legal-hold-decision-file", "/x/hold", "--recovery-decision-file", "/x/recovery",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert disposition.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert disposition.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_entry_point_is_installed() -> None:
    project = Path(__file__).parents[1] / "pyproject.toml"
    assert (
        'liquent-disposable-postgres-volume-disposition = '
        '"liquent_platform.operators.disposable_postgres_volume_disposition:main"'
    ) in project.read_text()
