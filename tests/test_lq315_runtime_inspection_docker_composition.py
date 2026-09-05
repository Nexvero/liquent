from __future__ import annotations

import json
from pathlib import Path

import pytest

from liquent_platform.operators.staging_process_adapter import (
    FACT_KEYS, ProcessObservation,
)
from liquent_platform.operators.staging_read_only_probe_cli import (
    StagingReadOnlyProbeCliUnavailable, run_read_only_probe,
)
from test_lq312_staging_read_only_probe_cli import (
    APP_IMAGE, NOW, _compose_output, _setup,
)


class RuntimeProcesses:
    def __init__(self, phase: str, *, runtime_returncode: int = 0):
        self.phase, self.runtime_returncode, self.calls = phase, runtime_returncode, []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if len(self.calls) == 1:
            return ProcessObservation(0, _compose_output(), b"", False, False, False)
        value = {"schema_version": 1, "phase": self.phase,
                 "facts": {FACT_KEYS[self.phase]: True}}
        return ProcessObservation(
            self.runtime_returncode, json.dumps(value).encode(), b"",
            False, False, False,
        )


def _run(tmp_path: Path, phase: str, processes):
    docker, auth, compose, runtime, images = _setup(tmp_path)
    return run_read_only_probe(
        phase=phase, docker_executable=docker, authorization_file=auth,
        compose_file=compose, runtime_environment_file=runtime,
        image_environment_file=images, project_name="liquent-lq312-run",
        processes=processes, clock=lambda: NOW,
    )


@pytest.mark.parametrize("phase", ["entrypoint", "input_ownership", "data_read_only"])
def test_runtime_phase_renders_then_runs_exact_hardened_inspector(
    tmp_path: Path, phase: str,
) -> None:
    processes = RuntimeProcesses(phase)
    result = _run(tmp_path, phase, processes)
    assert result.status == "passed"
    assert len(processes.calls) == 2
    render, run = processes.calls
    assert render[0][1:3] == ("compose", "--env-file")
    argv, options = run
    assert argv[:5] == (str(tmp_path / "docker"), "run", "--rm", "--pull", "never")
    for required in (
        "--network", "none", "--read-only", "--user", "10001:10001",
        "--security-opt", "no-new-privileges", "--cap-drop", "ALL",
        "--pids-limit", "64", "--memory", "128m", "--cpus", "0.25",
        "--log-driver", "none", "--entrypoint",
        "/opt/liquent/venv/bin/liquent-runtime-inspect", "--phase", phase,
    ):
        assert required in argv
    mounts = [argv[index + 1] for index, item in enumerate(argv) if item == "--mount"]
    assert len(mounts) == 3
    assert all(item.endswith(",readonly") for item in mounts)
    joined = " ".join(argv)
    assert "/run/secrets" not in joined
    assert "/var/lib/liquent/artifacts" not in joined
    assert "database_url" not in joined
    assert options["environment"] == {"LANG": "C", "LC_ALL": "C"}
    assert options["maximum_output_bytes"] == 65_536


def test_runtime_container_name_is_stable_opaque_and_run_bound(tmp_path: Path) -> None:
    first, second = RuntimeProcesses("entrypoint"), RuntimeProcesses("entrypoint")
    _run(tmp_path, "entrypoint", first)
    name = first.calls[1][0][first.calls[1][0].index("--name") + 1]
    assert name.startswith("liquent-inspect-") and len(name) == 40
    # The second setup needs a separate root but the same run ID.
    other = tmp_path / "other"
    other.mkdir()
    _run(other, "entrypoint", second)
    assert second.calls[1][0][second.calls[1][0].index("--name") + 1] == name


def test_static_mismatch_stops_before_inspection_container(tmp_path: Path) -> None:
    class Mismatch(RuntimeProcesses):
        def run(self, argv, **kwargs):
            observation = super().run(argv, **kwargs)
            if len(self.calls) == 1:
                value = json.loads(observation.stdout)
                value["services"]["research-worker"]["networks"] = {"public": None}
                return ProcessObservation(0, json.dumps(value).encode(), b"", False, False, False)
            return observation

    processes = Mismatch("entrypoint")
    with pytest.raises(StagingReadOnlyProbeCliUnavailable):
        _run(tmp_path, "entrypoint", processes)
    assert len(processes.calls) == 1


def test_unknown_container_effect_is_unavailable_without_retry(tmp_path: Path) -> None:
    processes = RuntimeProcesses("entrypoint", runtime_returncode=1)
    with pytest.raises(StagingReadOnlyProbeCliUnavailable) as caught:
        _run(tmp_path, "entrypoint", processes)
    assert str(caught.value) == "staging_read_only_probe_cli_unavailable"
    assert caught.value.__cause__ is None
    assert len(processes.calls) == 2


def test_unsafe_or_duplicate_bind_source_stops_before_container(tmp_path: Path) -> None:
    class Unsafe(RuntimeProcesses):
        def run(self, argv, **kwargs):
            observation = super().run(argv, **kwargs)
            if len(self.calls) == 1:
                value = json.loads(observation.stdout)
                value["services"]["research-worker"]["volumes"][0]["source"] = "/unsafe,option"
                return ProcessObservation(0, json.dumps(value).encode(), b"", False, False, False)
            return observation

    processes = Unsafe("input_ownership")
    with pytest.raises(StagingReadOnlyProbeCliUnavailable):
        _run(tmp_path, "input_ownership", processes)
    assert len(processes.calls) == 1
