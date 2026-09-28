from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

import liquent_platform.operators.staging_read_only_probe_cli as cli
from tests.test_lq312_staging_read_only_probe_cli import Processes, _setup


NOW = datetime(2026, 8, 20, 14, tzinfo=UTC)


def _private(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.chmod(path, 0o600)
    return path


def _rollback_files(tmp_path: Path, *, source_commit: str = "a" * 40):
    candidate = "registry.example/liquent@sha256:" + "b" * 64
    previous = "registry.example/liquent@sha256:" + "9" * 64
    evidence = _private(tmp_path / "rollback-evidence.json", {
        "schema_version": 1, "environment": "staging",
        "source_commit": source_commit, "candidate_image_ref": candidate,
        "previous_healthy_image_ref": previous,
        "rollback_target_image_ref": previous,
        "backup_snapshot_ref": "snapshot-329",
        "backup_evidence_sha256": "d" * 64,
        "restore_evidence_sha256": "e" * 64,
        "created_at": "2026-08-20T13:00:00Z",
        "verified_at": "2026-08-20T13:30:00Z",
        "valid_until": "2026-08-20T15:00:00Z",
        "prepared_by": "operator-329", "reviewed_by": "reviewer-329",
        "status": "verified",
    })
    expectation = _private(tmp_path / "rollback-expectation.json", {
        "schema_version": 1, "run_id": "lq312-run", "environment": "staging",
        "source_commit": "a" * 40, "candidate_image_ref": candidate,
        "rollback_evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        "executor_id": "executor-312", "authorizer_id": "authorizer-312",
        "valid_from": "2026-08-20T13:00:00Z",
        "valid_until": "2026-08-20T15:00:00Z",
    })
    return expectation, evidence


def _run(tmp_path: Path, expectation: Path, evidence: Path, processes: Processes):
    docker, authorization, compose, runtime, images = _setup(tmp_path)
    return cli.run_read_only_probe(
        phase="rollback", docker_executable=docker,
        authorization_file=authorization, compose_file=compose,
        runtime_environment_file=runtime, image_environment_file=images,
        project_name="liquent-lq312-run",
        rollback_expectation_file=expectation,
        rollback_evidence_file=evidence, processes=processes, clock=lambda: NOW,
    )


def test_current_bound_rollback_evidence_passes_without_process(tmp_path: Path) -> None:
    expectation, evidence = _rollback_files(tmp_path)
    processes = Processes(b"must not run")
    result = _run(tmp_path, expectation, evidence, processes)
    assert result.status == "passed"
    assert result.content == (
        b'{"facts":{"rollback_current":true},"phase":"rollback",'
        b'"schema_version":1}\n'
    )
    assert processes.calls == []


def test_semantic_evidence_mismatch_is_neutral_failed(tmp_path: Path) -> None:
    expectation, evidence = _rollback_files(tmp_path, source_commit="f" * 40)
    result = _run(tmp_path, expectation, evidence, Processes(b"must not run"))
    assert result.status == "failed"
    assert json.loads(result.content)["facts"] == {"rollback_current": False}


def test_expectation_must_match_staging_authorization(tmp_path: Path) -> None:
    expectation, evidence = _rollback_files(tmp_path)
    value = json.loads(expectation.read_text())
    value["run_id"] = "other-run"
    _private(expectation, value)
    result = _run(tmp_path, expectation, evidence, Processes(b"must not run"))
    assert result.status == "failed"


@pytest.mark.parametrize("missing", ["expectation", "evidence"])
def test_both_rollback_inputs_are_required_before_process(
    tmp_path: Path, missing: str,
) -> None:
    expectation, evidence = _rollback_files(tmp_path)
    docker, authorization, compose, runtime, images = _setup(tmp_path)
    processes = Processes(b"must not run")
    with pytest.raises(cli.StagingReadOnlyProbeCliUnavailable):
        cli.run_read_only_probe(
            phase="rollback", docker_executable=docker,
            authorization_file=authorization, compose_file=compose,
            runtime_environment_file=runtime, image_environment_file=images,
            project_name="liquent-lq312-run",
            rollback_expectation_file=None if missing == "expectation" else expectation,
            rollback_evidence_file=None if missing == "evidence" else evidence,
            processes=processes, clock=lambda: NOW,
        )
    assert processes.calls == []


def test_other_phase_rejects_rollback_inputs(tmp_path: Path) -> None:
    expectation, evidence = _rollback_files(tmp_path)
    docker, authorization, compose, runtime, images = _setup(tmp_path)
    processes = Processes(b"must not run")
    with pytest.raises(cli.StagingReadOnlyProbeCliUnavailable):
        cli.run_read_only_probe(
            phase="compose_render", docker_executable=docker,
            authorization_file=authorization, compose_file=compose,
            runtime_environment_file=runtime, image_environment_file=images,
            project_name="liquent-lq312-run",
            rollback_expectation_file=expectation,
            rollback_evidence_file=evidence, processes=processes, clock=lambda: NOW,
        )
    assert processes.calls == []
