from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from liquent_platform.operators.research_worker_staging_executor import StagingRunAuthorization
from liquent_platform.operators.staging_read_only_probe import (
    SUPPORTED_PHASES, StagingReadOnlyProbeUnavailable, evaluate_read_only_phase,
)
from liquent_platform.persistence.migrations import expected_head


NOW = datetime(2026, 8, 20, 12, tzinfo=UTC)


def _authorization() -> StagingRunAuthorization:
    return StagingRunAuthorization(
        "lq311-run", "a" * 40,
        "registry.example/liquent@sha256:" + "b" * 64, "c" * 64,
        expected_head(), "executor-311", "authorizer-311", NOW, NOW,
    )


def _image(**changes) -> bytes:
    value = [{
        "RepoDigests": [_authorization().image_ref],
        "Config": {"User": "10001:10001", "Labels": {
            "org.opencontainers.image.revision": _authorization().source_commit,
        }},
    }]
    value[0].update(changes)
    return json.dumps(value).encode()


def _compose(worker_changes=None) -> bytes:
    worker = {
        "command": [
            "liquent-research-worker", "--configuration",
            "/run/liquent/research-worker.json", "--database-url-file",
            "/run/secrets/database_url",
        ],
        "networks": {"application": None, "data": None, "observability": None},
        "volumes": [
            {"type": "bind", "source": "/private/config", "target": "/run/liquent/research-worker.json", "read_only": True, "bind": {"create_host_path": True}},
            {"type": "bind", "source": "/private/id", "target": "/run/liquent/research-worker-id", "read_only": True, "bind": {"create_host_path": True}},
            {"type": "bind", "source": "/private/data", "target": "/var/lib/liquent/research-data", "read_only": True, "bind": {"create_host_path": True}},
            {"type": "volume", "source": "liquent_artifacts", "target": "/var/lib/liquent/artifacts", "read_only": False, "volume": {}},
        ],
        "secrets": [{"source": "database_url", "target": "database_url", "uid": "10001", "gid": "10001", "mode": 256}],
        "stop_grace_period": "1m0s",
        "environment": {"LIQUENT_JOB_CONCURRENCY": "1", "LIQUENT_TRADING_CONNECTIVITY": "disabled"},
    }
    if worker_changes:
        worker.update(worker_changes)
    services = {name: {} for name in (
        "migration-gate", "control-plane", "postgres", "prometheus", "grafana", "backup",
    )}
    services["research-worker"] = worker
    return json.dumps({"name": "liquent-lq311", "services": services}).encode()


@pytest.mark.parametrize("phase", ["image_digest", "image_revision", "runtime_identity"])
def test_image_phases_derive_passed_fact_from_raw_inspection(phase: str) -> None:
    result = evaluate_read_only_phase(phase, _authorization(), image_inspection=_image())
    assert result.status == "passed"
    assert json.loads(result.content)["phase"] == phase


@pytest.mark.parametrize("phase", sorted(SUPPORTED_PHASES - {
    "image_digest", "image_revision", "runtime_identity",
}))
def test_compose_phases_derive_passed_fact_from_raw_rendered_model(phase: str) -> None:
    result = evaluate_read_only_phase(phase, _authorization(), compose_model=_compose())
    assert result.status == "passed"
    assert list(json.loads(result.content)["facts"].values()) == [True]


def test_digest_revision_and_runtime_mismatch_are_explicit_failed() -> None:
    wrong_digest = _image(RepoDigests=["registry.example/other@sha256:" + "d" * 64])
    assert evaluate_read_only_phase("image_digest", _authorization(), image_inspection=wrong_digest).status == "failed"
    wrong_revision = _image()
    value = json.loads(wrong_revision)
    value[0]["Config"]["Labels"]["org.opencontainers.image.revision"] = "d" * 40
    assert evaluate_read_only_phase("image_revision", _authorization(), image_inspection=json.dumps(value).encode()).status == "failed"
    wrong_user = _image()
    value = json.loads(wrong_user)
    value[0]["Config"]["User"] = "0:0"
    assert evaluate_read_only_phase("runtime_identity", _authorization(), image_inspection=json.dumps(value).encode()).status == "failed"


@pytest.mark.parametrize("phase,change", [
    ("command", {"command": ["other"]}),
    ("networks", {"networks": {"public": None, "application": None}}),
    ("mounts", {"volumes": []}),
    ("secret_mount", {"secrets": [{"source": "database_url", "target": "database_url", "mode": 292}]}),
    ("grace", {"stop_grace_period": "30s"}),
    ("trading_disabled", {"environment": {"LIQUENT_JOB_CONCURRENCY": "2", "LIQUENT_TRADING_CONNECTIVITY": "disabled"}}),
])
def test_compose_invariant_mismatch_is_explicit_failed(phase: str, change: dict) -> None:
    assert evaluate_read_only_phase(
        phase, _authorization(), compose_model=_compose(change)
    ).status == "failed"


def test_unknown_mutating_or_unproved_entrypoint_phases_are_unavailable() -> None:
    for phase in ("entrypoint", "migration_gate", "artifact_capabilities", "running_sigterm"):
        with pytest.raises(StagingReadOnlyProbeUnavailable):
            evaluate_read_only_phase(phase, _authorization(), compose_model=_compose())


def test_malformed_duplicate_oversized_or_mixed_observation_is_unavailable() -> None:
    with pytest.raises(StagingReadOnlyProbeUnavailable):
        evaluate_read_only_phase("compose_render", _authorization(), compose_model=b'{"services":{},"services":{}}')
    with pytest.raises(StagingReadOnlyProbeUnavailable):
        evaluate_read_only_phase("compose_render", _authorization(), compose_model=b"x" * 2_097_153)
    with pytest.raises(StagingReadOnlyProbeUnavailable):
        evaluate_read_only_phase(
            "image_digest", _authorization(), image_inspection=_image(), compose_model=_compose()
        )


def test_reduced_output_contains_no_private_rendered_values() -> None:
    result = evaluate_read_only_phase("mounts", _authorization(), compose_model=_compose())
    assert b"/private/" not in result.content
    assert b"database_url" not in result.content
    assert b"liquent_artifacts" not in result.content
