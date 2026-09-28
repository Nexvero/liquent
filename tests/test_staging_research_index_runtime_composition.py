from pathlib import Path
from unittest.mock import Mock

import httpx2
import pytest
from sqlalchemy import event

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.staging_research_index_runtime_composition import (
    StagingResearchIndexRuntimeComposition,
    compose_staging_research_index_runtime,
)
from liquent_platform.transport.staging_research_index_http_acquisition import (
    StagingResearchIndexHttpAcquisition,
)


def test_composition_performs_no_database_or_http_io(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'absent.db'}")
    sql: list[str] = []
    requests: list[object] = []
    event.listen(
        engine, "before_cursor_execute", lambda *args: sql.append(str(args[2]))
    )
    client = httpx2.Client(transport=httpx2.MockTransport(
        lambda request: requests.append(request) or httpx2.Response(500)
    ))
    try:
        composition = compose_staging_research_index_runtime(engine, client)
        assert type(composition) is StagingResearchIndexRuntimeComposition
        assert type(composition.acquisition) is StagingResearchIndexHttpAcquisition
        assert composition._client is client
        assert sql == [] and requests == []
        assert repr(composition) == "StagingResearchIndexRuntimeComposition()"
    finally:
        client.close()
        engine.dispose()


def test_runtime_does_not_own_external_resources_or_credentials(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'absent.db'}")
    client = httpx2.Client(transport=httpx2.MockTransport(
        lambda _: httpx2.Response(500)
    ))
    try:
        composition = compose_staging_research_index_runtime(engine, client)
        assert not hasattr(composition, "close")
        assert not hasattr(composition, "sessions")
        assert not hasattr(composition, "credentials")
    finally:
        client.close()
        engine.dispose()


def test_execute_rejects_unvalidated_session_inventory_before_io(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'absent.db'}")
    requests: list[object] = []
    client = httpx2.Client(transport=httpx2.MockTransport(
        lambda request: requests.append(request) or httpx2.Response(500)
    ))
    try:
        composition = compose_staging_research_index_runtime(engine, client)
        with pytest.raises(ValueError, match="validated staging session handoff"):
            composition.execute(
                run=Mock(),
                evidence_path=tmp_path / "evidence.json",
                fixture_id=Mock(),
                expected_active_revision=Mock(),
                session_handoff={},  # type: ignore[arg-type]
            )
        assert requests == []
        assert not (tmp_path / "absent.db").exists()
        assert not (tmp_path / "evidence.json").exists()
    finally:
        client.close()
        engine.dispose()
