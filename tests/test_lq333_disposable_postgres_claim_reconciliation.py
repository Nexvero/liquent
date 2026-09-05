from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_claim_reconcile as claim_reconcile
import liquent_platform.operators.disposable_postgres_reconcile as reconcile
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from tests.test_lq330_disposable_postgres_composition import _model
from tests.test_lq331_disposable_postgres_reconciliation import NOW, PROJECT, _inputs


class Processes:
    def __init__(self, values):
        self.values, self.calls = list(values), []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.values.pop(0)


def _observation(stdout: bytes = b"", *, timed_out: bool = False):
    return ProcessObservation(0, stdout, b"", timed_out, False, False)


def _private(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.chmod(path, 0o600)
    return path


def _setup(tmp_path: Path, processes: Processes, *, prior_claim: bool = True):
    values = _inputs(tmp_path, processes)
    previous = json.loads(values["reconciliation_file"].read_text())
    current = _private(tmp_path / "claim-reconciliation.json", {
        "schema_version": 1, "claim_reconciliation_id": "claim-reconcile-333",
        "reconciliation_id": previous["reconciliation_id"],
        "run_id": previous["run_id"], "phase": "disposable_postgres",
        "source_commit": previous["source_commit"], "image_ref": previous["image_ref"],
        "compose_sha256": previous["compose_sha256"],
        "reconciliation_executor_id": previous["executor_id"],
        "reconciliation_authorizer_id": previous["authorizer_id"],
        "executor_id": "claim-executor-333", "authorizer_id": "claim-authorizer-333",
        "valid_from": "2026-08-20T13:30:00Z",
        "valid_until": "2026-08-20T14:30:00Z",
    })
    evidence = tmp_path / "claim-evidence"
    evidence.mkdir(mode=0o700)
    previous_stem = hashlib.sha256(previous["reconciliation_id"].encode()).hexdigest()
    previous_claim = evidence / f".postgres-reconciliation-{previous_stem}.claim"
    if prior_claim:
        previous_claim.write_bytes(b"disposable-postgres-reconciliation\n")
        os.chmod(previous_claim, 0o600)
    values.update({
        "claim_reconciliation_file": current, "evidence_directory": evidence,
    })
    return values, evidence, previous_claim


def _reconciliation_paths(evidence: Path) -> tuple[Path, Path]:
    stem = hashlib.sha256(b"claim-reconcile-333").hexdigest()
    return (
        evidence / f"postgres-claim-reconciliation-{stem}.json",
        evidence / f".postgres-claim-reconciliation-{stem}.claim",
    )


def test_absence_is_finalized_evidence_first_and_claims_are_removed(tmp_path: Path) -> None:
    processes = Processes([_observation(_model()), *[_observation() for _ in range(4)]])
    values, evidence, previous_claim = _setup(tmp_path, processes)
    result = claim_reconcile.reconcile_disposable_postgres_claim(**values)
    final, own_claim = _reconciliation_paths(evidence)
    assert json.loads(result)["outcome"] == "absence_finalized"
    assert final.exists() and not own_claim.exists() and not previous_claim.exists()
    records = [json.loads(path.read_text()) for path in evidence.glob("*.json")]
    assert {record["outcome"] for record in records} == {
        "absent", "absence_finalized",
    }


def test_existing_previous_evidence_is_confirmed_without_docker(tmp_path: Path) -> None:
    seed_processes = Processes([_observation(_model()), *[_observation() for _ in range(4)]])
    values, evidence, previous_claim = _setup(tmp_path, seed_processes, prior_claim=False)
    reconcile.reconcile_disposable_postgres_with_evidence(
        docker_executable=values["docker_executable"],
        authorization_file=values["authorization_file"],
        reconciliation_file=values["reconciliation_file"],
        compose_file=values["compose_file"],
        runtime_environment_file=values["runtime_environment_file"],
        image_environment_file=values["image_environment_file"],
        project_name=values["project_name"], evidence_directory=evidence,
        processes=seed_processes, clock=values["clock"],
    )
    previous_claim.write_bytes(b"disposable-postgres-reconciliation\n")
    os.chmod(previous_claim, 0o600)
    processes = Processes([])
    values["processes"] = processes
    result = claim_reconcile.reconcile_disposable_postgres_claim(**values)
    assert json.loads(result)["outcome"] == "evidence_confirmed"
    assert processes.calls == [] and not previous_claim.exists()


def test_no_previous_claim_or_evidence_is_not_found_without_docker(tmp_path: Path) -> None:
    processes = Processes([])
    values, _, _ = _setup(tmp_path, processes, prior_claim=False)
    result = claim_reconcile.reconcile_disposable_postgres_claim(**values)
    assert json.loads(result)["outcome"] == "not_found"
    assert processes.calls == []


def test_unknown_inspection_retains_both_claims_and_no_evidence(tmp_path: Path) -> None:
    processes = Processes([_observation(_model()), _observation(timed_out=True)])
    values, evidence, previous_claim = _setup(tmp_path, processes)
    with pytest.raises(claim_reconcile.DisposablePostgresClaimReconcileUnavailable):
        claim_reconcile.reconcile_disposable_postgres_claim(**values)
    final, own_claim = _reconciliation_paths(evidence)
    assert previous_claim.exists() and own_claim.exists() and not final.exists()
    retry = Processes([])
    values["processes"] = retry
    with pytest.raises(claim_reconcile.DisposablePostgresClaimReconcileUnavailable):
        claim_reconcile.reconcile_disposable_postgres_claim(**values)
    assert retry.calls == []


def test_exact_final_retry_returns_claim_evidence_without_docker(tmp_path: Path) -> None:
    first = Processes([_observation(_model()), *[_observation() for _ in range(4)]])
    values, _, _ = _setup(tmp_path, first)
    expected = claim_reconcile.reconcile_disposable_postgres_claim(**values)
    second = Processes([])
    values["processes"] = second
    assert claim_reconcile.reconcile_disposable_postgres_claim(**values) == expected
    assert second.calls == []


def test_mismatched_current_authorization_stops_before_docker(tmp_path: Path) -> None:
    processes = Processes([])
    values, _, _ = _setup(tmp_path, processes)
    current = json.loads(values["claim_reconciliation_file"].read_text())
    current["reconciliation_id"] = "other-reconciliation"
    _private(values["claim_reconciliation_file"], current)
    with pytest.raises(claim_reconcile.DisposablePostgresClaimReconcileUnavailable):
        claim_reconcile.reconcile_disposable_postgres_claim(**values)
    assert processes.calls == []


def test_cli_emits_only_canonical_handoff_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_claim_reconciliation",'
        b'"outcome":"not_found","schema_version":1}\n'
    )
    monkeypatch.setattr(
        claim_reconcile, "reconcile_disposable_postgres_claim", lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--authorization-file", "/x/auth",
        "--reconciliation-file", "/x/reconciliation",
        "--claim-reconciliation-file", "/x/claim-reconciliation",
        "--compose-file", "/x/compose", "--runtime-env-file", "/x/runtime",
        "--image-env-file", "/x/images", "--project-name", PROJECT,
        "--evidence-directory", "/x/evidence",
    ]
    assert claim_reconcile.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert claim_reconcile.main(["--project-name", PROJECT]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
