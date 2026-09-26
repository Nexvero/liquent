from unittest.mock import Mock

import pytest

from liquent_platform.application.staging_research_index_session_acquisition import (
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRevision,
)
from liquent_platform.application.staging_research_index_session_material_acquirer import (
    InjectedStagingResearchIndexSessionSetAcquirer,
)
from tests.test_staging_research_index_session_acquisition import _handoff


SET_ID = StagingResearchIndexSessionSetId("material-session-set-2695")
REVISION = StagingResearchIndexSessionSetRevision("material-session-revision-2695")


def test_resolves_exact_binding_and_wraps_validated_handoff() -> None:
    handoff = _handoff()
    source = Mock()
    source.resolve.return_value = handoff
    acquirer = InjectedStagingResearchIndexSessionSetAcquirer(source)

    acquired = acquirer.acquire(SET_ID, REVISION)

    assert acquired is not None
    assert acquired.session_set_id is SET_ID
    assert acquired.revision is REVISION
    assert acquired.handoff is handoff
    source.resolve.assert_called_once_with(SET_ID, REVISION)


def test_source_absence_remains_neutral() -> None:
    source = Mock()
    source.resolve.return_value = None
    assert InjectedStagingResearchIndexSessionSetAcquirer(source).acquire(
        SET_ID, REVISION
    ) is None


def test_invalid_binding_is_rejected_before_source_access() -> None:
    source = Mock()
    acquirer = InjectedStagingResearchIndexSessionSetAcquirer(source)
    with pytest.raises(ValueError, match="exact staging session-set binding"):
        acquirer.acquire(SET_ID.value, REVISION)  # type: ignore[arg-type]
    source.resolve.assert_not_called()


def test_unvalidated_source_result_is_rejected() -> None:
    source = Mock()
    source.resolve.return_value = object()
    with pytest.raises(ValueError, match="validated staging session handoff"):
        InjectedStagingResearchIndexSessionSetAcquirer(source).acquire(
            SET_ID, REVISION
        )


def test_adapter_retains_no_session_material_in_representation() -> None:
    source = Mock()
    source.resolve.return_value = _handoff()
    acquirer = InjectedStagingResearchIndexSessionSetAcquirer(source)
    acquired = acquirer.acquire(SET_ID, REVISION)

    assert repr(acquirer) == "InjectedStagingResearchIndexSessionSetAcquirer()"
    assert repr(acquired) == "AcquiredStagingResearchIndexSessionSet()"
    assert SET_ID.value not in repr(acquirer)
