"""Owner-controlled closed configuration for the research-worker process."""

from __future__ import annotations

import json
import math
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path

from liquent_platform.identity.research import ResearchWorkerId
from liquent_platform.operators.research_worker_loop import ResearchWorkerLoopPolicy


_WORKER_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_CONFIG_KEYS = {
    "worker_id_path", "research_data_root", "artifact_root", "lease_seconds",
    "idle_wait_seconds", "unavailable_initial_wait_seconds",
    "unavailable_max_wait_seconds", "jitter_max_seconds", "job_concurrency",
    "trading_connectivity",
}


class ResearchWorkerConfigurationUnavailable(Exception):
    code = "research_worker_configuration_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class ResearchWorkerProcessConfiguration:
    worker_id_path: Path = field(repr=False)
    research_data_root: Path = field(repr=False)
    artifact_root: Path = field(repr=False)
    lease_seconds: float
    loop_policy: ResearchWorkerLoopPolicy
    job_concurrency: int = 1
    trading_connectivity: str = "disabled"

    def __post_init__(self) -> None:
        for path in (self.worker_id_path, self.research_data_root, self.artifact_root):
            if not isinstance(path, Path) or not path.is_absolute():
                raise ValueError("research worker paths must be absolute")
        if (
            type(self.lease_seconds) not in (int, float)
            or not math.isfinite(self.lease_seconds)
            or not 5 <= self.lease_seconds <= 3600
        ):
            raise ValueError("research worker lease must be between 5 and 3600 seconds")
        if type(self.job_concurrency) is not int or self.job_concurrency != 1:
            raise ValueError("research worker concurrency must be one")
        if type(self.trading_connectivity) is not str or self.trading_connectivity != "disabled":
            raise ValueError("research worker trading connectivity must be disabled")


class OwnerOnlyResearchWorkerIdSource:
    __slots__ = ("_path",)

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path) or not path.is_absolute():
            raise ValueError("research worker id path must be absolute")
        self._path = path

    def __repr__(self) -> str:
        return "OwnerOnlyResearchWorkerIdSource()"

    def load(self) -> ResearchWorkerId:
        try:
            raw = _private_file(self._path, 129)
            if raw.endswith(b"\n"):
                raw = raw[:-1]
            value = raw.decode("utf-8")
            if _WORKER_ID.fullmatch(value) is None:
                raise ResearchWorkerConfigurationUnavailable
            return ResearchWorkerId(value)
        except ResearchWorkerConfigurationUnavailable:
            raise
        except Exception:
            raise ResearchWorkerConfigurationUnavailable from None


def load_research_worker_configuration(path: Path) -> ResearchWorkerProcessConfiguration:
    """Load one exact owner-only JSON document without environment fallback."""

    try:
        raw = _private_file(path, 8192)

        def pairs(values):
            result = {}
            for key, value in values:
                if key in result:
                    raise ResearchWorkerConfigurationUnavailable
                result[key] = value
            return result

        values = json.loads(raw, object_pairs_hook=pairs)
        if type(values) is not dict or set(values) != _CONFIG_KEYS:
            raise ResearchWorkerConfigurationUnavailable
        paths = {
            name: Path(values[name])
            for name in ("worker_id_path", "research_data_root", "artifact_root")
            if type(values[name]) is str
        }
        if len(paths) != 3:
            raise ResearchWorkerConfigurationUnavailable
        policy = ResearchWorkerLoopPolicy(
            values["idle_wait_seconds"],
            values["unavailable_initial_wait_seconds"],
            values["unavailable_max_wait_seconds"],
            values["jitter_max_seconds"],
        )
        return ResearchWorkerProcessConfiguration(
            paths["worker_id_path"], paths["research_data_root"],
            paths["artifact_root"], values["lease_seconds"], policy,
            values["job_concurrency"], values["trading_connectivity"],
        )
    except ResearchWorkerConfigurationUnavailable:
        raise
    except Exception:
        raise ResearchWorkerConfigurationUnavailable from None


def _private_file(path: Path, maximum: int) -> bytes:
    descriptor: int | None = None
    try:
        if not isinstance(path, Path) or not path.is_absolute():
            raise ResearchWorkerConfigurationUnavailable
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) not in {0o400, 0o600}
            or not 0 < metadata.st_size <= maximum
        ):
            raise ResearchWorkerConfigurationUnavailable
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        result = b"".join(chunks)
        if not result or len(result) > maximum:
            raise ResearchWorkerConfigurationUnavailable
        return result
    except ResearchWorkerConfigurationUnavailable:
        raise
    except Exception:
        raise ResearchWorkerConfigurationUnavailable from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
