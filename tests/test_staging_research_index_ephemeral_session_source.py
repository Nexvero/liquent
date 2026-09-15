from unittest.mock import Mock

import pytest

from liquent_platform.application.staging_research_index_ephemeral_session_source import (
    EphemeralStagingResearchIndexSessionHandoffSource,
)
from liquent_platform.application.staging_research_index_session_acquisition import (
    StagingResearchIndexSessionSetId,
    StagingResearchIndexSessionSetRevision,
)
from tests.test_staging_research_index_session_acquisition import _handoff


SET_ID = StagingResearchIndexSessionSetId("ephemeral-session-set-2697")
REVISION = StagingResearchIndexSessionSetRevision("ephemeral-session-revision-2697")


def test_each_lookup_invokes_resolver_afresh() -> None:
    first, second = _handoff(), _handoff()
    resolver = Mock(side_effect=[first, second])
    source = EphemeralStagingResearchIndexSessionHandoffSource(resolver)

    assert source.resolve(SET_ID, REVISION) is first
    assert source.resolve(SET_ID, REVISION) is second
    assert resolver.call_count == 2
    assert resolver.call_args_list[0].args == (SET_ID, REVISION)
    assert resolver.call_args_list[1].args == (SET_ID, REVISION)


def test_later_absence_is_not_hidden_by_previous_success() -> None:
    resolver = Mock(side_effect=[_handoff(), None])
    source = EphemeralStagingResearchIndexSessionHandoffSource(resolver)
    assert source.resolve(SET_ID, REVISION) is not None
    assert source.resolve(SET_ID, REVISION) is None


def test_invalid_binding_is_rejected_before_resolver_access() -> None:
    resolver = Mock()
    source = EphemeralStagingResearchIndexSessionHandoffSource(resolver)
    with pytest.raises(ValueError, match="exact staging session-set binding"):
        source.resolve(SET_ID, REVISION.value)  # type: ignore[arg-type]
    resolver.assert_not_called()


def test_invalid_resolver_result_is_rejected() -> None:
    source = EphemeralStagingResearchIndexSessionHandoffSource(
        Mock(return_value=object())
    )
    with pytest.raises(ValueError, match="validated staging session handoff"):
        source.resolve(SET_ID, REVISION)


def test_representation_hides_resolver_and_session_material() -> None:
    resolver = Mock(return_value=_handoff())
    source = EphemeralStagingResearchIndexSessionHandoffSource(resolver)
    assert repr(source) == "EphemeralStagingResearchIndexSessionHandoffSource()"
    assert repr(resolver) not in repr(source)
    assert SET_ID.value not in repr(source)
