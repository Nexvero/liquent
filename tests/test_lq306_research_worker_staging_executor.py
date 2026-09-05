from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from liquent_platform.operators.research_worker_staging_evidence import verify_staging_evidence
from liquent_platform.operators.research_worker_staging_executor import (
    PHASES, StagingExecutorUnavailable, StagingPhaseEvidence,
    execute_staging_run, load_staging_run_authorization,
)
from liquent_platform.persistence.migrations import expected_head


NOW = datetime(2026, 8, 19, 12, tzinfo=UTC)


def _authorization(**changes: object) -> dict[str, object]:
    value = {
        "schema_version": 1, "run_id": "lq306-run", "environment": "staging",
        "source_commit": "a" * 40,
        "image_ref": "registry.example/liquent@sha256:" + "b" * 64,
        "compose_sha256": "c" * 64, "migration_head": expected_head(),
        "executor_id": "executor-306", "authorizer_id": "authorizer-306",
        "valid_from": "2026-08-19T11:00:00Z",
        "valid_until": "2026-08-20T11:00:00Z",
    }
    value.update(changes)
    return value


def _private(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _load(tmp_path: Path, **changes: object):
    return load_staging_run_authorization(
        _private(tmp_path / "authorization.json", _authorization(**changes)),
        clock=lambda: NOW,
    )


class Runner:
    def __init__(self, stop_phase: str | None = None, status: str = "failed"):
        self.stop_phase, self.status, self.calls = stop_phase, status, []

    def run(self, phase, authorization):
        self.calls.append((phase, authorization.run_id))
        if phase == self.stop_phase:
            if self.status == "unavailable":
                raise RuntimeError("private process output")
            return StagingPhaseEvidence("failed", "evidence:failed", "f" * 64)
        index = PHASES.index(phase) + 1
        return StagingPhaseEvidence("passed", f"evidence:{index}", f"{index:064x}")


def _output(tmp_path: Path) -> Path:
    output = tmp_path / "evidence"
    output.mkdir(mode=0o700)
    return output


def test_all_phases_run_once_in_fixed_order_and_output_verifies(tmp_path: Path) -> None:
    authorization, runner = _load(tmp_path), Runner()
    result = execute_staging_run(
        authorization, runner, _output(tmp_path), clock=lambda: NOW,
    )
    assert [phase for phase, _ in runner.calls] == list(PHASES)
    assert result.name == "lq306-run.json"
    assert oct(result.stat().st_mode & 0o777) == "0o600"
    assert verify_staging_evidence(result, clock=lambda: NOW) == "approved"


@pytest.mark.parametrize("status", ["failed", "unavailable"])
def test_first_non_passed_phase_stops_calls_and_marks_remainder_unavailable(
    tmp_path: Path, status: str,
) -> None:
    runner = Runner("migration_gate", status)
    result = execute_staging_run(_load(tmp_path), runner, _output(tmp_path), clock=lambda: NOW)
    record = json.loads(result.read_text())
    stop = PHASES.index("migration_gate")
    assert [phase for phase, _ in runner.calls] == list(PHASES[: stop + 1])
    expected = "failed" if status == "failed" else "unavailable"
    assert record["checks"]["migration_gate"]["status"] == expected
    assert all(record["checks"][phase] == {
        "status": "unavailable", "evidence_ref": None, "evidence_sha256": None,
    } for phase in PHASES[stop + 1:])
    decision = verify_staging_evidence(result, clock=lambda: NOW)
    assert decision == ("rejected" if status == "failed" else "unavailable")


@pytest.mark.parametrize("changes", [
    {"environment": "production"}, {"image_ref": "liquent:latest"},
    {"migration_head": "old"}, {"authorizer_id": "executor-306"},
    {"valid_from": "2026-08-19T13:00:00Z"},
    {"valid_until": "2026-08-19T11:00:00Z"},
])
def test_authorization_is_closed_current_and_staging_only(tmp_path: Path, changes) -> None:
    with pytest.raises(StagingExecutorUnavailable) as caught:
        _load(tmp_path, **changes)
    assert str(caught.value) == "research_worker_staging_executor_unavailable"
    assert caught.value.__cause__ is None


def test_output_must_be_private_empty_and_is_never_overwritten(tmp_path: Path) -> None:
    authorization = _load(tmp_path)
    broad = tmp_path / "broad"
    broad.mkdir(mode=0o755)
    with pytest.raises(StagingExecutorUnavailable):
        execute_staging_run(authorization, Runner(), broad, clock=lambda: NOW)
    output = _output(tmp_path)
    existing = output / "existing"
    existing.write_text("retained")
    with pytest.raises(StagingExecutorUnavailable):
        execute_staging_run(authorization, Runner(), output, clock=lambda: NOW)
    assert existing.read_text() == "retained"


def test_invalid_runner_result_becomes_unavailable_without_detail(tmp_path: Path) -> None:
    class Invalid:
        def run(self, *_): return {"status": "passed", "private": "detail"}

    result = execute_staging_run(_load(tmp_path), Invalid(), _output(tmp_path), clock=lambda: NOW)
    record = json.loads(result.read_text())
    assert all(item["status"] == "unavailable" for item in record["checks"].values())
    assert "private" not in result.read_text()
