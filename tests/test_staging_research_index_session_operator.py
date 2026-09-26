from pathlib import Path
from unittest.mock import Mock

import pytest

import liquent_platform.persistence.staging_research_index_session_operator as operator
from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceResult,
)
from liquent_platform.application.staging_research_index_session_acquisition import (
    AcquiredStagingResearchIndexSessionSet,
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRevision,
)
from tests.test_staging_research_index_acceptance_operator import FIXTURE, REVISION, RUN
from tests.test_staging_research_index_session_acquisition import _handoff


SET_ID = StagingResearchIndexSessionSetId("session-operator-set-2694")
SET_REVISION = StagingResearchIndexSessionSetRevision("session-operator-revision-2694")


def _request(tmp_path: Path) -> operator.StagingResearchIndexSessionOperatorRequest:
    return operator.StagingResearchIndexSessionOperatorRequest(
        RUN, tmp_path / "evidence.json", FIXTURE, REVISION, SET_ID, SET_REVISION
    )


def test_acquires_then_executes_with_exact_handoff(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = _request(tmp_path)
    registry = Mock()
    monkeypatch.setattr(
        operator,
        "compose_persistent_staging_research_index_session_set_registry",
        Mock(return_value=Mock(resolver=registry)),
    )
    acquired = AcquiredStagingResearchIndexSessionSet(
        SET_ID, SET_REVISION, _handoff()
    )
    acquire = Mock(return_value=acquired)
    monkeypatch.setattr(
        operator, "acquire_registered_staging_research_index_session_set", acquire
    )
    result = StagingResearchIndexAcceptanceResult(
        RUN, StagingResearchIndexAcceptanceOutcome.ACCEPTED
    )
    run = Mock(return_value=result)
    monkeypatch.setattr(operator, "run_staging_research_index_operator", run)
    engine, client, acquirer, material = Mock(), Mock(), Mock(), Mock()

    assert operator.run_staging_research_index_session_operator(
        engine, client, request, acquirer, material=material
    ) is result

    acquire.assert_called_once_with(SET_ID, SET_REVISION, registry, acquirer)
    forwarded = run.call_args.args[2]
    assert forwarded.session_handoff is acquired.handoff
    assert forwarded.run is RUN
    assert run.call_args.kwargs == {"material": material}


def test_neutral_absence_does_not_execute(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        operator,
        "compose_persistent_staging_research_index_session_set_registry",
        Mock(return_value=Mock(resolver=Mock())),
    )
    monkeypatch.setattr(
        operator,
        "acquire_registered_staging_research_index_session_set",
        Mock(return_value=None),
    )
    run = Mock()
    monkeypatch.setattr(operator, "run_staging_research_index_operator", run)

    assert operator.run_staging_research_index_session_operator(
        Mock(), Mock(), _request(tmp_path), Mock()
    ) is None
    run.assert_not_called()


def test_untyped_request_is_rejected_before_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = Mock()
    monkeypatch.setattr(
        operator,
        "compose_persistent_staging_research_index_session_set_registry",
        compose,
    )
    with pytest.raises(operator.StagingResearchIndexSessionOperatorUnavailable):
        operator.run_staging_research_index_session_operator(
            Mock(), Mock(), object(), Mock()  # type: ignore[arg-type]
        )
    compose.assert_not_called()


def test_failures_are_collapsed_without_details(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        operator,
        "compose_persistent_staging_research_index_session_set_registry",
        Mock(side_effect=RuntimeError("database address")),
    )
    with pytest.raises(operator.StagingResearchIndexSessionOperatorUnavailable) as raised:
        operator.run_staging_research_index_session_operator(
            Mock(), Mock(), _request(tmp_path), Mock()
        )
    assert raised.value.__cause__ is None
    assert "database" not in str(raised.value)


def test_request_hides_bound_operational_material(tmp_path: Path) -> None:
    request = _request(tmp_path)
    assert repr(request) == "StagingResearchIndexSessionOperatorRequest()"
    assert SET_ID.value not in repr(request)
    with pytest.raises(ValueError, match="exact staging session operator"):
        operator.StagingResearchIndexSessionOperatorRequest(
            RUN,
            str(tmp_path / "evidence.json"),  # type: ignore[arg-type]
            FIXTURE,
            REVISION,
            SET_ID,
            SET_REVISION,
        )
