from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_volume_deletion as deletion
import liquent_platform.operators.disposable_postgres_volume_deletion_reconcile as reconcile
from liquent_platform.operators.disposable_postgres_reconcile import _evidence_root
from tests.test_lq390_disposable_postgres_volume_disposition import (
    NOW, PROJECT, VOLUME, _hash, _private, _volume,
)
from tests.test_lq392_disposable_postgres_volume_deletion_preflight import _values
from tests.test_lq394_disposable_postgres_volume_deletion import (
    Processes, _observation, _success_processes,
)


def _inputs(tmp_path: Path):
    values, _ = _values(tmp_path)
    current = json.loads(values["volume_deletion_file"].read_text())
    reconciliation = _private(tmp_path / "volume-deletion-reconciliation.json", {
        "schema_version": 1,
        "volume_deletion_reconciliation_id": "volume-deletion-reconciliation-396",
        **{key: current[key] for key in (
            "volume_deletion_id", "volume_deletion_claim_id", "volume_disposition_id",
            "retention_decision_id", "legal_hold_decision_id", "recovery_decision_id",
            "run_id", "phase", "source_commit", "image_ref", "compose_sha256",
            "retained_volume", "volume_disposition_authorization_sha256",
            "lineage_manifest_sha256", "retention_decision_sha256",
            "legal_hold_decision_sha256", "recovery_decision_sha256", "scope",
        )},
        "volume_deletion_authorization_sha256": _hash(values["volume_deletion_file"]),
        "operation": "inspect_disposable_postgres_volume_deletion",
        "executor_id": "reconciliation-executor",
        "authorizer_id": "reconciliation-authorizer",
        "reviewer_id": "reconciliation-reviewer",
        "valid_from": "2026-08-23T13:30:00Z",
        "valid_until": "2026-08-23T14:30:00Z",
    })
    values["volume_deletion_reconciliation_file"] = reconciliation
    values["processes"] = Processes([])
    return values


def _open_claim(values: dict) -> Path:
    raw, current = deletion._historical_authorization(values["volume_deletion_file"])
    binding = deletion._binding(current, raw)
    stem = hashlib.sha256(current["volume_deletion_claim_id"].encode()).hexdigest()
    claim = values["evidence_directory"] / f".postgres-volume-deletion-{stem}.claim"
    descriptor = _evidence_root(values["evidence_directory"])
    try:
        deletion._create_claim(
            claim, binding, "2026-08-23T14:00:00Z", descriptor,
        )
    finally:
        os.close(descriptor)
    return claim


def test_missing_claim_and_evidence_is_not_found_without_docker(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    result = reconcile.reconcile_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "not_found"
    assert values["processes"].calls == []


def test_open_claim_and_exact_volume_is_present_read_only(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()), _observation(_volume()),
    ])
    before = claim.read_bytes()
    result = reconcile.reconcile_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "volume_present"
    assert claim.read_bytes() == before
    assert [call[0] for call in values["processes"].calls] == [
        (str(values["docker_executable"]), "volume", "ls", "--filter",
         f"name=^{VOLUME}$", "--format", "{{.Name}}"),
        (str(values["docker_executable"]), "volume", "inspect", VOLUME),
    ]
    assert not any(set(call[0]) & {"rm", "remove", "prune", "mount"}
                   for call in values["processes"].calls)


def test_open_claim_and_absent_volume_needs_evidence(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([_observation()])
    result = reconcile.reconcile_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "volume_absent_evidence_missing"
    assert claim.exists()
    assert len(values["processes"].calls) == 1


def test_foreign_bound_volume_is_conflict(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()),
        _observation(_volume(project="foreign-project")),
    ])
    result = reconcile.reconcile_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "conflict"
    assert claim.exists()


def test_final_evidence_has_priority_without_docker(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    deletion_values = {
        key: value for key, value in values.items()
        if key != "volume_deletion_reconciliation_file"
    }
    deletion_values["processes"] = _success_processes()
    deletion.delete_disposable_postgres_volume(**deletion_values)
    values["processes"] = Processes([])
    result = reconcile.reconcile_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "final_evidence_present"
    assert values["processes"].calls == []


def test_malformed_claim_is_unavailable_without_docker(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    current = json.loads(values["volume_deletion_file"].read_text())
    stem = hashlib.sha256(current["volume_deletion_claim_id"].encode()).hexdigest()
    claim = values["evidence_directory"] / f".postgres-volume-deletion-{stem}.claim"
    _private(claim, b"foreign\n")
    with pytest.raises(reconcile.DisposablePostgresVolumeDeletionReconcileUnavailable):
        reconcile.reconcile_disposable_postgres_volume_deletion(**values)
    assert claim.exists() and values["processes"].calls == []


@pytest.mark.parametrize("observation", [
    _observation(returncode=1), _observation(stderr=b"error"),
    _observation(timed_out=True), _observation((VOLUME + "\n" + VOLUME + "\n").encode()),
])
def test_ambiguous_list_is_technically_unavailable(
    tmp_path: Path, observation,
) -> None:
    values = _inputs(tmp_path)
    claim = _open_claim(values)
    values["processes"] = Processes([observation])
    with pytest.raises(reconcile.DisposablePostgresVolumeDeletionReconcileUnavailable):
        reconcile.reconcile_disposable_postgres_volume_deletion(**values)
    assert claim.exists()


def test_reconciliation_hash_mismatch_stops_before_claim_and_docker(tmp_path: Path) -> None:
    values = _inputs(tmp_path)
    current = json.loads(values["volume_deletion_reconciliation_file"].read_text())
    current["volume_deletion_authorization_sha256"] = "0" * 64
    _private(values["volume_deletion_reconciliation_file"], current)
    with pytest.raises(reconcile.DisposablePostgresVolumeDeletionReconcileUnavailable):
        reconcile.reconcile_disposable_postgres_volume_deletion(**values)
    assert values["processes"].calls == []


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_volume_deletion_reconciliation",'
        b'"outcome":"volume_present","schema_version":1}\n'
    )
    monkeypatch.setattr(
        reconcile, "reconcile_disposable_postgres_volume_deletion", lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--volume-disposition-file", "/x/disposition",
        "--volume-deletion-file", "/x/deletion",
        "--volume-deletion-reconciliation-file", "/x/reconciliation",
        "--lineage-manifest-file", "/x/lineage", "--retention-decision-file", "/x/retention",
        "--legal-hold-decision-file", "/x/hold", "--recovery-decision-file", "/x/recovery",
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
        'liquent-disposable-postgres-volume-delete-reconcile = '
        '"liquent_platform.operators.disposable_postgres_volume_deletion_reconcile:main"'
    ) in project.read_text()
