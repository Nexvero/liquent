from typing import get_type_hints

import pytest

from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot as Slot,
)
from liquent_platform.application.staging_research_index_session_acquisition import (
    AcquiredStagingResearchIndexSessionSet,
    StagingResearchIndexSessionSetAcquirer,
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRevision,
    validate_staging_research_index_session_set_acquisition,
)
from liquent_platform.application.staging_research_index_session_handoff import (
    StagingResearchIndexSessionHandoff,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    OpaqueStagingResearchSession as Session,
    StagingResearchIndexAcquisitionStage as Stage,
)


SET_ID = StagingResearchIndexSessionSetId("session-set-id-2690")
REVISION = StagingResearchIndexSessionSetRevision("session-set-revision-2690")


def _handoff() -> StagingResearchIndexSessionHandoff:
    revocation = Session("acquisition-revocation-session-2690")
    return StagingResearchIndexSessionHandoff({
        Stage.BASELINE: {
            Slot.EMPTY_WORKSPACE_READER: Session("acquisition-empty-session-2690"),
            Slot.VISIBLE_WORKSPACE_READER: Session(
                "acquisition-visible-session-2690"
            ),
            Slot.REVOCATION_FIXTURE_READER: revocation,
        },
        Stage.AFTER_REVOCATION: {Slot.REVOCATION_FIXTURE_READER: revocation},
        Stage.UNAVAILABILITY: {
            Slot.UNAVAILABLE_FIXTURE_READER: Session(
                "acquisition-unavailable-session-2690"
            )
        },
    })


def test_acquired_set_preserves_id_revision_and_validated_handoff() -> None:
    acquired = AcquiredStagingResearchIndexSessionSet(
        SET_ID, REVISION, _handoff()
    )

    validate_staging_research_index_session_set_acquisition(
        SET_ID, REVISION, acquired
    )
    assert acquired.handoff.execution_sessions()
    assert repr(acquired) == "AcquiredStagingResearchIndexSessionSet()"
    assert "session-set" not in repr(acquired)


@pytest.mark.parametrize(
    "session_set_id,revision",
    [
        (StagingResearchIndexSessionSetId("different-set-id-2690"), REVISION),
        (SET_ID, StagingResearchIndexSessionSetRevision("different-revision-2690")),
    ],
)
def test_validation_rejects_substituted_binding(
    session_set_id: StagingResearchIndexSessionSetId,
    revision: StagingResearchIndexSessionSetRevision,
) -> None:
    acquired = AcquiredStagingResearchIndexSessionSet(
        session_set_id, revision, _handoff()
    )

    with pytest.raises(ValueError, match="acquisition binding is invalid"):
        validate_staging_research_index_session_set_acquisition(
            SET_ID, REVISION, acquired
        )


@pytest.mark.parametrize("value", ["", "short", "contains space", "x" * 257])
def test_opaque_identifiers_reject_noncanonical_material(value: str) -> None:
    with pytest.raises(ValueError, match="opaque staging session-set"):
        StagingResearchIndexSessionSetId(value)
    with pytest.raises(ValueError, match="opaque staging session-set"):
        StagingResearchIndexSessionSetRevision(value)


def test_acquirer_contract_has_only_revision_bound_input_and_neutral_absence() -> None:
    hints = get_type_hints(StagingResearchIndexSessionSetAcquirer.acquire)

    assert set(hints) == {"session_set_id", "expected_revision", "return"}
    assert hints["session_set_id"] is StagingResearchIndexSessionSetId
    assert hints["expected_revision"] is StagingResearchIndexSessionSetRevision
    assert type(None) in hints["return"].__args__


def test_acquired_set_requires_exact_domain_types() -> None:
    with pytest.raises(ValueError, match="acquired staging session set"):
        AcquiredStagingResearchIndexSessionSet(
            SET_ID, REVISION, object()  # type: ignore[arg-type]
        )
