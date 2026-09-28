from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_volume_deletion as deletion
import liquent_platform.operators.disposable_postgres_volume_deletion_finalize as finalize
from tests.test_lq390_disposable_postgres_volume_disposition import (
    PROJECT, VOLUME, _hash, _private, _volume,
)
from tests.test_lq394_disposable_postgres_volume_deletion import (
    Processes, _observation, _success_processes,
)
from tests.test_lq396_disposable_postgres_volume_deletion_reconcile import (
    _inputs as _reconciliation_inputs, _open_claim,
)


def _inputs(tmp_path: Path):
    values = _reconciliation_inputs(tmp_path)
    previous = json.loads(values["volume_deletion_reconciliation_file"].read_text())
    current = _private(tmp_path / "volume-deletion-finalization.json", {
        "schema_version": 1,
        "volume_deletion_finalization_id": "volume-deletion-finalization-398",
        **{key: previous[key] for key in previous if key not in {
            "schema_version", "operation", "executor_id", "authorizer_id",
            "reviewer_id", "valid_from", "valid_until",
        }},
        "volume_deletion_reconciliation_authorization_sha256": _hash(
            values["volume_deletion_reconciliation_file"]
        ),
        "operation": "finalize_disposable_postgres_volume_deletion",
        "executor_id": "finalization-executor",
        "authorizer_id": "finalization-authorizer",
        "reviewer_id": "finalization-reviewer",
        "valid_from": "2026-08-23T13:30:00Z",
        "valid_until": "2026-08-23T14:30:00Z",
    })
    values["volume_deletion_finalization_file"] = current
    return values


def _final_evidence(values: dict) -> Path:
    current = json.loads(values["volume_deletion_finalization_file"].read_text())
    stem = hashlib.sha256(current["volume_deletion_finalization_id"].encode()).hexdigest()
    return values["evidence_directory"] / f"postgres-volume-deletion-finalization-{stem}.json"


def test_absent_volume_writes_finalization_evidence_before_claim_release(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([_observation()])
    result = finalize.finalize_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "volume_removal_finalized"
    evidence = _final_evidence(values)
    record = json.loads(evidence.read_text())
    assert record["observed_state"] == "volume_absent_evidence_missing"
    assert record["outcome"] == "volume_removal_finalized"
    assert evidence.exists() and not claim.exists()
    assert len(values["processes"].calls) == 1


def test_original_deletion_evidence_is_confirmed_without_docker(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    deletion_values = {
        key: value for key, value in values.items()
        if key not in {
            "volume_deletion_reconciliation_file",
            "volume_deletion_finalization_file",
        }
    }
    deletion_values["processes"] = _success_processes()
    deletion.delete_disposable_postgres_volume(**deletion_values)
    values["processes"] = Processes([])
    result = finalize.finalize_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "deletion_evidence_confirmed"
    assert _final_evidence(values).exists()
    assert values["processes"].calls == []


def test_present_volume_requires_continuation_without_write(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    claim = _open_claim(values)
    before = claim.read_bytes()
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()), _observation(_volume()),
    ])
    result = finalize.finalize_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "continuation_required"
    assert claim.read_bytes() == before and not _final_evidence(values).exists()


def test_not_found_is_write_free_without_docker(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    result = finalize.finalize_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "not_found"
    assert not _final_evidence(values).exists() and values["processes"].calls == []


def test_conflict_requires_investigation_without_write(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()),
        _observation(_volume(project="foreign-project")),
    ])
    result = finalize.finalize_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "investigation_required"
    assert claim.exists() and not _final_evidence(values).exists()


@pytest.mark.parametrize("field", [
    "volume_deletion_reconciliation_authorization_sha256",
    "volume_deletion_authorization_sha256",
])
def test_hash_mismatch_stops_before_inspector(
    tmp_path: Path, field: str,
) -> None:
    values = _inputs(tmp_path)
    current = json.loads(values["volume_deletion_finalization_file"].read_text())
    current[field] = "0" * 64
    _private(values["volume_deletion_finalization_file"], current)
    with pytest.raises(finalize.DisposablePostgresVolumeDeletionFinalizeUnavailable):
        finalize.finalize_disposable_postgres_volume_deletion(**values)
    assert values["processes"].calls == []


def test_claim_release_retry_uses_evidence_without_inspector(
    tmp_path: Path, monkeypatch,
) -> None:
    values = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([_observation()])
    original_release = finalize._release_claim
    monkeypatch.setattr(
        finalize, "_release_claim",
        lambda *_: (_ for _ in ()).throw(finalize.DisposablePostgresVolumeDeletionFinalizeUnavailable()),
    )
    with pytest.raises(finalize.DisposablePostgresVolumeDeletionFinalizeUnavailable):
        finalize.finalize_disposable_postgres_volume_deletion(**values)
    assert claim.exists() and _final_evidence(values).exists()

    monkeypatch.setattr(finalize, "_release_claim", original_release)
    values["processes"] = Processes([])
    result = finalize.finalize_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "volume_removal_finalized"
    assert not claim.exists() and values["processes"].calls == []


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_volume_deletion_finalization",'
        b'"outcome":"volume_removal_finalized","schema_version":1}\n'
    )
    monkeypatch.setattr(
        finalize, "finalize_disposable_postgres_volume_deletion", lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--volume-disposition-file", "/x/disposition",
        "--volume-deletion-file", "/x/deletion",
        "--volume-deletion-reconciliation-file", "/x/reconciliation",
        "--volume-deletion-finalization-file", "/x/finalization",
        "--lineage-manifest-file", "/x/lineage", "--retention-decision-file", "/x/retention",
        "--legal-hold-decision-file", "/x/hold", "--recovery-decision-file", "/x/recovery",
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
        'liquent-disposable-postgres-volume-delete-finalize = '
        '"liquent_platform.operators.disposable_postgres_volume_deletion_finalize:main"'
    ) in project.read_text()
