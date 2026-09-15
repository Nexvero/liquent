"""Validated opaque-session handoff for one controlled staging run."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    OpaqueStagingResearchSession,
    StagingResearchIndexAcquisitionStage,
)


_EXPECTED_SLOTS = {
    StagingResearchIndexAcquisitionStage.BASELINE: {
        StagingResearchIndexCredentialSlot.EMPTY_WORKSPACE_READER,
        StagingResearchIndexCredentialSlot.VISIBLE_WORKSPACE_READER,
        StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER,
    },
    StagingResearchIndexAcquisitionStage.AFTER_REVOCATION: {
        StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER,
    },
    StagingResearchIndexAcquisitionStage.UNAVAILABILITY: {
        StagingResearchIndexCredentialSlot.UNAVAILABLE_FIXTURE_READER,
    },
}


@dataclass(frozen=True, slots=True)
class StagingResearchIndexSessionHandoff:
    """Hold an exact, defensively copied session inventory without authority."""

    sessions: Mapping[
        StagingResearchIndexAcquisitionStage,
        Mapping[StagingResearchIndexCredentialSlot, OpaqueStagingResearchSession],
    ] = field(repr=False)

    def __post_init__(self) -> None:
        sessions = self.sessions
        if type(sessions) is not dict or set(sessions) != set(_EXPECTED_SLOTS):
            raise ValueError("exact staging session handoff is required")

        copied = {}
        for stage, expected_slots in _EXPECTED_SLOTS.items():
            stage_sessions = sessions[stage]
            if (
                type(stage_sessions) is not dict
                or set(stage_sessions) != expected_slots
                or any(
                    type(session) is not OpaqueStagingResearchSession
                    for session in stage_sessions.values()
                )
            ):
                raise ValueError("exact staging session handoff is required")
            copied[stage] = MappingProxyType(dict(stage_sessions))

        revocation_slot = StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER
        if (
            copied[StagingResearchIndexAcquisitionStage.BASELINE][revocation_slot]
            != copied[StagingResearchIndexAcquisitionStage.AFTER_REVOCATION][
                revocation_slot
            ]
        ):
            raise ValueError("revocation observation session must remain bound")

        object.__setattr__(self, "sessions", MappingProxyType(copied))

    def __repr__(self) -> str:
        return "StagingResearchIndexSessionHandoff()"

    def execution_sessions(
        self,
    ) -> dict[
        StagingResearchIndexAcquisitionStage,
        dict[StagingResearchIndexCredentialSlot, OpaqueStagingResearchSession],
    ]:
        """Return the validated inventory in the existing execution shape."""

        return {
            stage: dict(stage_sessions)
            for stage, stage_sessions in self.sessions.items()
        }
