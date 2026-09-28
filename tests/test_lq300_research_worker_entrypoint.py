import json
import signal
import threading
from pathlib import Path

import pytest

import liquent_platform.operators.research_worker as operator
from liquent_platform.application.health import Readiness
from liquent_platform.operators.research_worker import (
    OwnerOnlyResearchWorkerDatabaseUrlSource,
    ResearchWorkerOperatorUnavailable,
)


def _private(path: Path, value: str):
    path.write_text(value)
    path.chmod(0o600)
    return path


def _inputs(tmp_path: Path):
    data, artifacts = tmp_path / "data", tmp_path / "artifacts"
    data.mkdir(mode=0o700); artifacts.mkdir(mode=0o700)
    worker_id = _private(tmp_path / "worker-id", "worker-entry\n")
    config = {
        "worker_id_path": str(worker_id), "research_data_root": str(data),
        "artifact_root": str(artifacts), "lease_seconds": 60,
        "idle_wait_seconds": 2, "unavailable_initial_wait_seconds": 1,
        "unavailable_max_wait_seconds": 30, "jitter_max_seconds": 0.5,
        "job_concurrency": 1, "trading_connectivity": "disabled",
    }
    configuration = _private(tmp_path / "worker.json", json.dumps(config))
    database = _private(tmp_path / "database-url", "postgresql+psycopg://worker@db/liquent\n")
    return configuration, database


def test_database_url_source_is_owner_only_postgresql_and_repr_safe(tmp_path: Path):
    path = _private(tmp_path / "database", "postgresql+psycopg://worker@db/liquent\n")
    source = OwnerOnlyResearchWorkerDatabaseUrlSource(path)
    assert source.load() == "postgresql+psycopg://worker@db/liquent"
    assert repr(source) == "OwnerOnlyResearchWorkerDatabaseUrlSource()"
    assert str(path) not in repr(source)
    _private(path, "sqlite:///local.db")
    with pytest.raises(ResearchWorkerOperatorUnavailable): source.load()


def test_entrypoint_checks_readiness_composes_runs_and_disposes(tmp_path: Path, monkeypatch):
    configuration, database = _inputs(tmp_path)
    calls = []
    class Engine:
        def dispose(self): calls.append("dispose")
    engine = Engine()
    monkeypatch.setattr(operator, "build_engine", lambda value: calls.append(("engine", value)) or engine)
    class Probe:
        def __init__(self, candidate): assert candidate is engine
        def check(self): calls.append("readiness"); return Readiness(True, "database_ready")
    monkeypatch.setattr(operator, "DatabaseReadinessProbe", Probe)
    monkeypatch.setattr(operator, "LocalCsvMidBreakoutV0Resolver", lambda path: calls.append(("resolver", path)) or object())
    monkeypatch.setattr(operator, "LocalImmutableResearchArtifactStore", lambda path: calls.append(("artifacts", path)) or object())
    class Composition: processor = object()
    monkeypatch.setattr(operator, "compose_research_worker", lambda **values: calls.append("compose") or Composition())
    class Loop:
        def __init__(self, *args, **kwargs): calls.append("loop")
        def run(self, *, stop_requested, wait): calls.append("run"); return object()
    monkeypatch.setattr(operator, "ResearchWorkerLoop", Loop)
    assert operator.run_research_worker(configuration, database, stop_event=threading.Event(), install_signal_handlers=False) == 0
    assert calls[-2:] == ["run", "dispose"]
    assert calls.index("readiness") < calls.index("compose") < calls.index("run")


def test_unready_database_starts_nothing_and_disposes(tmp_path: Path, monkeypatch):
    configuration, database = _inputs(tmp_path)
    calls = []
    class Engine:
        def dispose(self): calls.append("dispose")
    monkeypatch.setattr(operator, "build_engine", lambda _: Engine())
    class Probe:
        def __init__(self, _): pass
        def check(self): return Readiness(False, "schema_revision_mismatch")
    monkeypatch.setattr(operator, "DatabaseReadinessProbe", Probe)
    monkeypatch.setattr(operator, "compose_research_worker", lambda **_: calls.append("compose"))
    with pytest.raises(ResearchWorkerOperatorUnavailable) as caught:
        operator.run_research_worker(configuration, database, install_signal_handlers=False)
    assert str(caught.value) == "research_worker_operator_unavailable"
    assert caught.value.__cause__ is None
    assert calls == ["dispose"]


def test_signal_handlers_only_set_stop_and_are_restored(tmp_path: Path, monkeypatch):
    configuration, database = _inputs(tmp_path)
    handlers, restored = {}, []
    class Engine:
        def dispose(self): pass
    monkeypatch.setattr(operator, "build_engine", lambda _: Engine())
    monkeypatch.setattr(operator, "DatabaseReadinessProbe", lambda _: type("P", (), {"check": lambda self: Readiness(True, "database_ready")})())
    monkeypatch.setattr(operator, "LocalCsvMidBreakoutV0Resolver", lambda _: object())
    monkeypatch.setattr(operator, "LocalImmutableResearchArtifactStore", lambda _: object())
    monkeypatch.setattr(operator, "compose_research_worker", lambda **_: type("C", (), {"processor": object()})())
    def register(name, handler):
        if name in handlers: restored.append((name, handler))
        handlers[name] = handler
        return "previous"
    monkeypatch.setattr(operator.signal, "signal", register)
    class Loop:
        def __init__(self, *_args, **_kwargs): pass
        def run(self, *, stop_requested, wait):
            handlers[signal.SIGTERM](signal.SIGTERM, None)
            assert stop_requested() is True
    monkeypatch.setattr(operator, "ResearchWorkerLoop", Loop)
    assert operator.run_research_worker(configuration, database) == 0
    assert {name for name, handler in restored if handler == "previous"} == {signal.SIGTERM, signal.SIGINT}


def test_main_returns_detail_free_failure(tmp_path: Path):
    missing = tmp_path / "missing"
    assert operator.main(["--configuration", str(missing), "--database-url-file", str(missing)]) == 1
