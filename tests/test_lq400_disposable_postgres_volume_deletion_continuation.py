from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_volume_deletion_continue as continuation
from tests.test_lq390_disposable_postgres_volume_disposition import (
    PROJECT, VOLUME, _hash, _private, _volume,
)
from tests.test_lq394_disposable_postgres_volume_deletion import Processes, _observation
from tests.test_lq396_disposable_postgres_volume_deletion_reconcile import _open_claim
from tests.test_lq398_disposable_postgres_volume_deletion_finalize import (
    _inputs as _finalization_inputs,
)


def _inputs(tmp_path: Path) -> tuple[dict, Path]:
    values = _finalization_inputs(tmp_path)
    previous = json.loads(values["volume_deletion_finalization_file"].read_text())
    current = _private(tmp_path / "volume-deletion-continuation.json", {
        "schema_version": 1,
        "volume_deletion_continuation_id": "volume-deletion-continuation-400",
        "volume_deletion_continuation_claim_id": "volume-deletion-continuation-claim-400",
        **{key: previous[key] for key in previous if key not in {
            "schema_version", "operation", "executor_id", "authorizer_id",
            "reviewer_id", "valid_from", "valid_until",
        }},
        "volume_deletion_finalization_authorization_sha256": _hash(
            values["volume_deletion_finalization_file"],
        ),
        "operation": "continue_disposable_postgres_volume_deletion",
        "executor_id": "continuation-executor",
        "authorizer_id": "continuation-authorizer",
        "reviewer_id": "continuation-reviewer",
        "valid_from": "2026-08-23T13:30:00Z",
        "valid_until": "2026-08-23T14:30:00Z",
    })
    values["volume_deletion_continuation_file"] = current
    original_claim = _open_claim(values)
    return values, original_claim


def _paths(values: dict) -> tuple[Path, Path]:
    current = json.loads(values["volume_deletion_continuation_file"].read_text())
    claim_stem = hashlib.sha256(
        current["volume_deletion_continuation_claim_id"].encode(),
    ).hexdigest()
    evidence_stem = hashlib.sha256(
        current["volume_deletion_continuation_id"].encode(),
    ).hexdigest()
    root = values["evidence_directory"]
    return (
        root / f".postgres-volume-deletion-continuation-{claim_stem}.claim",
        root / f"postgres-volume-deletion-continuation-{evidence_stem}.json",
    )


def _success() -> Processes:
    return Processes([
        _observation((VOLUME + "\n").encode()), _observation(_volume()),
        _observation(_volume()), _observation(), _observation(),
    ])


def test_present_volume_is_removed_once_and_original_claim_stays_open(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    values["processes"] = _success()
    result = continuation.continue_disposable_postgres_volume_deletion(**values)
    claim, evidence = _paths(values)
    assert json.loads(result)["outcome"] == "volume_removal_pending_finalization"
    assert original_claim.exists() and not claim.exists() and evidence.exists()
    record = json.loads(evidence.read_text())
    assert record["outcome"] == "volume_removal_pending_finalization"
    assert record["absence_confirmed"] is True
    calls = [call[0] for call in values["processes"].calls]
    assert calls[-3:] == [
        (str(values["docker_executable"]), "volume", "inspect", VOLUME),
        (str(values["docker_executable"]), "volume", "rm", VOLUME),
        (str(values["docker_executable"]), "volume", "ls", "--filter",
         f"name=^{VOLUME}$", "--format", "{{.Name}}"),
    ]
    assert sum("rm" in call for call in calls) == 1


@pytest.mark.parametrize("failure", [
    _observation(returncode=1), _observation(stderr=b"ambiguous"),
    _observation(timed_out=True),
])
def test_unknown_remove_outcome_keeps_both_claims_without_evidence(
    tmp_path: Path, failure,
) -> None:
    values, original_claim = _inputs(tmp_path)
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()), _observation(_volume()),
        _observation(_volume()), failure,
    ])
    with pytest.raises(continuation.DisposablePostgresVolumeDeletionContinueUnavailable):
        continuation.continue_disposable_postgres_volume_deletion(**values)
    claim, evidence = _paths(values)
    assert original_claim.exists() and claim.exists() and not evidence.exists()
    assert sum("rm" in call[0] for call in values["processes"].calls) == 1


def test_unconfirmed_absence_keeps_both_claims(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()), _observation(_volume()),
        _observation(_volume()), _observation(),
        _observation((VOLUME + "\n").encode()),
    ])
    with pytest.raises(continuation.DisposablePostgresVolumeDeletionContinueUnavailable):
        continuation.continue_disposable_postgres_volume_deletion(**values)
    claim, evidence = _paths(values)
    assert original_claim.exists() and claim.exists() and not evidence.exists()


def test_existing_continuation_claim_stops_before_docker(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    claim, evidence = _paths(values)
    _private(claim, b"foreign\n")
    values["processes"] = _success()
    with pytest.raises(continuation.DisposablePostgresVolumeDeletionContinueUnavailable):
        continuation.continue_disposable_postgres_volume_deletion(**values)
    assert original_claim.exists() and claim.exists() and not evidence.exists()
    assert len(values["processes"].calls) == 2


def test_last_inspect_conflict_stops_without_remove(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    values["processes"] = Processes([
        _observation((VOLUME + "\n").encode()), _observation(_volume()),
        _observation(_volume(project="foreign-project")),
    ])
    with pytest.raises(continuation.DisposablePostgresVolumeDeletionContinueUnavailable):
        continuation.continue_disposable_postgres_volume_deletion(**values)
    claim, evidence = _paths(values)
    assert original_claim.exists() and claim.exists() and not evidence.exists()
    assert not any("rm" in call[0] for call in values["processes"].calls)


def test_evidence_retry_releases_only_continuation_claim_without_docker(
    tmp_path: Path, monkeypatch,
) -> None:
    values, original_claim = _inputs(tmp_path)
    values["processes"] = _success()
    original_release = continuation._release_claim
    monkeypatch.setattr(
        continuation, "_release_claim",
        lambda *_: (_ for _ in ()).throw(
            continuation.DisposablePostgresVolumeDeletionContinueUnavailable()
        ),
    )
    with pytest.raises(continuation.DisposablePostgresVolumeDeletionContinueUnavailable):
        continuation.continue_disposable_postgres_volume_deletion(**values)
    claim, evidence = _paths(values)
    assert claim.exists() and evidence.exists() and original_claim.exists()

    monkeypatch.setattr(continuation, "_release_claim", original_release)
    values["processes"] = Processes([])
    result = continuation.continue_disposable_postgres_volume_deletion(**values)
    assert json.loads(result)["outcome"] == "volume_removal_pending_finalization"
    assert not claim.exists() and original_claim.exists()
    assert values["processes"].calls == []


def test_finalization_hash_mismatch_stops_before_docker(tmp_path: Path) -> None:
    values, original_claim = _inputs(tmp_path)
    current = json.loads(values["volume_deletion_continuation_file"].read_text())
    current["volume_deletion_finalization_authorization_sha256"] = "0" * 64
    _private(values["volume_deletion_continuation_file"], current)
    with pytest.raises(continuation.DisposablePostgresVolumeDeletionContinueUnavailable):
        continuation.continue_disposable_postgres_volume_deletion(**values)
    assert original_claim.exists() and values["processes"].calls == []


@pytest.mark.parametrize(("finalized", "expected"), [
    ("volume_removal_finalized", "already_finalized"),
    ("deletion_evidence_confirmed", "already_finalized"),
    ("not_found", "not_found"),
    ("investigation_required", "investigation_required"),
])
def test_closed_finalizer_outcomes_never_create_continuation_claim(
    tmp_path: Path, monkeypatch, finalized: str, expected: str,
) -> None:
    values, _ = _inputs(tmp_path)
    monkeypatch.setattr(
        continuation, "finalize_disposable_postgres_volume_deletion",
        lambda **_: json.dumps({
            "operation": "disposable_postgres_volume_deletion_finalization",
            "outcome": finalized, "schema_version": 1,
        }).encode(),
    )
    result = continuation.continue_disposable_postgres_volume_deletion(**values)
    claim, evidence = _paths(values)
    assert json.loads(result)["outcome"] == expected
    assert not claim.exists() and not evidence.exists()


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_volume_deletion_continuation",'
        b'"outcome":"volume_removal_pending_finalization","schema_version":1}\n'
    )
    monkeypatch.setattr(
        continuation, "continue_disposable_postgres_volume_deletion", lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--volume-disposition-file", "/x/disposition",
        "--volume-deletion-file", "/x/deletion",
        "--volume-deletion-reconciliation-file", "/x/reconciliation",
        "--volume-deletion-finalization-file", "/x/finalization",
        "--volume-deletion-continuation-file", "/x/continuation",
        "--lineage-manifest-file", "/x/lineage",
        "--retention-decision-file", "/x/retention",
        "--legal-hold-decision-file", "/x/hold",
        "--recovery-decision-file", "/x/recovery",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert continuation.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert continuation.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_entry_point_is_installed() -> None:
    project = Path(__file__).parents[1] / "pyproject.toml"
    assert (
        'liquent-disposable-postgres-volume-delete-continue = '
        '"liquent_platform.operators.disposable_postgres_volume_deletion_continue:main"'
    ) in project.read_text()
