from pathlib import Path
from unittest.mock import Mock

import pytest

import liquent_platform.persistence.staging_research_index_session_invocation as invocation
from tests.test_staging_research_index_session_operator import _request


def test_composes_once_and_executes_exact_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    engine, client, resolver, material = Mock(), Mock(), Mock(), Mock()
    request = _request(tmp_path)
    result = Mock()
    operator = Mock()
    operator.execute.return_value = result
    compose = Mock(return_value=operator)
    monkeypatch.setattr(
        invocation,
        "compose_ephemeral_staging_research_index_session_operator",
        compose,
    )

    assert invocation.invoke_staging_research_index_session_acceptance(
        engine, client, resolver, request, material=material
    ) is result

    compose.assert_called_once_with(engine, client, resolver, material=material)
    operator.execute.assert_called_once_with(request)


def test_neutral_absence_is_preserved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    operator = Mock()
    operator.execute.return_value = None
    monkeypatch.setattr(
        invocation,
        "compose_ephemeral_staging_research_index_session_operator",
        Mock(return_value=operator),
    )
    assert invocation.invoke_staging_research_index_session_acceptance(
        Mock(), Mock(), Mock(), _request(tmp_path)
    ) is None


def test_invalid_request_is_rejected_before_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = Mock()
    monkeypatch.setattr(
        invocation,
        "compose_ephemeral_staging_research_index_session_operator",
        compose,
    )
    with pytest.raises(invocation.StagingResearchIndexSessionInvocationUnavailable):
        invocation.invoke_staging_research_index_session_acceptance(
            Mock(), Mock(), Mock(), object()  # type: ignore[arg-type]
        )
    compose.assert_not_called()


def test_composition_failure_is_detail_free(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        invocation,
        "compose_ephemeral_staging_research_index_session_operator",
        Mock(side_effect=RuntimeError("secret resolver location")),
    )
    with pytest.raises(
        invocation.StagingResearchIndexSessionInvocationUnavailable
    ) as raised:
        invocation.invoke_staging_research_index_session_acceptance(
            Mock(), Mock(), Mock(), _request(tmp_path)
        )
    assert raised.value.__cause__ is None
    assert "resolver" not in str(raised.value)


def test_execution_failure_is_detail_free(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    operator = Mock()
    operator.execute.side_effect = RuntimeError("staging response body")
    monkeypatch.setattr(
        invocation,
        "compose_ephemeral_staging_research_index_session_operator",
        Mock(return_value=operator),
    )
    with pytest.raises(
        invocation.StagingResearchIndexSessionInvocationUnavailable
    ) as raised:
        invocation.invoke_staging_research_index_session_acceptance(
            Mock(), Mock(), Mock(), _request(tmp_path)
        )
    assert raised.value.__cause__ is None
    assert "response" not in str(raised.value)
