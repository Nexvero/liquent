from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_cleanup_continue_finalize as finalize
from tests.test_lq331_disposable_postgres_reconciliation import NOW, PROJECT
from tests.test_lq341_disposable_postgres_cleanup_reconciliation import _private
from tests.test_lq347_disposable_postgres_cleanup_continuation_reconciliation import (
    _setup as _reconciliation_setup,
)


def _setup(tmp_path: Path, resume_from: str = "container_stopped"):
    values, cleanup_claim, continuation_claim, _, _ = _reconciliation_setup(
        tmp_path, resume_from,
    )
    previous = json.loads(values["continuation_reconciliation_file"].read_text())
    current = {
        "schema_version": 1,
        "continuation_finalization_id": "continuation-finalization-349",
        **{key: previous[key] for key in (
            "continuation_reconciliation_id", "cleanup_continuation_id",
            "cleanup_reconciliation_id", "cleanup_id", "run_id", "phase", "source_commit",
            "image_ref", "compose_sha256", "reconciliation_id", "claim_reconciliation_id",
            "disposition_id", "staging_evidence_sha256", "reconciliation_evidence_sha256",
            "claim_reconciliation_evidence_sha256", "disposition_authorization_sha256",
            "cleanup_authorization_sha256", "cleanup_reconciliation_authorization_sha256",
            "continuation_authorization_sha256", "scope", "resume_from",
        )},
        "continuation_reconciliation_authorization_sha256": hashlib.sha256(
            values["continuation_reconciliation_file"].read_bytes()
        ).hexdigest(),
        "operation": "finalize_disposable_postgres_cleanup_continuation",
        "executor_id": "continuation-finalizer", "authorizer_id": "finalization-authorizer",
        "valid_from": "2026-08-20T13:30:00Z", "valid_until": "2026-08-20T14:30:00Z",
    }
    values["continuation_finalization_file"] = _private(
        tmp_path / "continuation-finalization.json", current,
    )
    values["clock"] = lambda: NOW
    return values, cleanup_claim, continuation_claim


def _observed(monkeypatch, state: str, calls: list[str] | None = None) -> None:
    def inspect(**_):
        if calls is not None:
            calls.append(state)
        return (json.dumps({
            "operation": "disposable_postgres_cleanup_continuation_reconciliation",
            "outcome": state, "schema_version": 1,
        }, sort_keys=True, separators=(",", ":")) + "\n").encode()
    monkeypatch.setattr(finalize, "reconcile_disposable_postgres_cleanup_continuation", inspect)


@pytest.mark.parametrize(("state", "outcome"), [
    ("continuation_evidence_present", "continuation_evidence_confirmed"),
    ("continuation_not_started", "continuation_attempt_finalized"),
    ("container_removed", "later_prefix_finalized"),
    ("application_network_removed", "later_prefix_finalized"),
    ("runtime_removed_evidence_missing", "runtime_removal_ready_for_cleanup_finalization"),
])
def test_finalizable_states_write_evidence_then_release_only_continuation_claim(
    tmp_path: Path, monkeypatch, state: str, outcome: str,
) -> None:
    values, cleanup_claim, continuation_claim = _setup(tmp_path)
    _observed(monkeypatch, state)
    result = finalize.finalize_disposable_postgres_cleanup_continuation(**values)
    assert json.loads(result)["outcome"] == outcome
    stem = hashlib.sha256(b"continuation-finalization-349").hexdigest()
    evidence = values["evidence_directory"] / f"postgres-cleanup-continuation-finalization-{stem}.json"
    record = json.loads(evidence.read_text())
    assert record["observed_state"] == state and record["outcome"] == outcome
    assert "started_at" in record and "completed_at" in record
    assert cleanup_claim.exists() and not continuation_claim.exists()
    assert values["processes"].calls == []


@pytest.mark.parametrize(("state", "outcome"), [
    ("not_found", "not_found"),
    ("conflict", "investigation_required"),
])
def test_neutral_states_do_not_write_or_release(
    tmp_path: Path, monkeypatch, state: str, outcome: str,
) -> None:
    values, cleanup_claim, continuation_claim = _setup(tmp_path)
    _observed(monkeypatch, state)
    result = finalize.finalize_disposable_postgres_cleanup_continuation(**values)
    assert json.loads(result)["outcome"] == outcome
    assert cleanup_claim.exists() and continuation_claim.exists()
    assert not list(values["evidence_directory"].glob("postgres-cleanup-continuation-finalization-*.json"))


def test_missing_original_cleanup_claim_requires_investigation_before_inspection(
    tmp_path: Path, monkeypatch,
) -> None:
    values, cleanup_claim, continuation_claim = _setup(tmp_path)
    cleanup_claim.unlink()
    monkeypatch.setattr(
        finalize, "reconcile_disposable_postgres_cleanup_continuation",
        lambda **_: pytest.fail("inspector must not run"),
    )
    result = finalize.finalize_disposable_postgres_cleanup_continuation(**values)
    assert json.loads(result)["outcome"] == "investigation_required"
    assert continuation_claim.exists()


def test_unknown_claim_release_retries_from_evidence_without_inspector(
    tmp_path: Path, monkeypatch,
) -> None:
    values, cleanup_claim, continuation_claim = _setup(tmp_path)
    calls: list[str] = []
    _observed(monkeypatch, "container_removed", calls)
    original_release = finalize._release
    monkeypatch.setattr(
        finalize, "_release",
        lambda *_: (_ for _ in ()).throw(
            finalize.DisposablePostgresCleanupContinueFinalizeUnavailable()
        ),
    )
    with pytest.raises(finalize.DisposablePostgresCleanupContinueFinalizeUnavailable):
        finalize.finalize_disposable_postgres_cleanup_continuation(**values)
    assert cleanup_claim.exists() and continuation_claim.exists() and calls == ["container_removed"]

    monkeypatch.setattr(finalize, "_release", original_release)
    monkeypatch.setattr(
        finalize, "reconcile_disposable_postgres_cleanup_continuation",
        lambda **_: pytest.fail("evidence retry must not inspect"),
    )
    result = finalize.finalize_disposable_postgres_cleanup_continuation(**values)
    assert json.loads(result)["outcome"] == "later_prefix_finalized"
    assert cleanup_claim.exists() and not continuation_claim.exists()


def test_mismatched_reconciliation_hash_stops_before_inspector(tmp_path: Path, monkeypatch) -> None:
    values, cleanup_claim, continuation_claim = _setup(tmp_path)
    current = json.loads(values["continuation_finalization_file"].read_text())
    current["continuation_reconciliation_authorization_sha256"] = "0" * 64
    _private(values["continuation_finalization_file"], current)
    monkeypatch.setattr(
        finalize, "reconcile_disposable_postgres_cleanup_continuation",
        lambda **_: pytest.fail("inspector must not run"),
    )
    with pytest.raises(finalize.DisposablePostgresCleanupContinueFinalizeUnavailable):
        finalize.finalize_disposable_postgres_cleanup_continuation(**values)
    assert cleanup_claim.exists() and continuation_claim.exists()


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_cleanup_continuation_finalization",'
        b'"outcome":"continuation_attempt_finalized","schema_version":1}\n'
    )
    monkeypatch.setattr(
        finalize, "finalize_disposable_postgres_cleanup_continuation", lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--authorization-file", "/x/auth",
        "--reconciliation-file", "/x/recon", "--claim-reconciliation-file", "/x/claim",
        "--disposition-file", "/x/disposition", "--cleanup-file", "/x/cleanup",
        "--cleanup-reconciliation-file", "/x/cleanup-recon",
        "--cleanup-continuation-file", "/x/continuation",
        "--continuation-reconciliation-file", "/x/continuation-recon",
        "--continuation-finalization-file", "/x/continuation-final",
        "--staging-evidence-file", "/x/staging", "--compose-file", "/x/compose",
        "--runtime-env-file", "/x/runtime", "--image-env-file", "/x/images",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert finalize.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert finalize.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
