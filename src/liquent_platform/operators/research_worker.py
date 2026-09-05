"""Owner-controlled entry point for the persistent research worker."""

from __future__ import annotations

import argparse
import secrets
import signal
import threading
from datetime import timedelta
from pathlib import Path

from liquent_platform.application.health import Readiness
from liquent_platform.application.local_csv import LocalCsvMidBreakoutV0Resolver
from liquent_platform.identity.research import (
    JobId, ResearchJobClaimId, ResearchJobRevisionId,
)
from liquent_platform.operators.research_worker_composition import compose_research_worker
from liquent_platform.operators.research_worker_configuration import (
    OwnerOnlyResearchWorkerIdSource, ResearchWorkerConfigurationUnavailable,
    _private_file, load_research_worker_configuration,
)
from liquent_platform.operators.research_worker_loop import ResearchWorkerLoop
from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.persistence.research_artifacts import (
    LocalImmutableResearchArtifactStore, ResearchArtifactStoreUnavailable,
)


class ResearchWorkerOperatorUnavailable(Exception):
    code = "research_worker_operator_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OwnerOnlyResearchWorkerDatabaseUrlSource:
    __slots__ = ("_path",)

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path) or not path.is_absolute():
            raise ValueError("research worker database URL path must be absolute")
        self._path = path

    def __repr__(self) -> str:
        return "OwnerOnlyResearchWorkerDatabaseUrlSource()"

    def load(self) -> str:
        try:
            raw = _private_file(self._path, 4096)
            if raw.endswith(b"\n"):
                raw = raw[:-1]
            value = raw.decode("utf-8")
            if not value.startswith("postgresql+psycopg://") or any(
                character.isspace() for character in value
            ):
                raise ResearchWorkerOperatorUnavailable
            return value
        except ResearchWorkerOperatorUnavailable:
            raise
        except Exception:
            raise ResearchWorkerOperatorUnavailable from None


def _identifier(identifier_type):
    return identifier_type(secrets.token_urlsafe(32))


def run_research_worker(
    configuration_path: Path,
    database_url_path: Path,
    *,
    stop_event: threading.Event | None = None,
    install_signal_handlers: bool = True,
) -> int:
    """Validate, compose, and run until an external or process stop request."""

    engine = None
    previous = {}
    event = stop_event or threading.Event()
    try:
        configuration = load_research_worker_configuration(configuration_path)
        worker_id = OwnerOnlyResearchWorkerIdSource(
            configuration.worker_id_path
        ).load()
        database_url = OwnerOnlyResearchWorkerDatabaseUrlSource(
            database_url_path
        ).load()
        engine = build_engine(database_url)
        readiness: Readiness = DatabaseReadinessProbe(engine).check()
        if not readiness.ready:
            raise ResearchWorkerOperatorUnavailable

        resolver = LocalCsvMidBreakoutV0Resolver(configuration.research_data_root)
        artifacts = LocalImmutableResearchArtifactStore(configuration.artifact_root)
        composition = compose_research_worker(
            engine=engine,
            resolver=resolver,
            artifacts=artifacts,
            generate_job_id=lambda: _identifier(JobId),
            generate_revision_id=lambda: _identifier(ResearchJobRevisionId),
            generate_claim_id=lambda: _identifier(ResearchJobClaimId),
            lease_duration=timedelta(seconds=configuration.lease_seconds),
        )
        random = secrets.SystemRandom()
        loop = ResearchWorkerLoop(
            composition.processor,
            worker_id,
            configuration.loop_policy,
            jitter=lambda maximum: random.uniform(0.0, maximum),
        )

        if install_signal_handlers:
            def request_stop(_signum, _frame):
                event.set()
            for name in (signal.SIGTERM, signal.SIGINT):
                previous[name] = signal.signal(name, request_stop)

        loop.run(stop_requested=event.is_set, wait=event.wait)
        return 0
    except (
        ResearchWorkerConfigurationUnavailable,
        ResearchArtifactStoreUnavailable,
        ResearchWorkerOperatorUnavailable,
    ):
        raise ResearchWorkerOperatorUnavailable from None
    except Exception:
        raise ResearchWorkerOperatorUnavailable from None
    finally:
        for name, handler in previous.items():
            signal.signal(name, handler)
        if engine is not None:
            engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="liquent-research-worker")
    parser.add_argument("--configuration", required=True, type=Path)
    parser.add_argument("--database-url-file", required=True, type=Path)
    arguments = parser.parse_args(argv)
    try:
        return run_research_worker(
            arguments.configuration,
            arguments.database_url_file,
        )
    except ResearchWorkerOperatorUnavailable:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
