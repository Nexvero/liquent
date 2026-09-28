from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_reconcile as reconcile
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from tests.test_lq330_disposable_postgres_composition import _model
from tests.test_lq331_disposable_postgres_reconciliation import (
    NOW, PROJECT, _inputs,
)


class Processes:
    def __init__(self, values):
        self.values, self.calls = list(values), []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.values.pop(0)


def _observation(stdout: bytes = b"", *, timed_out: bool = False):
    return ProcessObservation(0, stdout, b"", timed_out, False, False)


def _evidence(tmp_path: Path) -> Path:
    path = tmp_path / "postgres-reconciliation-evidence"
    path.mkdir(mode=0o700)
    return path


def _run(tmp_path: Path, processes: Processes, evidence: Path | None = None):
    values = _inputs(tmp_path, processes)
    return reconcile.reconcile_disposable_postgres_with_evidence(
        **values, evidence_directory=evidence or _evidence(tmp_path),
    )


def _paths(evidence: Path) -> tuple[Path, Path]:
    stem = hashlib.sha256(b"reconcile-331").hexdigest()
    return (
        evidence / f"postgres-reconciliation-{stem}.json",
        evidence / f".postgres-reconciliation-{stem}.claim",
    )


def test_result_is_persisted_privately_before_claim_removal(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    processes = Processes([_observation(_model()), *[_observation() for _ in range(4)]])
    result = _run(tmp_path, processes, evidence)
    final, claim = _paths(evidence)
    assert json.loads(result)["outcome"] == "absent"
    assert final.exists() and not claim.exists()
    assert final.stat().st_mode & 0o777 == 0o600
    record = json.loads(final.read_text())
    assert record["reconciliation_id"] == "reconcile-331"
    assert record["outcome"] == "absent" and record["phase"] == "disposable_postgres"


def test_exact_retry_returns_evidence_without_docker(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    first = Processes([_observation(_model()), *[_observation() for _ in range(4)]])
    expected = _run(tmp_path, first, evidence)
    second = Processes([])
    actual = _run(tmp_path, second, evidence)
    assert actual == expected and second.calls == []


def test_evidence_first_retry_removes_only_exact_leftover_claim(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    expected = _run(
        tmp_path,
        Processes([_observation(_model()), *[_observation() for _ in range(4)]]),
        evidence,
    )
    _, claim = _paths(evidence)
    claim.write_bytes(b"disposable-postgres-reconciliation\n")
    os.chmod(claim, 0o600)
    processes = Processes([])
    assert _run(tmp_path, processes, evidence) == expected
    assert not claim.exists() and processes.calls == []


def test_unknown_observation_leaves_claim_without_evidence(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    processes = Processes([_observation(_model()), _observation(timed_out=True)])
    with pytest.raises(reconcile.DisposablePostgresReconcileUnavailable):
        _run(tmp_path, processes, evidence)
    final, claim = _paths(evidence)
    assert claim.exists() and not final.exists()
    retry = Processes([])
    with pytest.raises(reconcile.DisposablePostgresReconcileUnavailable):
        _run(tmp_path, retry, evidence)
    assert retry.calls == []


def test_existing_evidence_with_changed_binding_is_unavailable(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    _run(
        tmp_path,
        Processes([_observation(_model()), *[_observation() for _ in range(4)]]),
        evidence,
    )
    reconciliation_file = tmp_path / "reconciliation.json"
    value = json.loads(reconciliation_file.read_text())
    value["executor_id"] = "different-executor"
    reconciliation_file.write_text(json.dumps(value))
    os.chmod(reconciliation_file, 0o600)
    processes = Processes([])
    with pytest.raises(reconcile.DisposablePostgresReconcileUnavailable):
        reconcile.reconcile_disposable_postgres_with_evidence(
            **_inputs_existing(tmp_path, processes), evidence_directory=evidence,
        )
    assert processes.calls == []


def _inputs_existing(tmp_path: Path, processes: Processes) -> dict:
    return {
        "docker_executable": tmp_path / "docker",
        "authorization_file": tmp_path / "authorization.json",
        "reconciliation_file": tmp_path / "reconciliation.json",
        "compose_file": tmp_path / "compose.yaml",
        "runtime_environment_file": tmp_path / "runtime.env",
        "image_environment_file": tmp_path / "images.env",
        "project_name": PROJECT, "processes": processes, "clock": lambda: NOW,
    }


def test_broad_evidence_directory_is_unavailable_before_docker(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    os.chmod(evidence, 0o755)
    processes = Processes([])
    with pytest.raises(reconcile.DisposablePostgresReconcileUnavailable):
        _run(tmp_path, processes, evidence)
    assert processes.calls == []
