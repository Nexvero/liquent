from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_claim_reconcile as claim_reconcile
import liquent_platform.operators.disposable_postgres_disposition as disposition
from liquent_platform.operators.research_worker_staging_executor import PHASES
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from tests.test_lq330_disposable_postgres_composition import _inspection, _model
from tests.test_lq331_disposable_postgres_reconciliation import (
    NETWORKS, NOW, PROJECT, VOLUME, _network, _volume,
)
from tests.test_lq333_disposable_postgres_claim_reconciliation import _setup


class Processes:
    def __init__(self, values):
        self.values, self.calls = list(values), []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.values.pop(0)


def _observation(stdout: bytes = b""):
    return ProcessObservation(0, stdout, b"", False, False, False)


def _private(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.chmod(path, 0o600)
    return path


def _chain(tmp_path: Path, outcome: str):
    if outcome == "absent":
        observations = [_observation(_model()), *[_observation() for _ in range(4)]]
    elif outcome == "conflict":
        observations = [
            _observation(_model()), _observation((f"{PROJECT}-postgres-1\n").encode()),
            _observation(), _observation(), _observation(),
        ]
    else:
        names = [f"{PROJECT}-postgres-1", *NETWORKS, VOLUME]
        observations = [
            _observation(_model()),
            *[_observation((name + "\n").encode()) for name in names],
            _observation(_inspection()), _observation(_network(NETWORKS[0])),
            _observation(_network(NETWORKS[1])), _observation(_volume()),
        ]
    processes = Processes(observations)
    values, evidence, _ = _setup(tmp_path, processes)
    claim_reconcile.reconcile_disposable_postgres_claim(**values)
    return values, evidence


def _staging(tmp_path: Path, authorization: Path, *, later_effect: bool = False) -> Path:
    auth = json.loads(authorization.read_text())
    checks = {}
    stop = PHASES.index("disposable_postgres")
    for index, phase in enumerate(PHASES):
        if index < stop:
            checks[phase] = {
                "status": "passed", "evidence_ref": f"evidence:{phase}",
                "evidence_sha256": f"{index + 1:064x}",
            }
        else:
            checks[phase] = {
                "status": "unavailable", "evidence_ref": None,
                "evidence_sha256": None,
            }
    if later_effect:
        checks["rollback"] = {
            "status": "passed", "evidence_ref": "evidence:rollback",
            "evidence_sha256": "f" * 64,
        }
    return _private(tmp_path / "staging-evidence.json", {
        "schema_version": 1, "run_id": auth["run_id"], "environment": "staging",
        "source_commit": auth["source_commit"], "image_ref": auth["image_ref"],
        "compose_sha256": auth["compose_sha256"],
        "migration_head": auth["migration_head"],
        "observed_at": "2026-08-20T14:00:00Z",
        "review_by": "2026-08-20T15:00:00Z",
        "prepared_by": auth["executor_id"], "reviewed_by": auth["authorizer_id"],
        "checks": checks,
    })


def _inputs(tmp_path: Path, outcome: str, *, later_effect: bool = False):
    values, evidence = _chain(tmp_path, outcome)
    previous = json.loads(values["reconciliation_file"].read_text())
    claim = json.loads(values["claim_reconciliation_file"].read_text())
    previous_stem = hashlib.sha256(previous["reconciliation_id"].encode()).hexdigest()
    claim_stem = hashlib.sha256(claim["claim_reconciliation_id"].encode()).hexdigest()
    previous_evidence = evidence / f"postgres-reconciliation-{previous_stem}.json"
    claim_evidence = evidence / f"postgres-claim-reconciliation-{claim_stem}.json"
    staging = _staging(tmp_path, values["authorization_file"], later_effect=later_effect)
    auth = json.loads(values["authorization_file"].read_text())
    disposition_file = _private(tmp_path / "disposition.json", {
        "schema_version": 1, "disposition_id": "disposition-335",
        "run_id": auth["run_id"], "phase": "disposable_postgres",
        "source_commit": auth["source_commit"], "image_ref": auth["image_ref"],
        "compose_sha256": auth["compose_sha256"],
        "reconciliation_id": previous["reconciliation_id"],
        "claim_reconciliation_id": claim["claim_reconciliation_id"],
        "staging_evidence_sha256": hashlib.sha256(staging.read_bytes()).hexdigest(),
        "reconciliation_evidence_sha256": hashlib.sha256(previous_evidence.read_bytes()).hexdigest(),
        "claim_reconciliation_evidence_sha256": hashlib.sha256(claim_evidence.read_bytes()).hexdigest(),
        "executor_id": "disposition-executor", "authorizer_id": "disposition-authorizer",
        "valid_from": "2026-08-20T13:30:00Z",
        "valid_until": "2026-08-20T14:30:00Z",
    })
    return {
        "authorization_file": values["authorization_file"],
        "reconciliation_file": values["reconciliation_file"],
        "claim_reconciliation_file": values["claim_reconciliation_file"],
        "disposition_file": disposition_file, "staging_evidence_file": staging,
        "evidence_directory": evidence, "clock": lambda: NOW,
    }, previous_evidence


@pytest.mark.parametrize("state,expected", [
    ("absent", "new_run_eligible"),
    ("isolated", "cleanup_review_eligible"),
    ("conflict", "investigation_required"),
])
def test_finalized_state_maps_to_closed_disposition(
    tmp_path: Path, state: str, expected: str,
) -> None:
    inputs, _ = _inputs(tmp_path, state)
    result = disposition.resolve_disposable_postgres_disposition(**inputs)
    assert json.loads(result)["outcome"] == expected


def test_later_phase_effect_forces_retain(tmp_path: Path) -> None:
    inputs, _ = _inputs(tmp_path, "isolated", later_effect=True)
    result = disposition.resolve_disposable_postgres_disposition(**inputs)
    assert json.loads(result)["outcome"] == "retain"


def test_hash_mismatch_or_open_claim_is_unavailable(tmp_path: Path) -> None:
    inputs, previous_evidence = _inputs(tmp_path, "absent")
    previous_evidence.write_bytes(previous_evidence.read_bytes() + b" ")
    with pytest.raises(disposition.DisposablePostgresDispositionUnavailable):
        disposition.resolve_disposable_postgres_disposition(**inputs)


def test_open_reconciliation_claim_is_unavailable(tmp_path: Path) -> None:
    inputs, _ = _inputs(tmp_path, "absent")
    previous = json.loads(inputs["reconciliation_file"].read_text())
    stem = hashlib.sha256(previous["reconciliation_id"].encode()).hexdigest()
    claim = inputs["evidence_directory"] / f".postgres-reconciliation-{stem}.claim"
    claim.write_bytes(b"disposable-postgres-reconciliation\n")
    os.chmod(claim, 0o600)
    with pytest.raises(disposition.DisposablePostgresDispositionUnavailable):
        disposition.resolve_disposable_postgres_disposition(**inputs)


def test_cli_emits_only_canonical_disposition_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_disposition",'
        b'"outcome":"retain","schema_version":1}\n'
    )
    monkeypatch.setattr(
        disposition, "resolve_disposable_postgres_disposition", lambda **_: expected,
    )
    arguments = [
        "--authorization-file", "/x/auth", "--reconciliation-file", "/x/recon",
        "--claim-reconciliation-file", "/x/claim-recon",
        "--disposition-file", "/x/disposition",
        "--staging-evidence-file", "/x/staging",
        "--evidence-directory", "/x/evidence",
    ]
    assert disposition.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert disposition.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
