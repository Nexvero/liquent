"""Crash-safe persistence contract for staging promotion attempts."""

from dataclasses import dataclass, field
import re
from typing import Protocol

from liquent_platform.application.staging_research_index_atomic_promotion import (
    StagingResearchIndexPromotionCommand,
    StagingResearchIndexPromotionReceipt,
)
from liquent_platform.application.staging_research_index_promotion_authority import (
    CurrentStagingResearchIndexPromotionAuthority,
)


_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,255}\Z")


@dataclass(frozen=True, slots=True)
class PreparedStagingResearchIndexPromotionAttempt:
    operation_id: str = field(repr=False)
    command: StagingResearchIndexPromotionCommand = field(repr=False)
    authority: CurrentStagingResearchIndexPromotionAuthority = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.operation_id) is not str
            or _OPAQUE.fullmatch(self.operation_id) is None
            or type(self.command) is not StagingResearchIndexPromotionCommand
            or type(self.authority) is not CurrentStagingResearchIndexPromotionAuthority
            or self.authority.actor_user_id != self.command.actor.user_id
        ):
            raise ValueError("prepared staging promotion attempt is invalid")

    def __repr__(self) -> str:
        return "PreparedStagingResearchIndexPromotionAttempt()"


@dataclass(frozen=True, slots=True)
class WriteStartedStagingResearchIndexPromotionAttempt:
    prepared: PreparedStagingResearchIndexPromotionAttempt = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.prepared) is not PreparedStagingResearchIndexPromotionAttempt:
            raise ValueError("write-started staging promotion attempt is invalid")

    def __repr__(self) -> str:
        return "WriteStartedStagingResearchIndexPromotionAttempt()"


@dataclass(frozen=True, slots=True)
class UnknownStagingResearchIndexPromotionEffect:
    attempt: WriteStartedStagingResearchIndexPromotionAttempt = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.attempt) is not WriteStartedStagingResearchIndexPromotionAttempt:
            raise ValueError("unknown staging promotion effect is invalid")

    def __repr__(self) -> str:
        return "UnknownStagingResearchIndexPromotionEffect()"


class StagingResearchIndexPromotionAttemptStore(Protocol):
    def prepare_current(
        self, command: StagingResearchIndexPromotionCommand, operation_id: str
    ) -> PreparedStagingResearchIndexPromotionAttempt | None: ...

    def mark_write_started(
        self, attempt: PreparedStagingResearchIndexPromotionAttempt
    ) -> WriteStartedStagingResearchIndexPromotionAttempt | None: ...

    def record_unknown(
        self, attempt: WriteStartedStagingResearchIndexPromotionAttempt
    ) -> UnknownStagingResearchIndexPromotionEffect: ...

    def record_committed(
        self,
        attempt: WriteStartedStagingResearchIndexPromotionAttempt,
        receipt: StagingResearchIndexPromotionReceipt,
    ) -> StagingResearchIndexPromotionReceipt: ...
