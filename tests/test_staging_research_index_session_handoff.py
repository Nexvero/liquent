import pytest

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


def _inventory() -> dict[Stage, dict[Slot, Session]]:
    revocation = Session("revocation-session-0001")
    return {
        Stage.BASELINE: {
            Slot.EMPTY_WORKSPACE_READER: Session("empty-workspace-session-0001"),
            Slot.VISIBLE_WORKSPACE_READER: Session("visible-workspace-session-01"),
            Slot.REVOCATION_FIXTURE_READER: revocation,
        },
        Stage.AFTER_REVOCATION: {
            Slot.REVOCATION_FIXTURE_READER: revocation,
        },
        Stage.UNAVAILABILITY: {
            Slot.UNAVAILABLE_FIXTURE_READER: Session("unavailable-session-0001"),
        },
    }


def test_accepts_exact_inventory_and_returns_independent_execution_copy() -> None:
    source = _inventory()
    handoff = StagingResearchIndexSessionHandoff(source)

    source[Stage.BASELINE].clear()
    execution = handoff.execution_sessions()

    assert set(execution) == set(Stage)
    assert set(execution[Stage.BASELINE]) == {
        Slot.EMPTY_WORKSPACE_READER,
        Slot.VISIBLE_WORKSPACE_READER,
        Slot.REVOCATION_FIXTURE_READER,
    }
    execution[Stage.BASELINE].clear()
    assert handoff.execution_sessions()[Stage.BASELINE]


def test_requires_same_revocation_session_before_and_after_mutation() -> None:
    sessions = _inventory()
    sessions[Stage.AFTER_REVOCATION][Slot.REVOCATION_FIXTURE_READER] = Session(
        "different-session-0001"
    )

    with pytest.raises(ValueError, match="must remain bound"):
        StagingResearchIndexSessionHandoff(sessions)


@pytest.mark.parametrize("change", ["missing_stage", "extra_slot", "none_slot"])
def test_rejects_inexact_inventory(change: str) -> None:
    sessions = _inventory()
    if change == "missing_stage":
        del sessions[Stage.UNAVAILABILITY]
    elif change == "extra_slot":
        sessions[Stage.AFTER_REVOCATION][Slot.VISIBLE_WORKSPACE_READER] = Session(
            "extra-session-value-0001"
        )
    else:
        sessions[Stage.BASELINE][Slot.NONE] = Session("none-session-value-00001")

    with pytest.raises(ValueError, match="exact staging session handoff"):
        StagingResearchIndexSessionHandoff(sessions)


def test_rejects_non_session_value_and_non_dict_inventory() -> None:
    sessions = _inventory()
    sessions[Stage.BASELINE][Slot.EMPTY_WORKSPACE_READER] = "not-a-session"  # type: ignore[assignment]

    with pytest.raises(ValueError, match="exact staging session handoff"):
        StagingResearchIndexSessionHandoff(sessions)
    with pytest.raises(ValueError, match="exact staging session handoff"):
        StagingResearchIndexSessionHandoff(dict(_inventory()).keys())  # type: ignore[arg-type]


def test_representation_contains_no_session_material() -> None:
    handoff = StagingResearchIndexSessionHandoff(_inventory())

    assert repr(handoff) == "StagingResearchIndexSessionHandoff()"
    assert "revocation-session" not in repr(handoff)
