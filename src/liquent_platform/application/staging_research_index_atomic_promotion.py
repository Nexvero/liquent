"""Atomic boundary contract for one staging Research-index promotion."""

from dataclasses import dataclass, field
import re
from typing import Protocol

from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import SessionPrincipal


_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,255}\Z")


@dataclass(frozen=True, slots=True)
class StagingResearchIndexPromotionCommand:
    actor: SessionPrincipal = field(repr=False)
    evidence_digest: str = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.actor) is not SessionPrincipal
            or type(self.evidence_digest) is not str
            or _DIGEST.fullmatch(self.evidence_digest) is None
        ):
            raise ValueError("staging promotion command is invalid")

    def __repr__(self) -> str:
        return "StagingResearchIndexPromotionCommand()"


@dataclass(frozen=True, slots=True)
class StagingResearchIndexPromotionReceipt:
    operation_id: str = field(repr=False)
    actor_user_id: UserId = field(repr=False)
    evidence_digest: str = field(repr=False)
    candidate_digest: str = field(repr=False)
    staging_origin: str = field(repr=False)
    target_environment: str = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.operation_id) is not str
            or _OPAQUE.fullmatch(self.operation_id) is None
            or not self.actor_user_id
            or type(self.evidence_digest) is not str
            or _DIGEST.fullmatch(self.evidence_digest) is None
            or type(self.candidate_digest) is not str
            or _DIGEST.fullmatch(self.candidate_digest) is None
            or type(self.staging_origin) is not str
            or not self.staging_origin
            or type(self.target_environment) is not str
            or _OPAQUE.fullmatch(self.target_environment) is None
        ):
            raise ValueError("staging promotion receipt is invalid")

    def __repr__(self) -> str:
        return "StagingResearchIndexPromotionReceipt()"


class AtomicStagingResearchIndexPromotionGateway(Protocol):
    """Revalidate all current facts and mutate within one atomic operation."""

    def promote_current(
        self, command: StagingResearchIndexPromotionCommand
    ) -> StagingResearchIndexPromotionReceipt | None: ...
