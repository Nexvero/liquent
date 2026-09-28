from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_volume_deletion_preflight as preflight
from tests.test_lq390_disposable_postgres_volume_disposition import (
    NOW, PROJECT, RUN, VOLUME, _hash, _inputs, _private, _volume,
)


def _values(tmp_path: Path, **changes):
    values, processes = _inputs(tmp_path, **changes)
    disposition = json.loads(values["volume_disposition_file"].read_text())
    retention = json.loads(values["retention_decision_file"].read_text())
    hold = json.loads(values["legal_hold_decision_file"].read_text())
    recovery = json.loads(values["recovery_decision_file"].read_text())
    deletion = _private(tmp_path / "volume-deletion.json", {
        "schema_version": 1, "volume_deletion_id": "volume-deletion-392",
        "volume_deletion_claim_id": "volume-deletion-claim-392",
        "volume_disposition_id": disposition["volume_disposition_id"],
        "retention_decision_id": retention["retention_decision_id"],
        "legal_hold_decision_id": hold["legal_hold_decision_id"],
        "recovery_decision_id": recovery["recovery_decision_id"],
        "run_id": RUN, "phase": "disposable_postgres",
        "source_commit": disposition["source_commit"],
        "image_ref": disposition["image_ref"],
        "compose_sha256": disposition["compose_sha256"],
        "retained_volume": VOLUME,
        "volume_disposition_authorization_sha256": _hash(
            values["volume_disposition_file"]
        ),
        "lineage_manifest_sha256": _hash(values["lineage_manifest_file"]),
        "retention_decision_sha256": _hash(values["retention_decision_file"]),
        "legal_hold_decision_sha256": _hash(values["legal_hold_decision_file"]),
        "recovery_decision_sha256": _hash(values["recovery_decision_file"]),
        "operation": "remove_disposable_postgres_data_volume",
        "scope": "data_volume_only", "executor_id": "deletion-executor",
        "authorizer_id": "deletion-authorizer", "reviewer_id": "deletion-reviewer",
        "valid_from": "2026-08-23T13:30:00Z",
        "valid_until": "2026-08-23T14:30:00Z",
    })
    values["volume_deletion_file"] = deletion
    return values, processes


def test_positive_fresh_resolution_is_ready_without_claim_or_mutation(tmp_path: Path) -> None:
    values, processes = _values(tmp_path)
    before = set(values["evidence_directory"].iterdir())
    result = preflight.preflight_disposable_postgres_volume_deletion(**values)
    assert json.loads(result) == {
        "operation": "disposable_postgres_volume_deletion_preflight",
        "outcome": "ready", "schema_version": 1,
    }
    assert set(values["evidence_directory"].iterdir()) == before == set()
    assert [call[0] for call in processes.calls] == [
        (str(values["docker_executable"]), "volume", "inspect", VOLUME),
    ]
    assert not any(set(call[0]) & {"rm", "remove", "prune", "mount"} for call in processes.calls)


@pytest.mark.parametrize("changes", [
    {"retention": "retain"}, {"hold": "active"},
    {"backup": "pending"}, {"restore": "pending"}, {"later_use": True},
])
def test_complete_negative_facts_are_rejected(tmp_path: Path, changes: dict) -> None:
    values, _ = _values(tmp_path, **changes)
    result = preflight.preflight_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "rejected"


@pytest.mark.parametrize("changes", [
    {"hold": "conflict"}, {"volume": b""},
    {"volume": _volume(project="foreign-project")},
])
def test_conflict_or_volume_mismatch_requires_investigation(
    tmp_path: Path, changes: dict,
) -> None:
    values, _ = _values(tmp_path, **changes)
    result = preflight.preflight_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "investigation_required"


def test_decision_hash_change_stops_before_docker(tmp_path: Path) -> None:
    values, processes = _values(tmp_path)
    values["retention_decision_file"].write_bytes(
        values["retention_decision_file"].read_bytes() + b" "
    )
    with pytest.raises(preflight.DisposablePostgresVolumeDeletionPreflightUnavailable):
        preflight.preflight_disposable_postgres_volume_deletion(**values)
    assert processes.calls == []


def test_existing_volume_deletion_claim_is_preserved_and_unavailable(tmp_path: Path) -> None:
    values, processes = _values(tmp_path)
    stem = hashlib.sha256(b"volume-deletion-claim-392").hexdigest()
    claim = _private(
        values["evidence_directory"] / f".postgres-volume-deletion-{stem}.claim",
        b"claim\n",
    )
    with pytest.raises(preflight.DisposablePostgresVolumeDeletionPreflightUnavailable):
        preflight.preflight_disposable_postgres_volume_deletion(**values)
    assert claim.exists() and processes.calls == []


@pytest.mark.parametrize(("field", "value"), [
    ("scope", "runtime_only"),
    ("operation", "remove_disposable_postgres_resources"),
    ("retained_volume", "caller-volume"),
    ("reviewer_id", "deletion-authorizer"),
])
def test_broadened_or_collapsed_authority_fails_closed(
    tmp_path: Path, field: str, value: str,
) -> None:
    values, processes = _values(tmp_path)
    authorization = json.loads(values["volume_deletion_file"].read_text())
    authorization[field] = value
    _private(values["volume_deletion_file"], authorization)
    with pytest.raises(preflight.DisposablePostgresVolumeDeletionPreflightUnavailable):
        preflight.preflight_disposable_postgres_volume_deletion(**values)
    assert processes.calls == []


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_volume_deletion_preflight",'
        b'"outcome":"ready","schema_version":1}\n'
    )
    monkeypatch.setattr(
        preflight, "preflight_disposable_postgres_volume_deletion", lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--volume-disposition-file", "/x/disposition",
        "--volume-deletion-file", "/x/deletion", "--lineage-manifest-file", "/x/lineage",
        "--retention-decision-file", "/x/retention", "--legal-hold-decision-file", "/x/hold",
        "--recovery-decision-file", "/x/recovery", "--project-name", PROJECT,
        "--evidence-directory", "/x/evidence",
    ]
    assert preflight.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert preflight.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_entry_point_is_installed() -> None:
    project = Path(__file__).parents[1] / "pyproject.toml"
    assert (
        'liquent-disposable-postgres-volume-deletion-preflight = '
        '"liquent_platform.operators.disposable_postgres_volume_deletion_preflight:main"'
    ) in project.read_text()
