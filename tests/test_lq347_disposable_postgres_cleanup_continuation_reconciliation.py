from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_cleanup_continue_reconcile as inspector
from tests.test_lq331_disposable_postgres_reconciliation import NOW, PROJECT
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import Processes, _private
from tests.test_lq345_disposable_postgres_cleanup_continuation import _setup as _continuation_setup


def _setup(tmp_path: Path, resume_from: str):
    values, cleanup_claim = _continuation_setup(tmp_path, resume_from)
    continuation = json.loads(values["cleanup_continuation_file"].read_text())
    binding = inspector._evidence_binding(
        continuation, values["cleanup_continuation_file"], PROJECT,
    )
    stem = hashlib.sha256(continuation["cleanup_continuation_id"].encode()).hexdigest()
    claim = _private(
        values["evidence_directory"] / f".postgres-cleanup-continuation-{stem}.claim",
        dict(binding, started_at="2026-08-20T14:00:00Z"),
    )
    current = {
        "schema_version": 1,
        "continuation_reconciliation_id": "continuation-reconciliation-347",
        **{key: continuation[key] for key in (
            "cleanup_continuation_id", "cleanup_reconciliation_id", "cleanup_id", "run_id",
            "phase", "source_commit", "image_ref", "compose_sha256", "reconciliation_id",
            "claim_reconciliation_id", "disposition_id", "staging_evidence_sha256",
            "reconciliation_evidence_sha256", "claim_reconciliation_evidence_sha256",
            "disposition_authorization_sha256", "cleanup_authorization_sha256",
            "cleanup_reconciliation_authorization_sha256", "scope", "resume_from",
        )},
        "continuation_authorization_sha256": hashlib.sha256(
            values["cleanup_continuation_file"].read_bytes()
        ).hexdigest(),
        "operation": "inspect_disposable_postgres_cleanup_continuation",
        "executor_id": "continuation-inspector", "authorizer_id": "inspection-authorizer",
        "valid_from": "2026-08-20T13:30:00Z", "valid_until": "2026-08-20T14:30:00Z",
    }
    values["continuation_reconciliation_file"] = _private(
        tmp_path / "continuation-reconciliation.json", current,
    )
    values["processes"] = Processes([])
    return values, cleanup_claim, claim, binding, stem


def _observed(monkeypatch, outcome: str, calls: list[str]):
    def reconcile(**_):
        calls.append(outcome)
        return (json.dumps({
            "operation": "disposable_postgres_runtime_cleanup_reconciliation",
            "outcome": outcome, "schema_version": 1,
        }, sort_keys=True, separators=(",", ":")) + "\n").encode()
    monkeypatch.setattr(inspector, "reconcile_disposable_postgres_cleanup", reconcile)


@pytest.mark.parametrize(("resume_from", "observed", "expected"), [
    ("container_stopped", "container_stopped", "continuation_not_started"),
    ("container_stopped", "container_removed", "container_removed"),
    ("container_stopped", "application_network_removed", "application_network_removed"),
    ("container_stopped", "runtime_removed_evidence_missing", "runtime_removed_evidence_missing"),
    ("container_removed", "container_removed", "continuation_not_started"),
    ("container_removed", "application_network_removed", "application_network_removed"),
    ("container_removed", "runtime_removed_evidence_missing", "runtime_removed_evidence_missing"),
    ("container_removed", "container_stopped", "conflict"),
    ("application_network_removed", "application_network_removed", "continuation_not_started"),
    ("application_network_removed", "runtime_removed_evidence_missing", "runtime_removed_evidence_missing"),
    ("application_network_removed", "container_removed", "conflict"),
    ("container_stopped", "runtime_intact", "conflict"),
    ("container_stopped", "final_evidence_present", "conflict"),
])
def test_closed_prefix_matrix_is_read_only(
    tmp_path: Path, monkeypatch, resume_from: str, observed: str, expected: str,
) -> None:
    values, cleanup_claim, claim, _, _ = _setup(tmp_path, resume_from)
    calls: list[str] = []
    _observed(monkeypatch, observed, calls)
    before = {path: path.read_bytes() for path in (cleanup_claim, claim)}
    result = inspector.reconcile_disposable_postgres_cleanup_continuation(**values)
    assert json.loads(result)["outcome"] == expected
    assert calls == [observed]
    assert {path: path.read_bytes() for path in before} == before


def test_exact_evidence_wins_without_inspection_or_claim_release(tmp_path: Path, monkeypatch) -> None:
    values, cleanup_claim, claim, binding, stem = _setup(tmp_path, "container_removed")
    _private(values["evidence_directory"] / f"postgres-cleanup-continuation-{stem}.json", {
        **binding, "outcome": "runtime_removed_pending_finalization",
        "started_at": "2026-08-20T14:00:00Z", "completed_at": "2026-08-20T14:01:00Z",
    })
    monkeypatch.setattr(inspector, "reconcile_disposable_postgres_cleanup", lambda **_: pytest.fail())
    result = inspector.reconcile_disposable_postgres_cleanup_continuation(**values)
    assert json.loads(result)["outcome"] == "continuation_evidence_present"
    assert cleanup_claim.exists() and claim.exists()


def test_absent_continuation_claim_is_neutral_and_does_not_inspect(tmp_path: Path, monkeypatch) -> None:
    values, cleanup_claim, claim, _, _ = _setup(tmp_path, "container_stopped")
    claim.unlink()
    monkeypatch.setattr(inspector, "reconcile_disposable_postgres_cleanup", lambda **_: pytest.fail())
    result = inspector.reconcile_disposable_postgres_cleanup_continuation(**values)
    assert json.loads(result)["outcome"] == "not_found"
    assert cleanup_claim.exists()


def test_missing_original_cleanup_claim_is_conflict_before_inspection(tmp_path: Path, monkeypatch) -> None:
    values, cleanup_claim, claim, _, _ = _setup(tmp_path, "container_stopped")
    cleanup_claim.unlink()
    monkeypatch.setattr(inspector, "reconcile_disposable_postgres_cleanup", lambda **_: pytest.fail())
    result = inspector.reconcile_disposable_postgres_cleanup_continuation(**values)
    assert json.loads(result)["outcome"] == "conflict"
    assert claim.exists()


def test_malformed_continuation_claim_is_detail_free_unavailable(tmp_path: Path, monkeypatch) -> None:
    values, _, claim, _, _ = _setup(tmp_path, "container_stopped")
    claim.chmod(0o644)
    monkeypatch.setattr(inspector, "reconcile_disposable_postgres_cleanup", lambda **_: pytest.fail())
    with pytest.raises(inspector.DisposablePostgresCleanupContinueReconcileUnavailable):
        inspector.reconcile_disposable_postgres_cleanup_continuation(**values)


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_cleanup_continuation_reconciliation",'
        b'"outcome":"not_found","schema_version":1}\n'
    )
    monkeypatch.setattr(
        inspector, "reconcile_disposable_postgres_cleanup_continuation", lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--authorization-file", "/x/auth",
        "--reconciliation-file", "/x/recon", "--claim-reconciliation-file", "/x/claim",
        "--disposition-file", "/x/disposition", "--cleanup-file", "/x/cleanup",
        "--cleanup-reconciliation-file", "/x/cleanup-recon",
        "--cleanup-continuation-file", "/x/continuation",
        "--continuation-reconciliation-file", "/x/continuation-recon",
        "--staging-evidence-file", "/x/staging", "--compose-file", "/x/compose",
        "--runtime-env-file", "/x/runtime", "--image-env-file", "/x/images",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert inspector.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert inspector.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
