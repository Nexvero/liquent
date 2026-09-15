from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

import liquent_platform.persistence.staging_research_index_controlled_operator as operator
from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceResult,
    StagingResearchIndexAcceptanceRun,
)
from liquent_platform.application.staging_research_index_fixture_control import (
    StagingResearchIndexFixtureId,
    StagingResearchIndexFixtureRevision,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot as Slot,
)
from liquent_platform.application.staging_research_index_session_handoff import (
    StagingResearchIndexSessionHandoff,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    OpaqueStagingResearchSession as Session,
    StagingResearchIndexAcquisitionStage as Stage,
)


RUN = StagingResearchIndexAcceptanceRun(
    "sha256:" + "a" * 64, "https://staging.liquent.ai", datetime.now(UTC)
)
FIXTURE = StagingResearchIndexFixtureId("operator-fixture-2689")
REVISION = StagingResearchIndexFixtureRevision("operator-revision-2689")


def _handoff() -> StagingResearchIndexSessionHandoff:
    revocation = Session("operator-revocation-session-2689")
    return StagingResearchIndexSessionHandoff({
        Stage.BASELINE: {
            Slot.EMPTY_WORKSPACE_READER: Session("operator-empty-session-2689"),
            Slot.VISIBLE_WORKSPACE_READER: Session("operator-visible-session-2689"),
            Slot.REVOCATION_FIXTURE_READER: revocation,
        },
        Stage.AFTER_REVOCATION: {Slot.REVOCATION_FIXTURE_READER: revocation},
        Stage.UNAVAILABILITY: {
            Slot.UNAVAILABLE_FIXTURE_READER: Session(
                "operator-unavailable-session-2689"
            )
        },
    })


def _request(tmp_path: Path) -> operator.StagingResearchIndexOperatorRequest:
    return operator.StagingResearchIndexOperatorRequest(
        RUN, tmp_path / "evidence.json", FIXTURE, REVISION, _handoff()
    )


def test_operator_composes_once_and_forwards_exact_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    request = _request(tmp_path)
    result = StagingResearchIndexAcceptanceResult(
        RUN, StagingResearchIndexAcceptanceOutcome.ACCEPTED
    )
    runtime = Mock()
    runtime.execute.return_value = result
    compose = Mock(return_value=runtime)
    monkeypatch.setattr(operator, "compose_staging_research_index_runtime", compose)
    engine, client, material = Mock(), Mock(), Mock()

    assert operator.run_staging_research_index_operator(
        engine, client, request, material=material
    ) is result

    compose.assert_called_once_with(engine, client, material=material)
    runtime.execute.assert_called_once_with(
        run=request.run,
        evidence_path=request.evidence_path,
        fixture_id=request.fixture_id,
        expected_active_revision=request.expected_active_revision,
        session_handoff=request.session_handoff,
    )


def test_operator_rejects_untyped_request_before_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose = Mock()
    monkeypatch.setattr(operator, "compose_staging_research_index_runtime", compose)

    with pytest.raises(operator.StagingResearchIndexOperatorUnavailable) as captured:
        operator.run_staging_research_index_operator(Mock(), Mock(), object())  # type: ignore[arg-type]

    assert str(captured.value) == "staging_research_index_operator_unavailable"
    compose.assert_not_called()


def test_operator_collapses_execution_failure_without_details(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime = Mock()
    runtime.execute.side_effect = RuntimeError("sensitive adapter detail")
    monkeypatch.setattr(
        operator, "compose_staging_research_index_runtime", Mock(return_value=runtime)
    )

    with pytest.raises(operator.StagingResearchIndexOperatorUnavailable) as captured:
        operator.run_staging_research_index_operator(Mock(), Mock(), _request(tmp_path))

    assert str(captured.value) == "staging_research_index_operator_unavailable"
    assert captured.value.__cause__ is None


def test_request_requires_exact_types_and_hides_operational_material(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path)
    assert repr(request) == "StagingResearchIndexOperatorRequest()"
    assert "staging.liquent.ai" not in repr(request)
    assert "operator-fixture" not in repr(request)

    with pytest.raises(ValueError, match="exact staging Research-index"):
        operator.StagingResearchIndexOperatorRequest(
            RUN, str(tmp_path / "evidence.json"), FIXTURE, REVISION, _handoff()  # type: ignore[arg-type]
        )
