from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_cleanup_finalize as finalize
from tests.test_lq331_disposable_postgres_reconciliation import NOW, PROJECT
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import (
    Processes, _private, _setup as _reconciliation_setup,
)


def _setup(tmp_path: Path, *, claim: bool = True):
    values, _, claim_path, _ = _reconciliation_setup(tmp_path, claim=claim)
    previous = json.loads(values["cleanup_reconciliation_file"].read_text())
    current = _private(tmp_path / "cleanup-finalization.json", {
        "schema_version": 1, "cleanup_finalization_id": "cleanup-finalization-343",
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
        "operation": "finalize_disposable_postgres_runtime_cleanup", "scope": "runtime_only",
        "executor_id": "cleanup-finalize-executor",
        "authorizer_id": "cleanup-finalize-authorizer",
        "valid_from": "2026-08-20T13:30:00Z", "valid_until": "2026-08-20T14:30:00Z",
    })
    values["cleanup_finalization_file"] = current
    values["clock"] = lambda: NOW
    return values, claim_path


def _observed(monkeypatch, outcome: str, calls: list | None = None) -> None:
    def inspect(**_):
        if calls is not None:
            calls.append(outcome)
        return (json.dumps({
            "operation": "disposable_postgres_runtime_cleanup_reconciliation",
            "outcome": outcome, "schema_version": 1,
        }, sort_keys=True, separators=(",", ":")) + "\n").encode()
    monkeypatch.setattr(finalize, "reconcile_disposable_postgres_cleanup", inspect)


@pytest.mark.parametrize(("state", "outcome"), [
    ("runtime_intact", "no_effect_finalized"),
    ("runtime_removed_evidence_missing", "runtime_removal_finalized"),
    ("final_evidence_present", "cleanup_evidence_confirmed"),
])
def test_finalizable_states_write_evidence_before_claim_release(
    tmp_path: Path, monkeypatch, state: str, outcome: str,
) -> None:
    values, claim = _setup(tmp_path)
    _observed(monkeypatch, state)
    result = finalize.finalize_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"] == outcome
    stem = hashlib.sha256(b"cleanup-finalization-343").hexdigest()
    evidence = values["evidence_directory"] / f"postgres-cleanup-finalization-{stem}.json"
    record = json.loads(evidence.read_text())
    assert record["observed_state"] == state and record["outcome"] == outcome
    assert not claim.exists()
    assert values["processes"].calls == []


@pytest.mark.parametrize("state", [
    "container_stopped", "container_removed", "application_network_removed",
])
def test_partial_states_require_continuation_without_write(
    tmp_path: Path, monkeypatch, state: str,
) -> None:
    values, claim = _setup(tmp_path)
    _observed(monkeypatch, state)
    result = finalize.finalize_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"] == "continuation_required"
    assert claim.exists()
    assert list(values["evidence_directory"].glob("postgres-cleanup-finalization-*.json")) == []


@pytest.mark.parametrize(("state", "outcome", "claim"), [
    ("conflict", "investigation_required", True),
    ("not_found", "not_found", False),
])
def test_conflict_and_absence_remain_neutral(
    tmp_path: Path, monkeypatch, state: str, outcome: str, claim: bool,
) -> None:
    values, claim_path = _setup(tmp_path, claim=claim)
    _observed(monkeypatch, state)
    result = finalize.finalize_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"] == outcome
    assert claim_path.exists() is claim
    assert list(values["evidence_directory"].glob("postgres-cleanup-finalization-*.json")) == []


def test_unknown_claim_release_retries_from_evidence_without_inspector(
    tmp_path: Path, monkeypatch,
) -> None:
    values, claim = _setup(tmp_path)
    calls = []
    _observed(monkeypatch, "runtime_intact", calls)
    original_release = finalize._release_claim
    monkeypatch.setattr(
        finalize, "_release_claim",
        lambda *_: (_ for _ in ()).throw(finalize.DisposablePostgresCleanupFinalizeUnavailable()),
    )
    with pytest.raises(finalize.DisposablePostgresCleanupFinalizeUnavailable):
        finalize.finalize_disposable_postgres_cleanup(**values)
    assert claim.exists() and calls == ["runtime_intact"]

    monkeypatch.setattr(finalize, "_release_claim", original_release)
    monkeypatch.setattr(
        finalize, "reconcile_disposable_postgres_cleanup",
        lambda **_: pytest.fail("evidence retry must not inspect"),
    )
    result = finalize.finalize_disposable_postgres_cleanup(**values)
    assert json.loads(result)["outcome"] == "no_effect_finalized"
    assert not claim.exists()


def test_mismatched_reconciliation_hash_stops_before_inspector(tmp_path: Path, monkeypatch) -> None:
    values, claim = _setup(tmp_path)
    current = json.loads(values["cleanup_finalization_file"].read_text())
    current["cleanup_reconciliation_authorization_sha256"] = "0" * 64
    _private(values["cleanup_finalization_file"], current)
    monkeypatch.setattr(
        finalize, "reconcile_disposable_postgres_cleanup",
        lambda **_: pytest.fail("inspector must not run"),
    )
    with pytest.raises(finalize.DisposablePostgresCleanupFinalizeUnavailable):
        finalize.finalize_disposable_postgres_cleanup(**values)
    assert claim.exists()


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_runtime_cleanup_finalization",'
        b'"outcome":"no_effect_finalized","schema_version":1}\n'
    )
    monkeypatch.setattr(finalize, "finalize_disposable_postgres_cleanup", lambda **_: expected)
    arguments = [
        "--docker-executable", "/x/docker", "--authorization-file", "/x/auth",
        "--reconciliation-file", "/x/recon", "--claim-reconciliation-file", "/x/claim",
        "--disposition-file", "/x/disposition", "--cleanup-file", "/x/cleanup",
        "--cleanup-reconciliation-file", "/x/cleanup-recon",
        "--cleanup-finalization-file", "/x/finalization",
        "--staging-evidence-file", "/x/staging", "--compose-file", "/x/compose",
        "--runtime-env-file", "/x/runtime", "--image-env-file", "/x/images",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert finalize.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert finalize.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
