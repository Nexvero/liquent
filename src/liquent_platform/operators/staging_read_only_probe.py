"""Closed reduction of read-only image and rendered Compose observations."""

from __future__ import annotations

import json
import re

from liquent_platform.operators.research_worker_staging_executor import (
    StagingRunAuthorization,
)
from liquent_platform.operators.staging_process_adapter import ReducedPhaseOutput


SUPPORTED_PHASES = frozenset({
    "image_digest", "image_revision", "runtime_identity", "trading_disabled",
    "compose_render", "command", "networks", "mounts", "secret_mount", "grace",
})
IMAGE = re.compile(r"[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}\Z")


class StagingReadOnlyProbeUnavailable(Exception):
    code = "staging_read_only_probe_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise StagingReadOnlyProbeUnavailable
        result[key] = value
    return result


def _json(raw: bytes, maximum: int):
    if type(raw) is not bytes or not raw or len(raw) > maximum:
        raise StagingReadOnlyProbeUnavailable
    try:
        return json.loads(raw, object_pairs_hook=_pairs)
    except StagingReadOnlyProbeUnavailable:
        raise
    except Exception:
        raise StagingReadOnlyProbeUnavailable from None


def _worker(model: object) -> dict:
    if type(model) is not dict or type(model.get("services")) is not dict:
        raise StagingReadOnlyProbeUnavailable
    services = model["services"]
    required = {
        "migration-gate", "control-plane", "research-worker", "postgres",
        "prometheus", "grafana", "backup",
    }
    if not required.issubset(services) or type(services["research-worker"]) is not dict:
        raise StagingReadOnlyProbeUnavailable
    return services["research-worker"]


def _image_fact(phase: str, authorization: StagingRunAuthorization, raw: bytes) -> bool:
    value = _json(raw, 1_048_576)
    if type(value) is not list or len(value) != 1 or type(value[0]) is not dict:
        raise StagingReadOnlyProbeUnavailable
    inspection = value[0]
    config = inspection.get("Config")
    if type(config) is not dict:
        raise StagingReadOnlyProbeUnavailable
    if phase == "image_digest":
        digests = inspection.get("RepoDigests")
        return (
            type(digests) is list
            and all(type(item) is str and IMAGE.fullmatch(item) for item in digests)
            and authorization.image_ref in digests
        )
    if phase == "image_revision":
        labels = config.get("Labels")
        return type(labels) is dict and labels.get(
            "org.opencontainers.image.revision"
        ) == authorization.source_commit
    user = config.get("User")
    return user in {"10001", "10001:10001"}


def _volume_map(worker: dict) -> dict[str, tuple[str, bool]]:
    volumes = worker.get("volumes")
    if type(volumes) is not list:
        raise StagingReadOnlyProbeUnavailable
    result = {}
    for volume in volumes:
        if type(volume) is not dict or set(volume) - {
            "type", "source", "target", "read_only", "bind", "volume",
            "consistency",
        }:
            raise StagingReadOnlyProbeUnavailable
        target, kind, read_only = volume.get("target"), volume.get("type"), volume.get("read_only", False)
        if type(target) is not str or kind not in {"bind", "volume"} or type(read_only) is not bool:
            raise StagingReadOnlyProbeUnavailable
        if target in result:
            raise StagingReadOnlyProbeUnavailable
        result[target] = (kind, read_only)
    return result


def _compose_fact(phase: str, raw: bytes) -> bool:
    model = _json(raw, 2_097_152)
    worker = _worker(model)
    if phase == "compose_render":
        return True
    if phase == "command":
        return worker.get("command") == [
            "liquent-research-worker", "--configuration",
            "/run/liquent/research-worker.json", "--database-url-file",
            "/run/secrets/database_url",
        ]
    if phase == "networks":
        networks = worker.get("networks")
        return type(networks) is dict and set(networks) == {
            "application", "data", "observability",
        }
    if phase == "mounts":
        volumes = _volume_map(worker)
        return volumes == {
            "/run/liquent/research-worker.json": ("bind", True),
            "/run/liquent/research-worker-id": ("bind", True),
            "/var/lib/liquent/research-data": ("bind", True),
            "/var/lib/liquent/artifacts": ("volume", False),
        }
    if phase == "secret_mount":
        secrets = worker.get("secrets")
        return type(secrets) is list and secrets == [{
            "source": "database_url", "target": "database_url",
            "uid": "10001", "gid": "10001", "mode": 256,
        }]
    if phase == "grace":
        return worker.get("stop_grace_period") in {"60s", "1m", "1m0s", 60_000_000_000}
    environment = worker.get("environment")
    return type(environment) is dict and (
        environment.get("LIQUENT_JOB_CONCURRENCY") in {1, "1"}
        and environment.get("LIQUENT_TRADING_CONNECTIVITY") == "disabled"
        and not any(term in key.upper() for key in environment for term in (
            "BROKER", "EXCHANGE", "API_KEY", "API_SECRET", "LIVE_TRADING",
        ))
    )


def evaluate_read_only_phase(
    phase: str,
    authorization: StagingRunAuthorization,
    *,
    image_inspection: bytes | None = None,
    compose_model: bytes | None = None,
) -> ReducedPhaseOutput:
    """Evaluate one supported observation without accepting an allow boolean."""

    try:
        if phase not in SUPPORTED_PHASES or type(authorization) is not StagingRunAuthorization:
            raise StagingReadOnlyProbeUnavailable
        if phase in {"image_digest", "image_revision", "runtime_identity"}:
            if image_inspection is None or compose_model is not None:
                raise StagingReadOnlyProbeUnavailable
            result = _image_fact(phase, authorization, image_inspection)
        else:
            if compose_model is None or image_inspection is not None:
                raise StagingReadOnlyProbeUnavailable
            result = _compose_fact(phase, compose_model)
        fact = {
            "image_digest": "digest_matches", "image_revision": "revision_matches",
            "runtime_identity": "uid_gid_matches", "trading_disabled": "trading_disabled",
            "compose_render": "render_valid", "command": "command_exact",
            "networks": "networks_isolated", "mounts": "mounts_bounded",
            "secret_mount": "secret_owner_only", "grace": "grace_bounded",
        }[phase]
        content = (json.dumps({
            "schema_version": 1, "phase": phase, "facts": {fact: result},
        }, sort_keys=True, separators=(",", ":")) + "\n").encode()
        return ReducedPhaseOutput(phase, "passed" if result else "failed", content)
    except StagingReadOnlyProbeUnavailable:
        raise
    except Exception:
        raise StagingReadOnlyProbeUnavailable from None
