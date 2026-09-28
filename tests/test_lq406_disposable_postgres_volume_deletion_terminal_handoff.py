from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_volume_deletion_terminal_handoff as handoff
from tests.test_lq390_disposable_postgres_volume_disposition import (
    PROJECT, _hash, _private,
)
from tests.test_lq394_disposable_postgres_volume_deletion import Processes, _observation
from tests.test_lq400_disposable_postgres_volume_deletion_continuation import _success
from tests.test_lq402_disposable_postgres_volume_deletion_continuation_reconcile import _open_claim
from tests.test_lq404_disposable_postgres_volume_deletion_continuation_finalize import (
    _inputs as _finalization_inputs,
)
import liquent_platform.operators.disposable_postgres_volume_deletion_continue as continuation
import liquent_platform.operators.disposable_postgres_volume_deletion_continue_finalize as continuation_finalize


def _setup(tmp_path: Path, *, confirmed: bool = False) -> tuple[dict, Path]:
    values, original_claim = _finalization_inputs(tmp_path)
    if confirmed:
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
    else:
        _open_claim(values)
        values["processes"] = Processes([_observation()])
    continuation_finalize.finalize_disposable_postgres_volume_deletion_continuation(
        **values,
    )
    deletion = json.loads(values["volume_deletion_file"].read_text())
    terminal_reconciliation = _private(tmp_path / "terminal-reconciliation.json", {
        "schema_version": 1,
        "volume_deletion_reconciliation_id": "terminal-reconciliation-406",
        **{key: deletion[key] for key in (
            "volume_deletion_id", "volume_deletion_claim_id", "volume_disposition_id",
            "retention_decision_id", "legal_hold_decision_id", "recovery_decision_id",
            "run_id", "phase", "source_commit", "image_ref", "compose_sha256",
            "retained_volume", "volume_disposition_authorization_sha256",
            "lineage_manifest_sha256", "retention_decision_sha256",
            "legal_hold_decision_sha256", "recovery_decision_sha256", "scope",
        )},
        "volume_deletion_authorization_sha256": _hash(values["volume_deletion_file"]),
        "operation": "inspect_disposable_postgres_volume_deletion",
        "executor_id": "terminal-inspector",
        "authorizer_id": "terminal-inspection-authorizer",
        "reviewer_id": "terminal-inspection-reviewer",
        "valid_from": "2026-08-23T13:30:00Z",
        "valid_until": "2026-08-23T14:30:00Z",
    })
    reconciliation = json.loads(terminal_reconciliation.read_text())
    terminal_finalization = _private(tmp_path / "terminal-finalization.json", {
        "schema_version": 1,
        "volume_deletion_finalization_id": "terminal-finalization-406",
        **{key: reconciliation[key] for key in reconciliation if key not in {
            "schema_version", "operation", "executor_id", "authorizer_id",
            "reviewer_id", "valid_from", "valid_until",
        }},
        "volume_deletion_reconciliation_authorization_sha256": _hash(
            terminal_reconciliation,
        ),
        "operation": "finalize_disposable_postgres_volume_deletion",
        "executor_id": "terminal-finalizer",
        "authorizer_id": "terminal-finalization-authorizer",
        "reviewer_id": "terminal-finalization-reviewer",
        "valid_from": "2026-08-23T13:30:00Z",
        "valid_until": "2026-08-23T14:30:00Z",
    })
    previous = json.loads(
        values["volume_deletion_continuation_finalization_file"].read_text(),
    )
    evidence_stem = hashlib.sha256(
        previous["volume_deletion_continuation_finalization_id"].encode(),
    ).hexdigest()
    final_evidence = values["evidence_directory"] / (
        f"postgres-volume-deletion-continuation-finalization-{evidence_stem}.json"
    )
    authorization = _private(tmp_path / "terminal-handoff.json", {
        "schema_version": 1,
        **{key: previous[key] for key in previous if key not in {
            "schema_version", "operation", "executor_id", "authorizer_id",
            "reviewer_id", "valid_from", "valid_until",
        }},
        "volume_deletion_terminal_handoff_id": "terminal-handoff-406",
        "terminal_volume_deletion_reconciliation_id": "terminal-reconciliation-406",
        "terminal_volume_deletion_finalization_id": "terminal-finalization-406",
        "volume_deletion_continuation_finalization_authorization_sha256": _hash(
            values["volume_deletion_continuation_finalization_file"],
        ),
        "volume_deletion_continuation_finalization_evidence_sha256": _hash(final_evidence),
        "terminal_volume_deletion_reconciliation_authorization_sha256": _hash(
            terminal_reconciliation,
        ),
        "terminal_volume_deletion_finalization_authorization_sha256": _hash(
            terminal_finalization,
        ),
        "operation": "handoff_disposable_postgres_volume_deletion_finalization",
        "executor_id": "handoff-executor",
        "authorizer_id": "handoff-authorizer",
        "reviewer_id": "handoff-reviewer",
        "valid_from": "2026-08-23T13:30:00Z",
        "valid_until": "2026-08-23T14:30:00Z",
    })
    return {
        "docker_executable": values["docker_executable"],
        "volume_disposition_file": values["volume_disposition_file"],
        "volume_deletion_file": values["volume_deletion_file"],
        "terminal_volume_deletion_reconciliation_file": terminal_reconciliation,
        "terminal_volume_deletion_finalization_file": terminal_finalization,
        "volume_deletion_continuation_file": values["volume_deletion_continuation_file"],
        "volume_deletion_continuation_finalization_file":
            values["volume_deletion_continuation_finalization_file"],
        "volume_deletion_terminal_handoff_file": authorization,
        "lineage_manifest_file": values["lineage_manifest_file"],
        "retention_decision_file": values["retention_decision_file"],
        "legal_hold_decision_file": values["legal_hold_decision_file"],
        "recovery_decision_file": values["recovery_decision_file"],
        "project_name": PROJECT, "evidence_directory": values["evidence_directory"],
        "processes": Processes([_observation()]), "clock": values["clock"],
    }, original_claim


@pytest.mark.parametrize("confirmed", [False, True])
def test_positive_lq404_evidence_finalizes_original_claim(
    tmp_path: Path, confirmed: bool,
) -> None:
    values, original_claim = _setup(tmp_path, confirmed=confirmed)
    result = handoff.handoff_disposable_postgres_volume_deletion_finalization(**values)
    assert json.loads(result)["outcome"] == "volume_deletion_finalized"
    assert not original_claim.exists()
    assert len(values["processes"].calls) == 1


def test_terminal_retry_uses_lq398_evidence_without_docker(tmp_path: Path) -> None:
    values, original_claim = _setup(tmp_path)
    handoff.handoff_disposable_postgres_volume_deletion_finalization(**values)
    assert not original_claim.exists()
    values["processes"] = Processes([])
    result = handoff.handoff_disposable_postgres_volume_deletion_finalization(**values)
    assert json.loads(result)["outcome"] == "volume_deletion_finalized"
    assert values["processes"].calls == []


def test_present_subclaim_requires_investigation_without_docker(tmp_path: Path) -> None:
    values, original_claim = _setup(tmp_path)
    _open_claim({
        **values,
        "volume_deletion_continuation_file": values["volume_deletion_continuation_file"],
    })
    values["processes"] = Processes([])
    result = handoff.handoff_disposable_postgres_volume_deletion_finalization(**values)
    assert json.loads(result)["outcome"] == "investigation_required"
    assert original_claim.exists() and values["processes"].calls == []


def test_missing_original_claim_requires_investigation(tmp_path: Path) -> None:
    values, original_claim = _setup(tmp_path)
    original_claim.unlink()
    values["processes"] = Processes([])
    result = handoff.handoff_disposable_postgres_volume_deletion_finalization(**values)
    assert json.loads(result)["outcome"] == "investigation_required"
    assert values["processes"].calls == []


def test_handoff_hash_mismatch_stops_before_lq398(tmp_path: Path) -> None:
    values, original_claim = _setup(tmp_path)
    current = json.loads(values["volume_deletion_terminal_handoff_file"].read_text())
    current["terminal_volume_deletion_finalization_authorization_sha256"] = "0" * 64
    _private(values["volume_deletion_terminal_handoff_file"], current)
    with pytest.raises(handoff.DisposablePostgresVolumeDeletionTerminalHandoffUnavailable):
        handoff.handoff_disposable_postgres_volume_deletion_finalization(**values)
    assert original_claim.exists() and values["processes"].calls == []


def test_nonterminal_lq398_outcome_is_investigation_required(
    tmp_path: Path, monkeypatch,
) -> None:
    values, original_claim = _setup(tmp_path)
    monkeypatch.setattr(
        handoff, "finalize_disposable_postgres_volume_deletion",
        lambda **_: b'{"operation":"disposable_postgres_volume_deletion_finalization",'
                     b'"outcome":"continuation_required","schema_version":1}\n',
    )
    result = handoff.handoff_disposable_postgres_volume_deletion_finalization(**values)
    assert json.loads(result)["outcome"] == "investigation_required"
    assert original_claim.exists()


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_volume_deletion_terminal_handoff",'
        b'"outcome":"volume_deletion_finalized","schema_version":1}\n'
    )
    monkeypatch.setattr(
        handoff, "handoff_disposable_postgres_volume_deletion_finalization",
        lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--volume-disposition-file", "/x/disposition",
        "--volume-deletion-file", "/x/deletion",
        "--terminal-volume-deletion-reconciliation-file", "/x/reconciliation",
        "--terminal-volume-deletion-finalization-file", "/x/finalization",
        "--volume-deletion-continuation-file", "/x/continuation",
        "--volume-deletion-continuation-finalization-file", "/x/continuation-final",
        "--volume-deletion-terminal-handoff-file", "/x/handoff",
        "--lineage-manifest-file", "/x/lineage",
        "--retention-decision-file", "/x/retention",
        "--legal-hold-decision-file", "/x/hold",
        "--recovery-decision-file", "/x/recovery",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert handoff.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert handoff.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_entry_point_is_installed() -> None:
    project = Path(__file__).parents[1] / "pyproject.toml"
    assert (
        'liquent-disposable-postgres-volume-delete-terminal-handoff = '
        '"liquent_platform.operators.disposable_postgres_volume_deletion_terminal_handoff:main"'
    ) in project.read_text()
