from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

import liquent_platform.operators.rollback_evidence_inspect as inspect


NOW = datetime(2026, 8, 20, 12, tzinfo=UTC)
CANDIDATE = "registry.example/liquent@sha256:" + "a" * 64
PREVIOUS = "registry.example/liquent@sha256:" + "b" * 64


def _private(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.chmod(path, 0o600)
    return path


def _evidence() -> dict:
    return {
        "schema_version": 1, "environment": "staging", "source_commit": "c" * 40,
        "candidate_image_ref": CANDIDATE, "previous_healthy_image_ref": PREVIOUS,
        "rollback_target_image_ref": PREVIOUS, "backup_snapshot_ref": "snapshot-328",
        "backup_evidence_sha256": "d" * 64, "restore_evidence_sha256": "e" * 64,
        "created_at": "2026-08-20T10:00:00Z", "verified_at": "2026-08-20T11:00:00Z",
        "valid_until": "2026-08-20T13:00:00Z", "prepared_by": "operator-328",
        "reviewed_by": "reviewer-328", "status": "verified",
    }


def _files(tmp_path: Path, evidence: dict | None = None):
    evidence_file = _private(tmp_path / "evidence.json", evidence or _evidence())
    expectation = {
        "schema_version": 1, "run_id": "run-328", "environment": "staging",
        "source_commit": "c" * 40, "candidate_image_ref": CANDIDATE,
        "rollback_evidence_sha256": hashlib.sha256(evidence_file.read_bytes()).hexdigest(),
        "executor_id": "executor-328", "authorizer_id": "authorizer-328",
        "valid_from": "2026-08-20T11:30:00Z", "valid_until": "2026-08-20T13:00:00Z",
    }
    return _private(tmp_path / "expectation.json", expectation), evidence_file


def test_current_bound_evidence_is_true_and_output_is_exact(tmp_path: Path) -> None:
    expectation, evidence = _files(tmp_path)
    assert inspect.inspect_rollback_evidence(expectation, evidence, clock=lambda: NOW) is True
    assert inspect.inspect(expectation, evidence, clock=lambda: NOW) == (
        b'{"facts":{"rollback_current":true},"phase":"rollback",'
        b'"schema_version":1}\n'
    )


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(status="stale"),
    lambda value: value.update(source_commit="f" * 40),
    lambda value: value.update(rollback_target_image_ref=CANDIDATE),
    lambda value: value.update(reviewed_by=value["prepared_by"]),
    lambda value: value.update(valid_until="2026-08-20T11:59:59Z"),
])
def test_explicit_stale_or_mismatched_evidence_is_false(
    tmp_path: Path, mutation,
) -> None:
    value = _evidence()
    mutation(value)
    expectation, evidence = _files(tmp_path, value)
    # Keep the expectation bound to the intended run rather than mutated semantics.
    expected = json.loads(expectation.read_text())
    expected["source_commit"] = "c" * 40
    _private(expectation, expected)
    assert inspect.inspect_rollback_evidence(expectation, evidence, clock=lambda: NOW) is False


def test_hash_mismatch_is_false_without_detail(tmp_path: Path) -> None:
    expectation, evidence = _files(tmp_path)
    evidence.write_bytes(evidence.read_bytes() + b" ")
    assert inspect.inspect_rollback_evidence(expectation, evidence, clock=lambda: NOW) is False


def test_duplicate_keys_permissions_and_cli_failure_are_unavailable(
    tmp_path: Path, capsys,
) -> None:
    expectation, evidence = _files(tmp_path)
    evidence.write_text('{"schema_version":1,"schema_version":1}\n')
    expected = json.loads(expectation.read_text())
    expected["rollback_evidence_sha256"] = hashlib.sha256(evidence.read_bytes()).hexdigest()
    _private(expectation, expected)
    with pytest.raises(inspect.RollbackEvidenceInspectUnavailable):
        inspect.inspect_rollback_evidence(expectation, evidence, clock=lambda: NOW)
    os.chmod(expectation, 0o644)
    assert inspect.main([
        "--expectation-file", str(expectation), "--evidence-file", str(evidence),
    ]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
