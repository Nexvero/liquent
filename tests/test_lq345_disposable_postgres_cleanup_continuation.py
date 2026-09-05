from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_cleanup_continue as continuation
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from tests.test_lq331_disposable_postgres_reconciliation import (
    CONTAINER, NETWORKS, NOW, PROJECT, _volume,
)
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import (
    Processes, _private, _setup as _reconciliation_setup,
)


def _observation(stdout: bytes = b"", *, timed_out: bool = False):
    return ProcessObservation(0, stdout, b"", timed_out, False, False)


def _setup(tmp_path: Path, state: str):
    values, _, cleanup_claim, _ = _reconciliation_setup(tmp_path, state)
    previous = json.loads(values["cleanup_reconciliation_file"].read_text())
    current = _private(tmp_path / "cleanup-continuation.json", {
        "schema_version": 1, "cleanup_continuation_id": "cleanup-continuation-345",
        "cleanup_reconciliation_id": previous["cleanup_reconciliation_id"],
        "cleanup_id": previous["cleanup_id"], "run_id": previous["run_id"],
        "phase": "disposable_postgres", "source_commit": previous["source_commit"],
        "image_ref": previous["image_ref"], "compose_sha256": previous["compose_sha256"],
        "reconciliation_id": previous["reconciliation_id"],
        "claim_reconciliation_id": previous["claim_reconciliation_id"],
        "disposition_id": previous["disposition_id"],
        "staging_evidence_sha256": previous["staging_evidence_sha256"],
        "reconciliation_evidence_sha256": previous["reconciliation_evidence_sha256"],
        "claim_reconciliation_evidence_sha256": previous["claim_reconciliation_evidence_sha256"],
        "disposition_authorization_sha256": previous["disposition_authorization_sha256"],
        "cleanup_authorization_sha256": previous["cleanup_authorization_sha256"],
        "cleanup_reconciliation_authorization_sha256": hashlib.sha256(
            values["cleanup_reconciliation_file"].read_bytes()
        ).hexdigest(),
        "operation": "continue_disposable_postgres_runtime_cleanup", "scope": "runtime_only",
        "resume_from": state, "executor_id": "continuation-executor",
        "authorizer_id": "continuation-authorizer",
        "valid_from": "2026-08-20T13:30:00Z", "valid_until": "2026-08-20T14:30:00Z",
    })
    values.update({"cleanup_continuation_file": current, "clock": lambda: NOW})
    return values, cleanup_claim


def _observed(monkeypatch, outcome: str, calls=None):
    def inspect(**_):
        if calls is not None:
            calls.append(outcome)
        return (json.dumps({
            "operation": "disposable_postgres_runtime_cleanup_reconciliation",
            "outcome": outcome, "schema_version": 1,
        }, sort_keys=True, separators=(",", ":")) + "\n").encode()
    monkeypatch.setattr(continuation, "reconcile_disposable_postgres_cleanup", inspect)


def _processes(state: str) -> Processes:
    count = {"container_stopped": 3, "container_removed": 2, "application_network_removed": 1}[state]
    return Processes([*[_observation() for _ in range(count * 2)], _observation(_volume())])


@pytest.mark.parametrize("state", [
    "container_stopped", "container_removed", "application_network_removed",
])
def test_each_state_executes_only_its_minimal_remaining_budget(tmp_path: Path, monkeypatch, state: str) -> None:
    values, cleanup_claim = _setup(tmp_path, state)
    _observed(monkeypatch, state)
    values["processes"] = _processes(state)
    result = continuation.continue_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"] == "runtime_removed_pending_finalization"
    commands = [call[0][1:3] for call in values["processes"].calls]
    expected = []
    if state == "container_stopped":
        expected += [("container", "rm"), ("container", "ls")]
    if state in {"container_stopped", "container_removed"}:
        expected += [("network", "rm"), ("network", "ls")]
    expected += [("network", "rm"), ("network", "ls"), ("volume", "inspect")]
    assert commands == expected
    assert not any(set(call[0]) & {"stop", "kill", "down", "prune", "--volumes", "--force"} for call in values["processes"].calls)
    assert cleanup_claim.exists()
    assert not list(values["evidence_directory"].glob(".postgres-cleanup-continuation-*.claim"))


def test_state_mismatch_is_rejected_before_claim_or_docker(tmp_path: Path, monkeypatch) -> None:
    values, cleanup_claim = _setup(tmp_path, "container_stopped")
    _observed(monkeypatch, "container_removed")
    values["processes"] = Processes([])
    result = continuation.continue_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"] == "rejected"
    assert cleanup_claim.exists() and values["processes"].calls == []
    assert not list(values["evidence_directory"].glob(".postgres-cleanup-continuation-*.claim"))


def test_unknown_first_remove_retains_both_claims_and_blocks_retry(tmp_path: Path, monkeypatch) -> None:
    values, cleanup_claim = _setup(tmp_path, "application_network_removed")
    _observed(monkeypatch, "application_network_removed")
    values["processes"] = Processes([_observation(timed_out=True)])
    with pytest.raises(continuation.DisposablePostgresCleanupContinueUnavailable):
        continuation.continue_disposable_postgres_cleanup(**values)
    claims = list(values["evidence_directory"].glob(".postgres-cleanup-continuation-*.claim"))
    assert cleanup_claim.exists() and len(claims) == 1
    values["processes"] = Processes([])
    with pytest.raises(continuation.DisposablePostgresCleanupContinueUnavailable):
        continuation.continue_disposable_postgres_cleanup(**values)
    assert values["processes"].calls == []


def test_exact_evidence_retry_releases_only_continuation_claim_without_inspector(tmp_path: Path, monkeypatch) -> None:
    values, cleanup_claim = _setup(tmp_path, "application_network_removed")
    calls = []
    _observed(monkeypatch, "application_network_removed", calls)
    values["processes"] = _processes("application_network_removed")
    expected = continuation.continue_disposable_postgres_cleanup(**values)
    assert calls == ["application_network_removed"]
    monkeypatch.setattr(
        continuation, "reconcile_disposable_postgres_cleanup",
        lambda **_: pytest.fail("evidence retry must not inspect"),
    )
    values["processes"] = Processes([])
    assert continuation.continue_disposable_postgres_cleanup(**values) == expected
    assert cleanup_claim.exists() and values["processes"].calls == []


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_runtime_cleanup_continuation",'
        b'"outcome":"rejected","schema_version":1}\n'
    )
    monkeypatch.setattr(continuation, "continue_disposable_postgres_cleanup", lambda **_: expected)
    arguments = [
        "--docker-executable", "/x/docker", "--authorization-file", "/x/auth",
        "--reconciliation-file", "/x/recon", "--claim-reconciliation-file", "/x/claim",
        "--disposition-file", "/x/disposition", "--cleanup-file", "/x/cleanup",
        "--cleanup-reconciliation-file", "/x/cleanup-recon",
        "--cleanup-continuation-file", "/x/continuation",
        "--staging-evidence-file", "/x/staging", "--compose-file", "/x/compose",
        "--runtime-env-file", "/x/runtime", "--image-env-file", "/x/images",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert continuation.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert continuation.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
