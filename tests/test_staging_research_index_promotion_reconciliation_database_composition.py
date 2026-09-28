import json
from pathlib import Path

import httpx2
import pytest

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.staging_research_index_promotion_attempt_journal import (  # noqa: E501
    DatabaseStagingResearchIndexPromotionAttemptJournal,
)
from liquent_platform.transport import (
    staging_research_index_promotion_provider_lifecycle as lifecycle_module,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_database_composition import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationDatabaseCompositionUnavailable,
    compose_database_backed_staging_research_index_promotion_reconciliation_runtime,
)
from tests.test_staging_research_index_promotion_attempt_journal import NOW, _attempt
from tests.test_staging_research_index_promotion_provider_composition import _payload


def write_settings(path: Path) -> None:
    path.write_text(
        "LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT="
        "https://provider.example/status/\n"
    )
    path.chmod(0o600)


def install_client(monkeypatch, handler):
    def build():
        return httpx2.Client(
            transport=httpx2.MockTransport(handler), trust_env=False
        )

    monkeypatch.setattr(lifecycle_module, "_create_client", build)


def record_unknown(engine, prepared):
    journal = DatabaseStagingResearchIndexPromotionAttemptJournal(engine)
    journal.record_prepared(prepared, observed_at=NOW)
    started = journal.mark_write_started(prepared, observed_at=NOW)
    return journal.record_unknown(started, observed_at=NOW)


def test_existing_engine_binds_index_reader_and_recorder_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'runtime.db'}")
    upgrade_to_head(str(engine.url))
    path = tmp_path / "provider.env"
    write_settings(path)
    prepared = _attempt(operation="promotion-2729")
    unknown = record_unknown(engine, prepared)
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            content=iter([json.dumps(_payload(unknown)).encode()]),
        )

    install_client(monkeypatch, handler)
    try:
        with compose_database_backed_staging_research_index_promotion_reconciliation_runtime(
            path, engine
        ) as runtime:
            receipt = runtime.execute_one()
            assert receipt is not None and receipt.operation_id == prepared.operation_id
        assert len(requests) == 1
        with compose_database_backed_staging_research_index_promotion_reconciliation_runtime(
            path, engine
        ) as next_runtime:
            assert next_runtime.execute_one() is None
    finally:
        engine.dispose()


def test_empty_database_is_neutral_without_provider_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    upgrade_to_head(str(engine.url))
    path = tmp_path / "provider.env"
    write_settings(path)
    requests = []
    install_client(monkeypatch, lambda request: requests.append(request))
    try:
        runtime = compose_database_backed_staging_research_index_promotion_reconciliation_runtime(
            path, engine
        )
        try:
            assert runtime.execute_one() is None and requests == []
        finally:
            runtime.close()
    finally:
        engine.dispose()


def test_invalid_engine_fails_before_client_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "provider.env"
    write_settings(path)
    created = []
    monkeypatch.setattr(lifecycle_module, "_create_client", lambda: created.append(1))
    with pytest.raises(
        StagingResearchIndexPromotionReconciliationDatabaseCompositionUnavailable
    ) as caught:
        compose_database_backed_staging_research_index_promotion_reconciliation_runtime(
            path, object()
        )
    assert created == []
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_composition_does_not_own_engine_or_expose_schema_operations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'ownership.db'}")
    upgrade_to_head(str(engine.url))
    path = tmp_path / "provider.env"
    write_settings(path)
    install_client(monkeypatch, lambda _: httpx2.Response(500))
    runtime = compose_database_backed_staging_research_index_promotion_reconciliation_runtime(
        path, engine
    )
    runtime.close()
    try:
        with engine.connect() as connection:
            assert connection is not None
        for forbidden in ("migrate", "upgrade", "create_all", "drop_all"):
            assert not hasattr(runtime, forbidden)
    finally:
        engine.dispose()
