from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_reconcile as reconcile
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from tests.test_lq312_staging_read_only_probe_cli import _setup
from tests.test_lq330_disposable_postgres_composition import (
    POSTGRES_IMAGE, PROJECT, _inspection, _model,
)


NOW = datetime(2026, 8, 20, 14, tzinfo=UTC)
CONTAINER = f"{PROJECT}-postgres-1"
NETWORKS = (f"{PROJECT}-application", f"{PROJECT}-data")
VOLUME = f"{PROJECT}-postgres-data"


def _observation(stdout: bytes = b"", *, timed_out: bool = False):
    return ProcessObservation(0, stdout, b"", timed_out, False, False)


class Processes:
    def __init__(self, values):
        self.values, self.calls = list(values), []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.values.pop(0)


def _private(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.chmod(path, 0o600)
    return path


def _reconciliation(tmp_path: Path, **changes) -> Path:
    value = {
        "schema_version": 1, "reconciliation_id": "reconcile-331",
        "run_id": "lq312-run", "phase": "disposable_postgres",
        "source_commit": "a" * 40,
        "image_ref": "registry.example/liquent@sha256:" + "b" * 64,
        "compose_sha256": "placeholder", "executor_id": "executor-331",
        "authorizer_id": "authorizer-331",
        "valid_from": "2026-08-20T13:30:00Z",
        "valid_until": "2026-08-20T14:30:00Z",
    }
    value.update(changes)
    return _private(tmp_path / "reconciliation.json", value)


def _inputs(tmp_path: Path, processes: Processes, **changes):
    docker, authorization, compose, runtime, images = _setup(tmp_path)
    auth = json.loads(authorization.read_text())
    reconciliation_file = _reconciliation(
        tmp_path, compose_sha256=auth["compose_sha256"], **changes,
    )
    return dict(
        docker_executable=docker, authorization_file=authorization,
        reconciliation_file=reconciliation_file, compose_file=compose,
        runtime_environment_file=runtime, image_environment_file=images,
        project_name=PROJECT, processes=processes, clock=lambda: NOW,
    )


def _network(name: str, *, project: str = PROJECT) -> bytes:
    return json.dumps([{
        "Name": name, "Internal": True,
        "Labels": {"com.docker.compose.project": project},
    }]).encode()


def _volume(*, project: str = PROJECT) -> bytes:
    return json.dumps([{
        "Name": VOLUME, "Labels": {"com.docker.compose.project": project},
    }]).encode()


def test_all_bound_resources_absent_is_neutral_and_read_only(tmp_path: Path) -> None:
    processes = Processes([_observation(_model()), *[_observation() for _ in range(4)]])
    result = reconcile.reconcile_disposable_postgres(**_inputs(tmp_path, processes))
    assert json.loads(result)["outcome"] == "absent"
    assert len(processes.calls) == 5
    assert not any(set(call[0]) & {"up", "down", "rm", "remove", "prune"} for call in processes.calls)


def test_partial_resource_set_is_conflict_without_inspect(tmp_path: Path) -> None:
    processes = Processes([
        _observation(_model()), _observation((CONTAINER + "\n").encode()),
        _observation(), _observation(), _observation(),
    ])
    result = reconcile.reconcile_disposable_postgres(**_inputs(tmp_path, processes))
    assert json.loads(result)["outcome"] == "conflict"
    assert len(processes.calls) == 5


def test_complete_exact_isolated_set_is_classified_read_only(tmp_path: Path) -> None:
    present = [CONTAINER, *NETWORKS, VOLUME]
    processes = Processes([
        _observation(_model()),
        *[_observation((name + "\n").encode()) for name in present],
        _observation(_inspection()),
        _observation(_network(NETWORKS[0])),
        _observation(_network(NETWORKS[1])), _observation(_volume()),
    ])
    result = reconcile.reconcile_disposable_postgres(**_inputs(tmp_path, processes))
    assert result == (
        b'{"inspection":"disposable_postgres_reconciliation",'
        b'"outcome":"isolated","schema_version":1}\n'
    )
    assert all(call[1]["timeout_seconds"] == 60.0 for call in processes.calls)


def test_wrong_resource_ownership_is_conflict(tmp_path: Path) -> None:
    present = [CONTAINER, *NETWORKS, VOLUME]
    processes = Processes([
        _observation(_model()),
        *[_observation((name + "\n").encode()) for name in present],
        _observation(_inspection()),
        _observation(_network(NETWORKS[0], project="other")),
        _observation(_network(NETWORKS[1])), _observation(_volume()),
    ])
    result = reconcile.reconcile_disposable_postgres(**_inputs(tmp_path, processes))
    assert json.loads(result)["outcome"] == "conflict"


def test_stale_or_mismatched_reconciliation_stops_before_docker(tmp_path: Path) -> None:
    processes = Processes([])
    with pytest.raises(reconcile.DisposablePostgresReconcileUnavailable):
        reconcile.reconcile_disposable_postgres(**_inputs(
            tmp_path, processes, run_id="other-run",
        ))
    assert processes.calls == []


def test_technical_list_or_inspect_ambiguity_is_unavailable(tmp_path: Path) -> None:
    processes = Processes([_observation(_model()), _observation(timed_out=True)])
    with pytest.raises(reconcile.DisposablePostgresReconcileUnavailable):
        reconcile.reconcile_disposable_postgres(**_inputs(tmp_path, processes))
    assert len(processes.calls) == 2


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"inspection":"disposable_postgres_reconciliation",'
        b'"outcome":"absent","schema_version":1}\n'
    )
    monkeypatch.setattr(
        reconcile, "reconcile_disposable_postgres_with_evidence", lambda **_: expected,
    )
    arguments = [
        "--docker-executable", "/x/docker", "--authorization-file", "/x/auth",
        "--reconciliation-file", "/x/reconcile", "--compose-file", "/x/compose",
        "--runtime-env-file", "/x/runtime", "--image-env-file", "/x/images",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert reconcile.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert reconcile.main(["--project-name", PROJECT]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
