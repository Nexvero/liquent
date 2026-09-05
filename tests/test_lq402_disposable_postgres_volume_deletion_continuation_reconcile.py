from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_volume_deletion_continue as continuation
import liquent_platform.operators.disposable_postgres_volume_deletion_continue_reconcile as reconcile
from liquent_platform.operators.disposable_postgres_reconcile import _evidence_root
from tests.test_lq390_disposable_postgres_volume_disposition import (
    NOW, PROJECT, VOLUME, _hash, _private, _volume,
)
from tests.test_lq394_disposable_postgres_volume_deletion import Processes, _observation
from tests.test_lq400_disposable_postgres_volume_deletion_continuation import (
    _inputs as _continuation_inputs, _success,
)


def _inputs(tmp_path: Path) -> tuple[dict, Path]:
    values, original_claim = _continuation_inputs(tmp_path)
    previous = json.loads(values["volume_deletion_continuation_file"].read_text())
    current = _private(tmp_path / "volume-deletion-continuation-reconciliation.json", {
        "schema_version": 1,
        "volume_deletion_continuation_reconciliation_id":
            "volume-deletion-continuation-reconciliation-402",
        **{key: previous[key] for key in previous if key not in {
            "schema_version", "operation", "executor_id", "authorizer_id",
            "reviewer_id", "valid_from", "valid_until",
        }},
        "volume_deletion_continuation_authorization_sha256": _hash(
            values["volume_deletion_continuation_file"],
        ),
        "operation": "inspect_disposable_postgres_volume_deletion_continuation",
        "executor_id": "continuation-inspector",
        "authorizer_id": "continuation-inspection-authorizer",
        "reviewer_id": "continuation-inspection-reviewer",
        "valid_from": "2026-08-23T13:30:00Z",
        "valid_until": "2026-08-23T14:30:00Z",
    })
    values["volume_deletion_continuation_reconciliation_file"] = current
    values["processes"] = Processes([])
    return values, original_claim


def _open_claim(values: dict) -> Path:
    raw, current = continuation._authorization(
        values["volume_deletion_continuation_file"], clock=lambda: NOW,
    )
    binding = continuation._binding(current, raw)
    stem = hashlib.sha256(
        current["volume_deletion_continuation_claim_id"].encode(),
    ).hexdigest()
    claim = values["evidence_directory"] / (
        f".postgres-volume-deletion-continuation-{stem}.claim"
    )
    descriptor = _evidence_root(values["evidence_directory"])
    try:
        continuation._create_claim(claim, binding, "2026-08-23T14:00:00Z", descriptor)
    finally:
        os.close(descriptor)
    return claim


def test_missing_continuation_claim_and_evidence_is_not_found(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    result = reconcile.reconcile_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "not_found"
    assert original_claim.exists() and values["processes"].calls == []


def test_open_double_claim_and_exact_volume_is_present_read_only(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    claim = _open_claim(values)
    before = (original_claim.read_bytes(), claim.read_bytes())
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()), _observation(_volume()),
    ])
    result = reconcile.reconcile_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "volume_present"
    assert before == (original_claim.read_bytes(), claim.read_bytes())
    assert [call[0] for call in values["processes"].calls] == [
        (str(values["docker_executable"]), "volume", "ls", "--filter",
         f"name=^{VOLUME}$", "--format", "{{.Name}}"),
        (str(values["docker_executable"]), "volume", "inspect", VOLUME),
    ]
    assert not any(set(call[0]) & {"rm", "remove", "prune", "mount"}
                   for call in values["processes"].calls)


def test_open_double_claim_and_absent_volume_needs_evidence(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([_observation()])
    result = reconcile.reconcile_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "volume_absent_evidence_missing"
    assert original_claim.exists() and claim.exists()


def test_foreign_bound_volume_is_conflict(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()),
        _observation(_volume(project="foreign-project")),
    ])
    result = reconcile.reconcile_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "conflict"
    assert original_claim.exists() and claim.exists()


def test_continuation_evidence_has_priority_without_docker(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    operator_values = {
        key: value for key, value in values.items()
        if key != "volume_deletion_continuation_reconciliation_file"
    }
    operator_values["processes"] = _success()
    continuation.continue_disposable_postgres_volume_deletion(**operator_values)
    values["processes"] = Processes([])
    result = reconcile.reconcile_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "continuation_evidence_present"
    assert original_claim.exists() and values["processes"].calls == []


def test_missing_original_claim_is_conflict_without_docker(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    claim = _open_claim(values)
    original_claim.unlink()
    result = reconcile.reconcile_disposable_postgres_volume_deletion_continuation(**values)
    assert json.loads(result)["outcome"] == "conflict"
    assert claim.exists() and values["processes"].calls == []


def test_malformed_continuation_claim_is_unavailable_without_docker(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    current = json.loads(values["volume_deletion_continuation_file"].read_text())
    stem = hashlib.sha256(
        current["volume_deletion_continuation_claim_id"].encode(),
    ).hexdigest()
    claim = values["evidence_directory"] / (
        f".postgres-volume-deletion-continuation-{stem}.claim"
    )
    _private(claim, b"foreign\n")
    with pytest.raises(
        reconcile.DisposablePostgresVolumeDeletionContinueReconcileUnavailable,
    ):
        reconcile.reconcile_disposable_postgres_volume_deletion_continuation(**values)
    assert original_claim.exists() and claim.exists() and values["processes"].calls == []


@pytest.mark.parametrize("observation", [
    _observation(returncode=1), _observation(stderr=b"error"),
    _observation(timed_out=True),
    _observation((VOLUME + "\n" + VOLUME + "\n").encode()),
])
def test_ambiguous_list_is_technically_unavailable(
    tmp_path: Path, observation,
) -> None:
    values, original_claim = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([observation])
    with pytest.raises(
        reconcile.DisposablePostgresVolumeDeletionContinueReconcileUnavailable,
    ):
        reconcile.reconcile_disposable_postgres_volume_deletion_continuation(**values)
    assert original_claim.exists() and claim.exists()


def test_reconciliation_hash_mismatch_stops_before_claim_and_docker(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    current = json.loads(
        values["volume_deletion_continuation_reconciliation_file"].read_text(),
    )
    current["volume_deletion_continuation_authorization_sha256"] = "0" * 64
    _private(values["volume_deletion_continuation_reconciliation_file"], current)
    with pytest.raises(
        reconcile.DisposablePostgresVolumeDeletionContinueReconcileUnavailable,
    ):
        reconcile.reconcile_disposable_postgres_volume_deletion_continuation(**values)
    assert original_claim.exists() and values["processes"].calls == []


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_volume_deletion_continuation_reconciliation",'
        b'"outcome":"volume_present","schema_version":1}\n'
    )
    monkeypatch.setattr(
        reconcile, "reconcile_disposable_postgres_volume_deletion_continuation",
        lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--volume-disposition-file", "/x/disposition",
        "--volume-deletion-file", "/x/deletion",
        "--volume-deletion-reconciliation-file", "/x/reconciliation",
        "--volume-deletion-finalization-file", "/x/finalization",
        "--volume-deletion-continuation-file", "/x/continuation",
        "--volume-deletion-continuation-reconciliation-file", "/x/inspection",
        "--lineage-manifest-file", "/x/lineage",
        "--retention-decision-file", "/x/retention",
        "--legal-hold-decision-file", "/x/hold",
        "--recovery-decision-file", "/x/recovery",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert reconcile.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert reconcile.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_entry_point_is_installed() -> None:
    project = Path(__file__).parents[1] / "pyproject.toml"
    assert (
        'liquent-disposable-postgres-volume-delete-continue-reconcile = '
        '"liquent_platform.operators.disposable_postgres_volume_deletion_continue_reconcile:main"'
    ) in project.read_text()
