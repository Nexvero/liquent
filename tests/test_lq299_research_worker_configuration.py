import json
import os
from pathlib import Path

import pytest

from liquent_platform.identity.research import ResearchWorkerId
from liquent_platform.operators.research_worker_configuration import (
    OwnerOnlyResearchWorkerIdSource,
    ResearchWorkerConfigurationUnavailable,
    load_research_worker_configuration,
)


def _private(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)
    return path


def _values(tmp_path: Path):
    return {
        "worker_id_path": str(tmp_path / "worker-id"),
        "research_data_root": str(tmp_path / "data"),
        "artifact_root": str(tmp_path / "artifacts"),
        "lease_seconds": 60,
        "idle_wait_seconds": 2,
        "unavailable_initial_wait_seconds": 1,
        "unavailable_max_wait_seconds": 30,
        "jitter_max_seconds": 0.5,
        "job_concurrency": 1,
        "trading_connectivity": "disabled",
    }


def test_exact_owner_only_configuration_loads_closed_policy(tmp_path: Path):
    values = _values(tmp_path)
    path = _private(tmp_path / "worker.json", json.dumps(values))
    configuration = load_research_worker_configuration(path)
    assert configuration.worker_id_path == tmp_path / "worker-id"
    assert configuration.lease_seconds == 60
    assert configuration.loop_policy.idle_wait_seconds == 2
    assert configuration.job_concurrency == 1
    assert configuration.trading_connectivity == "disabled"
    assert str(tmp_path) not in repr(configuration)


@pytest.mark.parametrize("change", [
    {"job_concurrency": 2}, {"job_concurrency": True},
    {"trading_connectivity": "paper"}, {"lease_seconds": 4},
    {"lease_seconds": 3601}, {"worker_id_path": "relative"},
    {"idle_wait_seconds": 0}, {"unavailable_max_wait_seconds": 0.5},
])
def test_configuration_rejects_expansion_and_unbounded_values(tmp_path: Path, change):
    values = _values(tmp_path)
    values.update(change)
    path = _private(tmp_path / "worker.json", json.dumps(values))
    with pytest.raises(ResearchWorkerConfigurationUnavailable):
        load_research_worker_configuration(path)


def test_configuration_rejects_missing_unknown_and_duplicate_keys(tmp_path: Path):
    values = _values(tmp_path)
    del values["artifact_root"]
    with pytest.raises(ResearchWorkerConfigurationUnavailable):
        load_research_worker_configuration(_private(tmp_path / "missing", json.dumps(values)))
    values = _values(tmp_path)
    values["command"] = "anything"
    with pytest.raises(ResearchWorkerConfigurationUnavailable):
        load_research_worker_configuration(_private(tmp_path / "unknown", json.dumps(values)))
    raw = json.dumps(_values(tmp_path))[:-1] + ',"lease_seconds":60}'
    with pytest.raises(ResearchWorkerConfigurationUnavailable):
        load_research_worker_configuration(_private(tmp_path / "duplicate", raw))


def test_worker_id_is_stable_exact_and_optional_single_newline_is_removed(tmp_path: Path):
    path = _private(tmp_path / "worker-id", "worker-prod-01\n")
    source = OwnerOnlyResearchWorkerIdSource(path)
    assert source.load() == ResearchWorkerId("worker-prod-01")
    assert source.load() == ResearchWorkerId("worker-prod-01")
    assert repr(source) == "OwnerOnlyResearchWorkerIdSource()"
    assert str(path) not in repr(source)


@pytest.mark.parametrize("value", ["", " worker", "worker ", "two\nlines", "x" * 129, "worker/one"])
def test_worker_id_rejects_empty_ambiguous_or_path_like_values(tmp_path: Path, value: str):
    path = _private(tmp_path / "worker-id", value)
    with pytest.raises(ResearchWorkerConfigurationUnavailable):
        OwnerOnlyResearchWorkerIdSource(path).load()


def test_private_files_reject_symlink_loose_mode_and_hardlink(tmp_path: Path):
    target = _private(tmp_path / "target", "worker-1")
    symlink = tmp_path / "symlink"
    symlink.symlink_to(target)
    with pytest.raises(ResearchWorkerConfigurationUnavailable):
        OwnerOnlyResearchWorkerIdSource(symlink).load()
    os.chmod(target, 0o644)
    with pytest.raises(ResearchWorkerConfigurationUnavailable):
        OwnerOnlyResearchWorkerIdSource(target).load()
    os.chmod(target, 0o600)
    hardlink = tmp_path / "hardlink"
    os.link(target, hardlink)
    with pytest.raises(ResearchWorkerConfigurationUnavailable):
        OwnerOnlyResearchWorkerIdSource(target).load()


def test_no_hostname_pid_or_environment_fallback(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LIQUENT_RESEARCH_WORKER_ID", "environment-worker")
    missing = tmp_path / "missing"
    with pytest.raises(ResearchWorkerConfigurationUnavailable):
        OwnerOnlyResearchWorkerIdSource(missing).load()
