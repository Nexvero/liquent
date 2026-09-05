from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from liquent_platform.operators.staging_process_adapter import ProcessObservation
from liquent_platform.operators.staging_read_only_probe_cli import (
    StagingReadOnlyProbeCliUnavailable,
)
from test_lq312_staging_read_only_probe_cli import APP_IMAGE, _compose_output
from test_lq315_runtime_inspection_docker_composition import RuntimeProcesses, _run


PHASE = "artifact_capabilities"


def test_artifact_phase_runs_one_hardened_write_probe(tmp_path: Path) -> None:
    processes = RuntimeProcesses(PHASE)
    result = _run(tmp_path, PHASE, processes)
    assert result.status == "passed"
    assert len(processes.calls) == 2
    argv, options = processes.calls[1]
    assert argv[:5] == (str(tmp_path / "docker"), "run", "--rm", "--pull", "never")
    assert argv[argv.index("--network") + 1] == "none"
    assert "--read-only" in argv
    assert argv[argv.index("--user") + 1] == "10001:10001"
    assert argv[argv.index("--security-opt") + 1] == "no-new-privileges"
    assert argv[argv.index("--cap-drop") + 1] == "ALL"
    mounts = [argv[index + 1] for index, value in enumerate(argv) if value == "--mount"]
    assert mounts == [
        "type=volume,source=artifacts,target=/var/lib/liquent/artifacts",
    ]
    assert argv[argv.index("--entrypoint") + 1] == (
        "/opt/liquent/venv/bin/liquent-artifact-capability-inspect"
    )
    token = argv[argv.index("--run-token") + 1]
    assert token == hashlib.sha256(
        b"liquent-lq312-run:artifact_capabilities"
    ).hexdigest()
    joined = " ".join(argv)
    for forbidden in (
        "/run/secrets", "/run/liquent/research-worker.json",
        "/run/liquent/research-worker-id", "/var/lib/liquent/research-data",
        "database_url", "--env", "--publish", "--privileged", "--device",
    ):
        assert forbidden not in joined
    assert options["environment"] == {"LANG": "C", "LC_ALL": "C"}
    assert options["maximum_output_bytes"] == 65_536


def test_token_and_container_are_stable_and_phase_bound(tmp_path: Path) -> None:
    first = RuntimeProcesses(PHASE)
    _run(tmp_path, PHASE, first)
    argv = first.calls[1][0]
    name = argv[argv.index("--name") + 1]
    assert name.startswith("liquent-inspect-") and len(name) == 40
    other = tmp_path / "other"
    other.mkdir()
    second = RuntimeProcesses(PHASE)
    _run(other, PHASE, second)
    second_argv = second.calls[1][0]
    assert second_argv[second_argv.index("--name") + 1] == name
    assert second_argv[second_argv.index("--run-token") + 1] == (
        argv[argv.index("--run-token") + 1]
    )


def test_invalid_or_read_only_artifact_volume_stops_before_write_container(
    tmp_path: Path,
) -> None:
    class Unsafe(RuntimeProcesses):
        def run(self, argv, **kwargs):
            observation = super().run(argv, **kwargs)
            if len(self.calls) == 1:
                value = json.loads(observation.stdout)
                volume = value["services"]["research-worker"]["volumes"][3]
                volume["source"] = "unsafe,option"
                return ProcessObservation(
                    0, json.dumps(value).encode(), b"", False, False, False,
                )
            return observation

    processes = Unsafe(PHASE)
    with pytest.raises(StagingReadOnlyProbeCliUnavailable):
        _run(tmp_path, PHASE, processes)
    assert len(processes.calls) == 1


def test_static_mismatch_stops_before_write_container(tmp_path: Path) -> None:
    class Mismatch(RuntimeProcesses):
        def run(self, argv, **kwargs):
            observation = super().run(argv, **kwargs)
            if len(self.calls) == 1:
                value = json.loads(observation.stdout)
                value["services"]["research-worker"]["networks"] = {"public": None}
                return ProcessObservation(
                    0, json.dumps(value).encode(), b"", False, False, False,
                )
            return observation

    processes = Mismatch(PHASE)
    with pytest.raises(StagingReadOnlyProbeCliUnavailable):
        _run(tmp_path, PHASE, processes)
    assert len(processes.calls) == 1


def test_unknown_write_effect_is_unavailable_without_retry_or_cleanup(
    tmp_path: Path,
) -> None:
    processes = RuntimeProcesses(PHASE, runtime_returncode=2)
    with pytest.raises(StagingReadOnlyProbeCliUnavailable) as caught:
        _run(tmp_path, PHASE, processes)
    assert str(caught.value) == "staging_read_only_probe_cli_unavailable"
    assert caught.value.__cause__ is None
    assert len(processes.calls) == 2
    assert all(value not in processes.calls[1][0] for value in ("stop", "rm", "down"))
