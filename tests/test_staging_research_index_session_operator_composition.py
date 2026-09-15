from pathlib import Path
from unittest.mock import Mock

import httpx2
import pytest
from sqlalchemy import event

import liquent_platform.persistence.staging_research_index_session_operator_composition as composition
from liquent_platform.persistence.database import build_engine
from tests.test_staging_research_index_session_operator import _request


def test_composition_performs_no_database_http_or_source_io(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'absent.db'}")
    sql: list[str] = []
    requests: list[object] = []
    event.listen(
        engine, "before_cursor_execute", lambda *args: sql.append(str(args[2]))
    )
    client = httpx2.Client(transport=httpx2.MockTransport(
        lambda request: requests.append(request) or httpx2.Response(500)
    ))
    source = Mock()
    try:
        wired = composition.compose_staging_research_index_session_operator(
            engine, client, source
        )
        assert sql == [] and requests == []
        source.resolve.assert_not_called()
        assert repr(wired) == "StagingResearchIndexSessionOperatorComposition()"
        assert not (tmp_path / "absent.db").exists()
    finally:
        client.close()
        engine.dispose()


def test_execute_forwards_bound_resources_and_exact_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    engine, client, source, material = Mock(), Mock(), Mock(), Mock()
    request = _request(tmp_path)
    result = Mock()
    run = Mock(return_value=result)
    monkeypatch.setattr(
        composition, "run_staging_research_index_session_operator", run
    )
    wired = composition.compose_staging_research_index_session_operator(
        engine, client, source, material=material
    )

    assert wired.execute(request) is result
    run.assert_called_once_with(
        engine, client, request, wired.acquirer, material=material
    )
    assert wired.acquirer._source is source


def test_composition_does_not_own_external_resources() -> None:
    wired = composition.compose_staging_research_index_session_operator(
        Mock(), Mock(), Mock()
    )
    assert not hasattr(wired, "close")
    assert not hasattr(wired, "credentials")
    assert not hasattr(wired, "sessions")


def test_representation_hides_resources_and_source() -> None:
    engine, client, source = Mock(), Mock(), Mock()
    wired = composition.compose_staging_research_index_session_operator(
        engine, client, source
    )
    rendered = repr(wired)
    assert rendered == "StagingResearchIndexSessionOperatorComposition()"
    assert repr(source) not in rendered
