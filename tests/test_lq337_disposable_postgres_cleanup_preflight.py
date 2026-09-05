from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_cleanup_preflight as preflight
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from tests.test_lq330_disposable_postgres_composition import _inspection, _model
from tests.test_lq331_disposable_postgres_reconciliation import (
    NETWORKS, NOW, PROJECT, VOLUME, _network, _volume,
)
from tests.test_lq335_disposable_postgres_disposition import _inputs as _disposition_inputs


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


def _processes(state: str) -> Processes:
    if state == "absent":
        values = [_observation(_model()), *[_observation() for _ in range(4)]]
    elif state == "conflict":
        values = [
            _observation(_model()),
            _observation((f"{PROJECT}-postgres-1\n").encode()),
            _observation(), _observation(), _observation(),
        ]
    else:
        names = [f"{PROJECT}-postgres-1", *NETWORKS, VOLUME]
        values = [
            _observation(_model()),
            *[_observation((name + "\n").encode()) for name in names],
            _observation(_inspection()), _observation(_network(NETWORKS[0])),
            _observation(_network(NETWORKS[1])), _observation(_volume()),
        ]
    return Processes(values)


def _inputs(tmp_path: Path, *, scope: str, state: str = "isolated"):
    disposition_inputs, _ = _disposition_inputs(tmp_path, "isolated")
    auth = json.loads(disposition_inputs["authorization_file"].read_text())
    recon = json.loads(disposition_inputs["reconciliation_file"].read_text())
    claim = json.loads(disposition_inputs["claim_reconciliation_file"].read_text())
    decision = json.loads(disposition_inputs["disposition_file"].read_text())
    cleanup = _private(tmp_path / "cleanup.json", {
        "schema_version": 1, "cleanup_id": "cleanup-337",
        "run_id": auth["run_id"], "phase": "disposable_postgres",
        "source_commit": auth["source_commit"], "image_ref": auth["image_ref"],
        "compose_sha256": auth["compose_sha256"],
        "reconciliation_id": recon["reconciliation_id"],
        "claim_reconciliation_id": claim["claim_reconciliation_id"],
        "disposition_id": decision["disposition_id"],
        "staging_evidence_sha256": decision["staging_evidence_sha256"],
        "reconciliation_evidence_sha256": decision["reconciliation_evidence_sha256"],
        "claim_reconciliation_evidence_sha256": decision["claim_reconciliation_evidence_sha256"],
        "disposition_authorization_sha256": hashlib.sha256(
            disposition_inputs["disposition_file"].read_bytes()
        ).hexdigest(),
        "operation": "remove_disposable_postgres_resources", "scope": scope,
        "executor_id": "cleanup-executor", "authorizer_id": "cleanup-authorizer",
        "valid_from": "2026-08-20T13:30:00Z",
        "valid_until": "2026-08-20T14:30:00Z",
    })
    return {
        "docker_executable": tmp_path / "docker",
        "authorization_file": disposition_inputs["authorization_file"],
        "reconciliation_file": disposition_inputs["reconciliation_file"],
        "claim_reconciliation_file": disposition_inputs["claim_reconciliation_file"],
        "disposition_file": disposition_inputs["disposition_file"],
        "cleanup_file": cleanup,
        "staging_evidence_file": disposition_inputs["staging_evidence_file"],
        "compose_file": tmp_path / "compose.yaml",
        "runtime_environment_file": tmp_path / "runtime.env",
        "image_environment_file": tmp_path / "images.env",
        "project_name": PROJECT,
        "evidence_directory": disposition_inputs["evidence_directory"],
        "processes": _processes(state), "clock": lambda: NOW,
    }


def test_runtime_only_exact_isolated_resources_are_ready(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, scope="runtime_only")
    result = preflight.preflight_disposable_postgres_cleanup(**inputs)
    assert json.loads(result)["outcome"] == "ready"
    assert not any(set(call[0]) & {"up", "down", "rm", "remove", "prune"} for call in inputs["processes"].calls)


def test_current_absence_is_already_absent(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, scope="runtime_only", state="absent")
    result = preflight.preflight_disposable_postgres_cleanup(**inputs)
    assert json.loads(result)["outcome"] == "already_absent"


def test_current_partial_or_foreign_state_is_rejected(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, scope="runtime_only", state="conflict")
    result = preflight.preflight_disposable_postgres_cleanup(**inputs)
    assert json.loads(result)["outcome"] == "rejected"


def test_volume_scope_is_rejected_without_authoritative_clearance(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, scope="runtime_and_data_volume")
    result = preflight.preflight_disposable_postgres_cleanup(**inputs)
    assert json.loads(result)["outcome"] == "rejected"


def test_cleanup_hash_mismatch_or_open_claim_is_unavailable(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, scope="runtime_only")
    value = json.loads(inputs["cleanup_file"].read_text())
    value["disposition_authorization_sha256"] = "0" * 64
    _private(inputs["cleanup_file"], value)
    with pytest.raises(preflight.DisposablePostgresCleanupPreflightUnavailable):
        preflight.preflight_disposable_postgres_cleanup(**inputs)


def test_open_cleanup_claim_is_unavailable_before_docker(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, scope="runtime_only")
    stem = hashlib.sha256(b"cleanup-337").hexdigest()
    claim = inputs["evidence_directory"] / f".postgres-cleanup-{stem}.claim"
    claim.write_bytes(b"disposable-postgres-cleanup\n")
    os.chmod(claim, 0o600)
    inputs["processes"] = Processes([])
    with pytest.raises(preflight.DisposablePostgresCleanupPreflightUnavailable):
        preflight.preflight_disposable_postgres_cleanup(**inputs)
    assert inputs["processes"].calls == []


def test_cli_emits_only_canonical_preflight_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_cleanup_preflight",'
        b'"outcome":"ready","schema_version":1}\n'
    )
    monkeypatch.setattr(
        preflight, "preflight_disposable_postgres_cleanup", lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--authorization-file", "/x/auth",
        "--reconciliation-file", "/x/recon",
        "--claim-reconciliation-file", "/x/claim-recon",
        "--disposition-file", "/x/disposition", "--cleanup-file", "/x/cleanup",
        "--staging-evidence-file", "/x/staging", "--compose-file", "/x/compose",
        "--runtime-env-file", "/x/runtime", "--image-env-file", "/x/images",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert preflight.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert preflight.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
