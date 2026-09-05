from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from liquent_platform.operators.research_worker_staging_executor import (
    PHASES, StagingRunAuthorization,
)
from liquent_platform.operators.staging_phase_composition import (
    FixedStagingPhaseCommands, PrivateStagingEvidenceObjectSink,
    StagingPhaseCompositionUnavailable, StagingProcessInputs,
    compose_staging_phase_runner,
)
from liquent_platform.operators.staging_process_adapter import (
    FACT_KEYS, ProcessObservation, ReducedPhaseOutput,
)
from liquent_platform.persistence.migrations import expected_head


NOW = datetime(2026, 8, 20, 10, tzinfo=UTC)


def _authorization() -> StagingRunAuthorization:
    return StagingRunAuthorization(
        "lq309-run", "a" * 40,
        "registry.example/liquent@sha256:" + "b" * 64, "c" * 64,
        expected_head(), "executor-309", "authorizer-309", NOW, NOW,
    )


def _file(path: Path, mode: int, content: str = "value\n") -> Path:
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)
    return path


def _inputs(tmp_path: Path) -> StagingProcessInputs:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    return StagingProcessInputs(
        _file(tmp_path / "probe", 0o700), _file(tmp_path / "docker", 0o700),
        work, _file(tmp_path / "authorization.json", 0o600),
        _file(tmp_path / "compose.yaml", 0o644),
        _file(tmp_path / "runtime.env", 0o600),
        _file(tmp_path / "images.env", 0o400),
    )


def _evidence_root(tmp_path: Path) -> Path:
    root = tmp_path / "objects"
    root.mkdir(mode=0o700)
    return root


class Processes:
    def __init__(self): self.calls = []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        phase = argv[argv.index("--phase") + 1]
        value = {"schema_version": 1, "phase": phase,
                 "facts": {FACT_KEYS[phase]: True}}
        return ProcessObservation(0, json.dumps(value).encode(), b"", False, False, False)


def test_commands_are_fixed_run_bound_and_environment_closed(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    commands = FixedStagingPhaseCommands(inputs)
    request = commands.request("compose_render", _authorization())
    assert request.argv == (
        str(inputs.probe_executable), "--phase", "compose_render",
        "--docker-executable", str(inputs.docker_executable),
        "--authorization-file", str(inputs.authorization_file),
        "--compose-file", str(inputs.compose_file),
        "--runtime-env-file", str(inputs.runtime_environment_file),
        "--image-env-file", str(inputs.image_environment_file),
        "--project-name", "liquent-lq309-run",
    )
    assert request.environment == {"LANG": "C", "LC_ALL": "C"}
    assert request.timeout_seconds == 60.0
    assert request.maximum_output_bytes == 65_536
    assert repr(inputs) == "StagingProcessInputs()"
    assert repr(request) == "StagingProcessRequest()"


def test_mutating_phase_has_fixed_longer_timeout_without_other_changes(tmp_path: Path) -> None:
    commands = FixedStagingPhaseCommands(_inputs(tmp_path))
    assert commands.request("migration_gate", _authorization()).timeout_seconds == 300.0
    with pytest.raises(StagingPhaseCompositionUnavailable):
        commands.request("unknown", _authorization())


def test_private_environment_files_and_empty_work_directory_fail_closed(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    os.chmod(inputs.runtime_environment_file, 0o644)
    with pytest.raises(StagingPhaseCompositionUnavailable):
        FixedStagingPhaseCommands(inputs).request("image_digest", _authorization())
    os.chmod(inputs.runtime_environment_file, 0o600)
    (inputs.working_directory / "unexpected").write_text("x")
    with pytest.raises(StagingPhaseCompositionUnavailable):
        FixedStagingPhaseCommands(inputs).request("image_digest", _authorization())


def test_sink_writes_private_atomic_hash_verified_object_once(tmp_path: Path) -> None:
    root = _evidence_root(tmp_path)
    sink = PrivateStagingEvidenceObjectSink(root)
    reduced = ReducedPhaseOutput(
        "image_digest", "passed",
        b'{"facts":{"digest_matches":true},"phase":"image_digest","schema_version":1}\n',
    )
    result = sink.store(reduced)
    objects = list(root.iterdir())
    assert len(objects) == 1 and objects[0].suffix == ".json"
    assert stat_mode(objects[0]) == 0o600
    assert result.status == "passed"
    assert result.evidence_ref == f"evidence:{result.evidence_sha256}"
    with pytest.raises(StagingPhaseCompositionUnavailable):
        sink.store(reduced)
    assert len(list(root.iterdir())) == 1


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def test_composition_runs_reduce_store_for_all_phases_without_real_processes(tmp_path: Path) -> None:
    processes = Processes()
    root = _evidence_root(tmp_path)
    runner = compose_staging_phase_runner(_inputs(tmp_path), root, processes=processes)
    results = [runner.run(phase, _authorization()) for phase in PHASES]
    assert all(result.status == "passed" for result in results)
    assert len(processes.calls) == len(PHASES)
    assert len(list(root.iterdir())) == len(PHASES)
    assert repr(runner) == "ComposedStagingPhaseRunner()"


def test_process_or_parser_failure_creates_no_evidence_object(tmp_path: Path) -> None:
    class Broken:
        def run(self, *_args, **_kwargs):
            return ProcessObservation(1, b"private", b"detail", False, False, False)

    root = _evidence_root(tmp_path)
    runner = compose_staging_phase_runner(_inputs(tmp_path), root, processes=Broken())
    with pytest.raises(StagingPhaseCompositionUnavailable) as caught:
        runner.run("image_digest", _authorization())
    assert str(caught.value) == "staging_phase_composition_unavailable"
    assert caught.value.__cause__ is None
    assert list(root.iterdir()) == []
