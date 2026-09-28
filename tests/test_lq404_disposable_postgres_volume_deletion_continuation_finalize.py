from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_volume_deletion_continue as continuation
import liquent_platform.operators.disposable_postgres_volume_deletion_continue_finalize as finalize
from tests.test_lq390_disposable_postgres_volume_disposition import (
    PROJECT, VOLUME, _hash, _private, _volume,
)
from tests.test_lq394_disposable_postgres_volume_deletion import Processes, _observation
from tests.test_lq400_disposable_postgres_volume_deletion_continuation import _success
from tests.test_lq402_disposable_postgres_volume_deletion_continuation_reconcile import (
    _inputs as _reconciliation_inputs, _open_claim,
)


def _inputs(tmp_path: Path) -> tuple[dict, Path]:
    values, original_claim = _reconciliation_inputs(tmp_path)
    previous = json.loads(
        values["volume_deletion_continuation_reconciliation_file"].read_text(),
    )
    current = _private(tmp_path / "volume-deletion-continuation-finalization.json", {
        "schema_version": 1,
        "volume_deletion_continuation_finalization_id":
            "volume-deletion-continuation-finalization-404",
        **{key: previous[key] for key in previous if key not in {
            "schema_version", "operation", "executor_id", "authorizer_id",
            "reviewer_id", "valid_from", "valid_until",
        }},
        "volume_deletion_continuation_reconciliation_authorization_sha256": _hash(
            values["volume_deletion_continuation_reconciliation_file"],
        ),
        "operation": "finalize_disposable_postgres_volume_deletion_continuation",
        "executor_id": "continuation-finalization-executor",
        "authorizer_id": "continuation-finalization-authorizer",
        "reviewer_id": "continuation-finalization-reviewer",
        "valid_from": "2026-08-23T13:30:00Z",
        "valid_until": "2026-08-23T14:30:00Z",
    })
    values["volume_deletion_continuation_finalization_file"] = current
    values["processes"] = Processes([])
    return values, original_claim


def _evidence(values: dict) -> Path:
    current = json.loads(
        values["volume_deletion_continuation_finalization_file"].read_text(),
    )
    stem = hashlib.sha256(
        current["volume_deletion_continuation_finalization_id"].encode(),
    ).hexdigest()
    return values["evidence_directory"] / (
        f"postgres-volume-deletion-continuation-finalization-{stem}.json"
    )


def test_absent_volume_writes_evidence_before_subclaim_release(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([_observation()])
    result = finalize.finalize_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "volume_removal_ready_for_deletion_finalization"
    evidence = _evidence(values)
    record = json.loads(evidence.read_text())
    assert record["observed_state"] == "volume_absent_evidence_missing"
    assert record["outcome"] == "volume_removal_ready_for_deletion_finalization"
    assert evidence.exists() and not claim.exists() and original_claim.exists()


def test_continuation_evidence_is_confirmed_without_docker(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    operator_values = {
        key: value for key, value in values.items()
        if key not in {
            "volume_deletion_continuation_reconciliation_file",
            "volume_deletion_continuation_finalization_file",
        }
    }
    operator_values["processes"] = _success()
    continuation.continue_disposable_postgres_volume_deletion(**operator_values)
    values["processes"] = Processes([])
    result = finalize.finalize_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "continuation_evidence_confirmed"
    assert _evidence(values).exists() and original_claim.exists()
    assert values["processes"].calls == []


def test_present_volume_requires_investigation_without_write(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    claim = _open_claim(values)
    before = (original_claim.read_bytes(), claim.read_bytes())
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()), _observation(_volume()),
    ])
    result = finalize.finalize_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "investigation_required"
    assert before == (original_claim.read_bytes(), claim.read_bytes())
    assert not _evidence(values).exists()


def test_not_found_is_write_free_without_docker(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    result = finalize.finalize_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "not_found"
    assert original_claim.exists() and not _evidence(values).exists()
    assert values["processes"].calls == []


def test_foreign_volume_requires_investigation_without_write(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()),
        _observation(_volume(project="foreign-project")),
    ])
    result = finalize.finalize_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "investigation_required"
    assert original_claim.exists() and claim.exists() and not _evidence(values).exists()


def test_missing_original_claim_blocks_terminal_finalization(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    claim = _open_claim(values)
    original_claim.unlink()
    values["processes"] = Processes([])
    result = finalize.finalize_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "investigation_required"
    assert claim.exists() and not _evidence(values).exists()


def test_claim_release_retry_uses_evidence_without_inspector(
    tmp_path: Path, monkeypatch,
) -> None:
    values, original_claim = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([_observation()])
    original_release = finalize._release_claim
    monkeypatch.setattr(
        finalize, "_release_claim",
        lambda *_: (_ for _ in ()).throw(
            finalize.DisposablePostgresVolumeDeletionContinueFinalizeUnavailable()
        ),
    )
    with pytest.raises(
        finalize.DisposablePostgresVolumeDeletionContinueFinalizeUnavailable,
    ):
        finalize.finalize_disposable_postgres_volume_deletion_continuation(**values)
    assert claim.exists() and _evidence(values).exists() and original_claim.exists()

    monkeypatch.setattr(finalize, "_release_claim", original_release)
    values["processes"] = Processes([])
    result = finalize.finalize_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "volume_removal_ready_for_deletion_finalization"
    assert not claim.exists() and original_claim.exists()
    assert values["processes"].calls == []


def test_reconciliation_hash_mismatch_stops_before_inspector(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    current = json.loads(
        values["volume_deletion_continuation_finalization_file"].read_text(),
    )
    current["volume_deletion_continuation_reconciliation_authorization_sha256"] = "0" * 64
    _private(values["volume_deletion_continuation_finalization_file"], current)
    with pytest.raises(
        finalize.DisposablePostgresVolumeDeletionContinueFinalizeUnavailable,
    ):
        finalize.finalize_disposable_postgres_volume_deletion_continuation(**values)
    assert original_claim.exists() and values["processes"].calls == []


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_volume_deletion_continuation_finalization",'
        b'"outcome":"continuation_evidence_confirmed","schema_version":1}\n'
    )
    monkeypatch.setattr(
        finalize, "finalize_disposable_postgres_volume_deletion_continuation",
        lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--volume-disposition-file", "/x/disposition",
        "--volume-deletion-file", "/x/deletion",
        "--volume-deletion-reconciliation-file", "/x/reconciliation",
        "--volume-deletion-finalization-file", "/x/finalization",
        "--volume-deletion-continuation-file", "/x/continuation",
        "--volume-deletion-continuation-reconciliation-file", "/x/inspection",
        "--volume-deletion-continuation-finalization-file", "/x/finish",
        "--lineage-manifest-file", "/x/lineage",
        "--retention-decision-file", "/x/retention",
        "--legal-hold-decision-file", "/x/hold",
        "--recovery-decision-file", "/x/recovery",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert finalize.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert finalize.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_entry_point_is_installed() -> None:
    project = Path(__file__).parents[1] / "pyproject.toml"
    assert (
        'liquent-disposable-postgres-volume-delete-continue-finalize = '
        '"liquent_platform.operators.disposable_postgres_volume_deletion_continue_finalize:main"'
    ) in project.read_text()
