from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from liquent_platform.operators.research_worker_staging_executor import PHASES
from liquent_platform.operators.staging_process_adapter import (
    FACT_KEYS, LocalBoundedProcessRunner, ProcessObservation,
    StagingProcessUnavailable, reduce_phase_output,
)


def _run(tmp_path: Path, source: str, **changes) -> ProcessObservation:
    values = {
        "cwd": tmp_path, "environment": {"LC_ALL": "C"},
        "timeout_seconds": 2.0, "maximum_output_bytes": 4096,
        "terminate_grace_seconds": 0.2,
    }
    values.update(changes)
    return LocalBoundedProcessRunner().run((sys.executable, "-c", source), **values)


def _observation(phase: str, result: bool = True) -> ProcessObservation:
    value = {
        "schema_version": 1, "phase": phase,
        "facts": {FACT_KEYS[phase]: result},
    }
    return ProcessObservation(0, json.dumps(value).encode(), b"", False, False, False)


def test_runner_uses_explicit_environment_and_separate_bounded_channels(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "import os,sys;sys.stdout.write(os.environ.get('LC_ALL','missing'));"
        "sys.stderr.write('separate')",
    )
    assert result.returncode == 0
    assert result.stdout == b"C" and result.stderr == b"separate"
    assert not result.timed_out and not result.truncated and not result.hard_killed
    assert repr(result) == "ProcessObservation()"


def test_output_limit_terminates_and_marks_result_unavailable_for_reduction(tmp_path: Path) -> None:
    result = _run(tmp_path, "import sys;sys.stdout.write('x'*10000)", maximum_output_bytes=64)
    assert result.truncated and len(result.stdout) == 64
    with pytest.raises(StagingProcessUnavailable):
        reduce_phase_output("image_digest", result)


def test_timeout_terminates_process_without_claiming_success(tmp_path: Path) -> None:
    result = _run(tmp_path, "import time;time.sleep(5)", timeout_seconds=0.05)
    assert result.timed_out and result.returncode != 0
    with pytest.raises(StagingProcessUnavailable):
        reduce_phase_output("idle_start", result)


def test_ignored_terminate_requires_hard_kill_and_is_observable(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(5)",
        timeout_seconds=0.1, terminate_grace_seconds=0.05,
    )
    assert result.timed_out and result.hard_killed


@pytest.mark.parametrize("phase", PHASES)
def test_every_phase_has_one_exact_boolean_fact_and_neutral_canonical_output(phase: str) -> None:
    passed = reduce_phase_output(phase, _observation(phase, True))
    failed = reduce_phase_output(phase, _observation(phase, False))
    assert passed.status == "passed" and failed.status == "failed"
    assert passed.phase == phase and repr(passed) == "ReducedPhaseOutput()"
    assert json.loads(passed.content) == {
        "schema_version": 1, "phase": phase, "facts": {FACT_KEYS[phase]: True},
    }


@pytest.mark.parametrize("observation", [
    ProcessObservation(1, b"{}", b"", False, False, False),
    ProcessObservation(0, b"{}", b"private error", False, False, False),
    ProcessObservation(0, b'{"schema_version":1,"phase":"image_digest","facts":{"digest_matches":true},"extra":1}', b"", False, False, False),
    ProcessObservation(0, b'{"schema_version":1,"phase":"image_digest","phase":"image_digest","facts":{"digest_matches":true}}', b"", False, False, False),
    ProcessObservation(0, b'{"schema_version":1,"phase":"image_digest","facts":{"digest_matches":"true"}}', b"", False, False, False),
    ProcessObservation(0, b'{"schema_version":1,"phase":"image_digest","facts":{"digest_matches":true},"url":"https://private.example"}', b"", False, False, False),
])
def test_nonzero_stderr_unknown_duplicate_typed_or_private_output_is_unavailable(observation) -> None:
    with pytest.raises(StagingProcessUnavailable) as caught:
        reduce_phase_output("image_digest", observation)
    assert str(caught.value) == "staging_process_unavailable"
    assert caught.value.__cause__ is None


def test_runner_rejects_relative_executable_and_invalid_limits_before_start(tmp_path: Path) -> None:
    runner = LocalBoundedProcessRunner()
    with pytest.raises(StagingProcessUnavailable):
        runner.run(("python", "-V"), cwd=tmp_path, environment={},
                   timeout_seconds=1, maximum_output_bytes=10)
    with pytest.raises(StagingProcessUnavailable):
        runner.run((sys.executable, "-V"), cwd=tmp_path, environment={},
                   timeout_seconds=0, maximum_output_bytes=10)
