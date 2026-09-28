from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_volume_deletion as deletion
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from tests.test_lq390_disposable_postgres_volume_disposition import (
    PROJECT, VOLUME, _private, _volume,
)
from tests.test_lq392_disposable_postgres_volume_deletion_preflight import _values


def _observation(
    stdout: bytes = b"", *, returncode: int = 0, stderr: bytes = b"",
    timed_out: bool = False,
) -> ProcessObservation:
    return ProcessObservation(returncode, stdout, stderr, timed_out, False, False)


class Processes:
    def __init__(self, observations):
        self.observations, self.calls = list(observations), []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.observations.pop(0)


def _success_processes(*, after: bytes = b"") -> Processes:
    return Processes([
        _observation(_volume()),
        _observation(_volume()),
        _observation((VOLUME + "\n").encode()),
        _observation(after),
    ])


def _operator_values(tmp_path: Path, **changes):
    values, _ = _values(tmp_path, **changes)
    values["processes"] = _success_processes()
    return values


def _paths(values: dict) -> tuple[Path, Path]:
    current = json.loads(values["volume_deletion_file"].read_text())
    claim_stem = hashlib.sha256(current["volume_deletion_claim_id"].encode()).hexdigest()
    evidence_stem = hashlib.sha256(current["volume_deletion_id"].encode()).hexdigest()
    root = values["evidence_directory"]
    return (
        root / f".postgres-volume-deletion-{claim_stem}.claim",
        root / f"postgres-volume-deletion-{evidence_stem}.json",
    )


def test_exact_volume_is_removed_once_evidence_first(tmp_path: Path) -> None:
    values = _operator_values(tmp_path)
    processes = values["processes"]
    result = deletion.delete_disposable_postgres_volume(**values)
    assert json.loads(result)["outcome"] == "volume_removed"
    claim, evidence = _paths(values)
    assert not claim.exists() and evidence.exists()
    record = json.loads(evidence.read_text())
    assert record["outcome"] == "volume_removed"
    assert record["executed_step"] == "remove_exact_volume_once"
    assert record["absence_confirmed"] is True
    assert [call[0] for call in processes.calls] == [
        (str(values["docker_executable"]), "volume", "inspect", VOLUME),
        (str(values["docker_executable"]), "volume", "inspect", VOLUME),
        (str(values["docker_executable"]), "volume", "rm", VOLUME),
        (str(values["docker_executable"]), "volume", "ls", "--filter",
         f"name=^{VOLUME}$", "--format", "{{.Name}}"),
    ]
    assert sum("rm" in call[0] for call in processes.calls) == 1


@pytest.mark.parametrize(("changes", "outcome"), [
    ({"retention": "retain"}, "rejected"),
    ({"hold": "active"}, "rejected"),
    ({"hold": "conflict"}, "investigation_required"),
])
def test_non_ready_preflight_never_creates_claim(
    tmp_path: Path, changes: dict, outcome: str,
) -> None:
    values, processes = _values(tmp_path, **changes)
    result = deletion.delete_disposable_postgres_volume(**values)
    assert json.loads(result)["outcome"] == outcome
    claim, evidence = _paths(values)
    assert not claim.exists() and not evidence.exists()
    assert len(processes.calls) == 1


def test_last_binding_conflict_leaves_claim_without_remove(tmp_path: Path) -> None:
    values = _operator_values(tmp_path)
    values["processes"] = Processes([
        _observation(_volume()), _observation(_volume(project="foreign-project")),
    ])
    with pytest.raises(deletion.DisposablePostgresVolumeDeletionUnavailable):
        deletion.delete_disposable_postgres_volume(**values)
    claim, evidence = _paths(values)
    assert claim.exists() and not evidence.exists()
    assert not any("rm" in call[0] for call in values["processes"].calls)


@pytest.mark.parametrize("failure", [
    _observation(returncode=1), _observation(timed_out=True),
    _observation(stderr=b"ambiguous"),
])
def test_unknown_remove_outcome_keeps_claim_without_retry(
    tmp_path: Path, failure: ProcessObservation,
) -> None:
    values = _operator_values(tmp_path)
    values["processes"] = Processes([
        _observation(_volume()), _observation(_volume()), failure,
    ])
    with pytest.raises(deletion.DisposablePostgresVolumeDeletionUnavailable):
        deletion.delete_disposable_postgres_volume(**values)
    claim, evidence = _paths(values)
    assert claim.exists() and not evidence.exists()
    assert sum("rm" in call[0] for call in values["processes"].calls) == 1


def test_unconfirmed_absence_keeps_claim_and_does_not_remove_twice(tmp_path: Path) -> None:
    values = _operator_values(tmp_path)
    values["processes"] = _success_processes(after=(VOLUME + "\n").encode())
    with pytest.raises(deletion.DisposablePostgresVolumeDeletionUnavailable):
        deletion.delete_disposable_postgres_volume(**values)
    claim, evidence = _paths(values)
    assert claim.exists() and not evidence.exists()
    assert sum("rm" in call[0] for call in values["processes"].calls) == 1


def test_existing_claim_stops_before_docker_and_is_preserved(tmp_path: Path) -> None:
    values = _operator_values(tmp_path)
    claim, evidence = _paths(values)
    _private(claim, b"foreign-claim\n")
    with pytest.raises(deletion.DisposablePostgresVolumeDeletionUnavailable):
        deletion.delete_disposable_postgres_volume(**values)
    assert claim.exists() and not evidence.exists()
    assert values["processes"].calls == []


def test_evidence_retry_releases_claim_without_preflight_or_docker(
    tmp_path: Path, monkeypatch,
) -> None:
    values = _operator_values(tmp_path)
    original_release = deletion._release_claim
    monkeypatch.setattr(
        deletion, "_release_claim",
        lambda *_: (_ for _ in ()).throw(deletion.DisposablePostgresVolumeDeletionUnavailable()),
    )
    with pytest.raises(deletion.DisposablePostgresVolumeDeletionUnavailable):
        deletion.delete_disposable_postgres_volume(**values)
    claim, evidence = _paths(values)
    assert claim.exists() and evidence.exists()

    monkeypatch.setattr(deletion, "_release_claim", original_release)
    values["processes"] = Processes([])
    result = deletion.delete_disposable_postgres_volume(**values)
    assert json.loads(result)["outcome"] == "volume_removed"
    assert not claim.exists() and evidence.exists()
    assert values["processes"].calls == []


def test_final_evidence_is_idempotent_without_docker(tmp_path: Path) -> None:
    values = _operator_values(tmp_path)
    deletion.delete_disposable_postgres_volume(**values)
    values["processes"] = Processes([])
    result = deletion.delete_disposable_postgres_volume(**values)
    assert json.loads(result)["outcome"] == "volume_removed"
    assert values["processes"].calls == []


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_volume_deletion",'
        b'"outcome":"volume_removed","schema_version":1}\n'
    )
    monkeypatch.setattr(deletion, "delete_disposable_postgres_volume", lambda **_: expected)
    arguments = [
        "--docker-executable", "/x/docker", "--volume-disposition-file", "/x/disposition",
        "--volume-deletion-file", "/x/deletion", "--lineage-manifest-file", "/x/lineage",
        "--retention-decision-file", "/x/retention", "--legal-hold-decision-file", "/x/hold",
        "--recovery-decision-file", "/x/recovery", "--project-name", PROJECT,
        "--evidence-directory", "/x/evidence",
    ]
    assert deletion.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert deletion.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_entry_point_is_installed() -> None:
    project = Path(__file__).parents[1] / "pyproject.toml"
    assert (
        'liquent-disposable-postgres-volume-delete = '
        '"liquent_platform.operators.disposable_postgres_volume_deletion:main"'
    ) in project.read_text()
