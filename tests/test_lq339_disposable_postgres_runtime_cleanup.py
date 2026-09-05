from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import liquent_platform.operators.disposable_postgres_runtime_cleanup as cleanup
from liquent_platform.operators.staging_process_adapter import ProcessObservation
from tests.test_lq330_disposable_postgres_composition import _inspection, _model
from tests.test_lq331_disposable_postgres_reconciliation import (
    CONTAINER, NETWORKS, PROJECT, VOLUME, _volume,
)
from tests.test_lq337_disposable_postgres_cleanup_preflight import _inputs


class Processes:
    def __init__(self, values):
        self.values, self.calls = list(values), []

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return self.values.pop(0)


def _observation(
    stdout: bytes = b"", *, timed_out: bool = False, stderr: bytes = b"",
) -> ProcessObservation:
    return ProcessObservation(0, stdout, stderr, timed_out, False, False)


def _network(name: str, *, extra: bool = False) -> bytes:
    containers = {"container-id": {"Name": CONTAINER}}
    if extra:
        containers["foreign-id"] = {"Name": "foreign-service"}
    return json.dumps([{
        "Name": name, "Internal": True,
        "Labels": {"com.docker.compose.project": PROJECT},
        "Containers": containers,
    }]).encode()


def _stopped() -> bytes:
    return json.dumps([{
        "Name": f"/{CONTAINER}",
        "State": {"Running": False, "Status": "exited"},
    }]).encode()


def _successful_processes(*, extra_endpoint: bool = False) -> Processes:
    return Processes([
        _observation(_model()), _observation(_inspection()),
        _observation(_network(NETWORKS[0], extra=extra_endpoint)),
        _observation(_network(NETWORKS[1])), _observation(_volume()),
        _observation(), _observation(_stopped()), _observation(), _observation(),
        _observation(), _observation(), _observation(), _observation(),
        _observation(_volume()),
    ])


def _runtime_inputs(tmp_path: Path, processes: Processes, *, scope="runtime_only"):
    values = _inputs(tmp_path, scope=scope)
    values["processes"] = processes
    return values


@pytest.fixture(autouse=True)
def ready_preflight(monkeypatch):
    monkeypatch.setattr(
        cleanup, "preflight_disposable_postgres_cleanup",
        lambda **_: (
            b'{"operation":"disposable_postgres_cleanup_preflight",'
            b'"outcome":"ready","schema_version":1}\n'
        ),
    )


def test_exact_runtime_cleanup_is_ordered_and_retains_volume(tmp_path: Path) -> None:
    processes = _successful_processes()
    values = _runtime_inputs(tmp_path, processes)
    result = cleanup.cleanup_disposable_postgres_runtime(**values)
    assert json.loads(result)["outcome"] == "removed_runtime"
    mutation = [call[0][1:] for call in processes.calls[5:]]
    assert mutation == [
        ("container", "stop", "--time", "30", CONTAINER),
        ("container", "inspect", CONTAINER),
        ("container", "rm", CONTAINER),
        ("container", "ls", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Names}}"),
        ("network", "rm", NETWORKS[0]),
        ("network", "ls", "--filter", f"name=^{NETWORKS[0]}$", "--format", "{{.Name}}"),
        ("network", "rm", NETWORKS[1]),
        ("network", "ls", "--filter", f"name=^{NETWORKS[1]}$", "--format", "{{.Name}}"),
        ("volume", "inspect", VOLUME),
    ]
    assert not any("--force" in call[0] or "--volumes" in call[0] for call in processes.calls)
    stem = hashlib.sha256(b"cleanup-337").hexdigest()
    evidence = values["evidence_directory"] / f"postgres-cleanup-{stem}.json"
    claim = values["evidence_directory"] / f".postgres-cleanup-{stem}.claim"
    assert json.loads(evidence.read_text())["outcome"] == "removed_runtime"
    assert not claim.exists()


def test_additional_network_endpoint_is_rejected_before_claim(tmp_path: Path) -> None:
    processes = _successful_processes(extra_endpoint=True)
    values = _runtime_inputs(tmp_path, processes)
    result = cleanup.cleanup_disposable_postgres_runtime(**values)
    assert json.loads(result)["outcome"] == "rejected"
    assert len(processes.calls) == 5
    assert list(values["evidence_directory"].glob(".postgres-cleanup-*.claim")) == []


def test_unknown_first_effect_retains_claim_without_retry(tmp_path: Path) -> None:
    processes = _successful_processes()
    processes.values[5] = _observation(timed_out=True)
    values = _runtime_inputs(tmp_path, processes)
    with pytest.raises(cleanup.DisposablePostgresRuntimeCleanupUnavailable):
        cleanup.cleanup_disposable_postgres_runtime(**values)
    assert len(processes.calls) == 6
    claims = list(values["evidence_directory"].glob(".postgres-cleanup-*.claim"))
    assert len(claims) == 1
    retry = Processes([])
    values["processes"] = retry
    with pytest.raises(cleanup.DisposablePostgresRuntimeCleanupUnavailable):
        cleanup.cleanup_disposable_postgres_runtime(**values)
    assert retry.calls == []


def test_exact_final_retry_returns_without_docker(tmp_path: Path) -> None:
    values = _runtime_inputs(tmp_path, _successful_processes())
    expected = cleanup.cleanup_disposable_postgres_runtime(**values)
    retry = Processes([])
    values["processes"] = retry
    assert cleanup.cleanup_disposable_postgres_runtime(**values) == expected
    assert retry.calls == []


def test_non_runtime_scope_stops_before_preflight_or_docker(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        cleanup, "preflight_disposable_postgres_cleanup",
        lambda **_: pytest.fail("preflight must not run"),
    )
    processes = Processes([])
    values = _runtime_inputs(tmp_path, processes, scope="runtime_and_data_volume")
    with pytest.raises(cleanup.DisposablePostgresRuntimeCleanupUnavailable):
        cleanup.cleanup_disposable_postgres_runtime(**values)
    assert processes.calls == []


def test_neutral_preflight_outcomes_do_not_create_claim(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        cleanup, "preflight_disposable_postgres_cleanup",
        lambda **_: (
            b'{"operation":"disposable_postgres_cleanup_preflight",'
            b'"outcome":"already_absent","schema_version":1}\n'
        ),
    )
    processes = Processes([])
    values = _runtime_inputs(tmp_path, processes)
    result = cleanup.cleanup_disposable_postgres_runtime(**values)
    assert json.loads(result)["outcome"] == "already_absent"
    assert processes.calls == []
    assert list(values["evidence_directory"].glob(".postgres-cleanup-*.claim")) == []


def test_cli_emits_only_canonical_result_or_nothing(monkeypatch, capsys) -> None:
    expected = (
        b'{"operation":"disposable_postgres_runtime_cleanup",'
        b'"outcome":"removed_runtime","schema_version":1}\n'
    )
    monkeypatch.setattr(cleanup, "cleanup_disposable_postgres_runtime", lambda **_: expected)
    arguments = [
        "--docker-executable", "/x/docker", "--authorization-file", "/x/auth",
        "--reconciliation-file", "/x/recon",
        "--claim-reconciliation-file", "/x/claim-recon",
        "--disposition-file", "/x/disposition", "--cleanup-file", "/x/cleanup",
        "--staging-evidence-file", "/x/staging", "--compose-file", "/x/compose",
        "--runtime-env-file", "/x/runtime", "--image-env-file", "/x/images",
        "--project-name", PROJECT, "--evidence-directory", "/x/evidence",
    ]
    assert cleanup.main(arguments) == 0
    assert capsys.readouterr().out.encode() == expected
    assert cleanup.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
