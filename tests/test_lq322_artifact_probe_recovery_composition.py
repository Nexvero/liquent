from __future__ import annotations

import json
from pathlib import Path

import pytest

from liquent_platform.operators.artifact_probe_recovery import (
    ArtifactProbeRecoveryUnavailable, recover_artifact_probe,
)
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from test_lq312_staging_read_only_probe_cli import APP_IMAGE, NOW, _compose_output, _setup, _private


class Processes:
    def __init__(self, inspected: str, removed: str = "removed"):
        self.inspected, self.removed, self.calls = inspected, removed, []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if len(self.calls) == 1:
            output = _compose_output()
        elif len(self.calls) == 2:
            output = json.dumps({
                "schema_version": 1, "inspection": "artifact_probe_recovery",
                "outcome": self.inspected,
            }).encode()
        else:
            output = json.dumps({
                "schema_version": 1, "operation": "artifact_probe_recovery_remove",
                "outcome": self.removed,
            }).encode()
        return ProcessObservation(0, output, b"", False, False, False)


def _run(tmp_path: Path, processes, *, mismatch: bool = False):
    docker, authorization, compose, runtime, images = _setup(tmp_path)
    recovery = {
        "schema_version": 1, "recovery_id": "recovery-322",
        "run_id": "other" if mismatch else "lq312-run",
        "phase": "artifact_capabilities", "source_commit": "a" * 40,
        "image_ref": APP_IMAGE,
        "compose_sha256": json.loads(authorization.read_text())["compose_sha256"],
        "executor_id": "recovery-executor", "authorizer_id": "recovery-authorizer",
        "valid_from": "2026-08-20T13:30:00Z", "valid_until": "2026-08-20T14:30:00Z",
    }
    recovery_file = _private(tmp_path / "recovery.json", json.dumps(recovery))
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700, exist_ok=True)
    return recover_artifact_probe(
        docker_executable=docker, authorization_file=authorization,
        recovery_file=recovery_file, compose_file=compose,
        runtime_environment_file=runtime, image_environment_file=images,
        project_name="liquent-lq312-run", processes=processes, clock=lambda: NOW,
        evidence_directory=evidence,
    )


@pytest.mark.parametrize("inspected,expected", [
    ("absent", "already_absent"), ("conflict", "conflict"),
])
def test_nonrecoverable_inspection_never_starts_write_container(
    tmp_path: Path, inspected: str, expected: str,
) -> None:
    processes = Processes(inspected)
    output = json.loads(_run(tmp_path, processes))
    assert output["outcome"] == expected
    assert len(processes.calls) == 2
    inspect_argv = processes.calls[1][0]
    mounts = [inspect_argv[index + 1] for index, value in enumerate(inspect_argv) if value == "--mount"]
    assert mounts == ["type=volume,source=artifacts,target=/var/lib/liquent/artifacts,readonly"]


def test_recoverable_runs_exact_read_only_then_write_sequence(tmp_path: Path) -> None:
    processes = Processes("recoverable", "removed")
    assert json.loads(_run(tmp_path, processes))["outcome"] == "removed"
    assert len(processes.calls) == 3
    inspect, remove = processes.calls[1][0], processes.calls[2][0]
    assert inspect[inspect.index("--entrypoint") + 1].endswith("recovery-inspect")
    assert remove[remove.index("--entrypoint") + 1].endswith("recovery-remove")
    inspect_mount = inspect[inspect.index("--mount") + 1]
    remove_mount = remove[remove.index("--mount") + 1]
    assert inspect_mount.endswith(",readonly") and not remove_mount.endswith(",readonly")
    assert inspect[inspect.index("--run-token") + 1] == remove[remove.index("--run-token") + 1]
    for argv in (inspect, remove):
        joined = " ".join(argv)
        assert "--network none" in joined and "--read-only" in argv
        assert "/run/secrets" not in joined and "/var/lib/liquent/research-data" not in joined


def test_recovery_binding_mismatch_stops_before_docker(tmp_path: Path) -> None:
    processes = Processes("recoverable")
    with pytest.raises(ArtifactProbeRecoveryUnavailable) as caught:
        _run(tmp_path, processes, mismatch=True)
    assert str(caught.value) == "artifact_probe_recovery_unavailable"
    assert processes.calls == []


def test_unknown_inspection_or_remove_is_not_retried(tmp_path: Path) -> None:
    class Unknown(Processes):
        def run(self, argv, **kwargs):
            value = super().run(argv, **kwargs)
            if len(self.calls) == 3:
                return ProcessObservation(2, b"", b"", False, False, False)
            return value

    processes = Unknown("recoverable")
    with pytest.raises(ArtifactProbeRecoveryUnavailable):
        _run(tmp_path, processes)
    assert len(processes.calls) == 3
    retry = Processes("recoverable")
    with pytest.raises(ArtifactProbeRecoveryUnavailable):
        _run(tmp_path, retry)
    assert retry.calls == []


def test_exact_completed_retry_reads_evidence_without_docker(tmp_path: Path) -> None:
    first = Processes("recoverable", "removed")
    expected = _run(tmp_path, first)
    second = Processes("conflict")
    assert _run(tmp_path, second) == expected
    assert second.calls == []
    evidence = tmp_path / "evidence"
    files = [path for path in evidence.iterdir() if path.suffix == ".json"]
    assert len(files) == 1
    assert files[0].stat().st_mode & 0o777 == 0o600
