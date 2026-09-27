"""Opaque revision-bound contract for controlled staging-session acquisition."""

from dataclasses import dataclass, field
import re
from typing import Protocol

from liquent_platform.application.staging_research_index_session_handoff import (
    StagingResearchIndexSessionHandoff,
)


_OPAQUE = re.compile(r"[A-Za-z0-9._~-]{16,256}\Z")


def _validate_opaque(value: object) -> None:
    if type(value) is not str or _OPAQUE.fullmatch(value) is None:
        raise ValueError("opaque staging session-set material is invalid")


@dataclass(frozen=True, slots=True)
class StagingResearchIndexSessionSetId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate_opaque(self.value)


@dataclass(frozen=True, slots=True)
class StagingResearchIndexSessionSetRevision:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate_opaque(self.value)


@dataclass(frozen=True, slots=True)
class AcquiredStagingResearchIndexSessionSet:
    session_set_id: StagingResearchIndexSessionSetId = field(repr=False)
    revision: StagingResearchIndexSessionSetRevision = field(repr=False)
    handoff: StagingResearchIndexSessionHandoff = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.session_set_id) is not StagingResearchIndexSessionSetId
            or type(self.revision) is not StagingResearchIndexSessionSetRevision
            or type(self.handoff) is not StagingResearchIndexSessionHandoff
        ):
            raise ValueError("acquired staging session set is invalid")

    def __repr__(self) -> str:
        return "AcquiredStagingResearchIndexSessionSet()"


class StagingResearchIndexSessionSetAcquirer(Protocol):
    def acquire(
        self,
        session_set_id: StagingResearchIndexSessionSetId,
        expected_revision: StagingResearchIndexSessionSetRevision,
    ) -> AcquiredStagingResearchIndexSessionSet | None: ...


def validate_staging_research_index_session_set_acquisition(
    session_set_id: StagingResearchIndexSessionSetId,
    expected_revision: StagingResearchIndexSessionSetRevision,
    acquired: AcquiredStagingResearchIndexSessionSet,
) -> None:
    """Require the acquired set to retain the requested opaque binding."""

    if (
        type(session_set_id) is not StagingResearchIndexSessionSetId
        or type(expected_revision) is not StagingResearchIndexSessionSetRevision
        or type(acquired) is not AcquiredStagingResearchIndexSessionSet
        or acquired.session_set_id != session_set_id
        or acquired.revision != expected_revision
    ):
        raise ValueError("staging session-set acquisition binding is invalid")
