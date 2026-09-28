from unittest.mock import Mock

import pytest

from liquent_platform.application.staging_research_index_controlled_session_acquisition import (
    StagingResearchIndexControlledSessionAcquisitionUnavailable,
    acquire_registered_staging_research_index_session_set,
)
from liquent_platform.application.staging_research_index_session_acquisition import (
    AcquiredStagingResearchIndexSessionSet,
    RegisteredStagingResearchIndexSessionSet,
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRevision,
)
from tests.test_staging_research_index_session_acquisition import _handoff


SET_ID = StagingResearchIndexSessionSetId("controlled-session-set-2693")
REVISION = StagingResearchIndexSessionSetRevision("controlled-session-revision-2693")
REGISTERED = RegisteredStagingResearchIndexSessionSet(SET_ID, REVISION)
ACQUIRED = AcquiredStagingResearchIndexSessionSet(SET_ID, REVISION, _handoff())


def test_resolves_before_and_after_exact_acquisition() -> None:
    registry = Mock()
    registry.resolve.side_effect = [REGISTERED, REGISTERED]
    acquirer = Mock()
    acquirer.acquire.return_value = ACQUIRED

    assert acquire_registered_staging_research_index_session_set(
        SET_ID, REVISION, registry, acquirer
    ) is ACQUIRED
    assert registry.resolve.call_count == 2
    acquirer.acquire.assert_called_once_with(SET_ID, REVISION)


def test_initial_absence_prevents_acquisition() -> None:
    registry, acquirer = Mock(), Mock()
    registry.resolve.return_value = None
    assert acquire_registered_staging_research_index_session_set(
        SET_ID, REVISION, registry, acquirer
    ) is None
    acquirer.acquire.assert_not_called()


def test_revocation_during_acquisition_fails_closed() -> None:
    registry, acquirer = Mock(), Mock()
    registry.resolve.side_effect = [REGISTERED, None]
    acquirer.acquire.return_value = ACQUIRED
    assert acquire_registered_staging_research_index_session_set(
        SET_ID, REVISION, registry, acquirer
    ) is None


def test_acquirer_absence_is_neutral_without_second_lookup() -> None:
    registry, acquirer = Mock(), Mock()
    registry.resolve.return_value = REGISTERED
    acquirer.acquire.return_value = None
    assert acquire_registered_staging_research_index_session_set(
        SET_ID, REVISION, registry, acquirer
    ) is None
    registry.resolve.assert_called_once_with(SET_ID, REVISION)


def test_substitution_and_technical_failure_are_detail_free() -> None:
    registry, acquirer = Mock(), Mock()
    registry.resolve.return_value = REGISTERED
    acquirer.acquire.return_value = AcquiredStagingResearchIndexSessionSet(
        StagingResearchIndexSessionSetId("substituted-session-set-2693"),
        REVISION,
        _handoff(),
    )
    with pytest.raises(StagingResearchIndexControlledSessionAcquisitionUnavailable) as raised:
        acquire_registered_staging_research_index_session_set(
            SET_ID, REVISION, registry, acquirer
        )
    assert raised.value.__cause__ is None and raised.value.__context__ is None
    assert "substituted" not in str(raised.value)
