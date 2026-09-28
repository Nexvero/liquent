"""Current operator authority for one staging promotion evidence binding."""

from dataclasses import dataclass, field
import re
from typing import Protocol

from liquent_platform.application.staging_research_index_current_promotion_evidence import (
    CurrentStagingResearchIndexPromotionEvidence,
)
from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import SessionPrincipal


_ENVIRONMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,127}\Z")


@dataclass(frozen=True, slots=True)
class CurrentStagingResearchIndexPromotionAuthority:
    actor_user_id: UserId = field(repr=False)
    candidate_digest: str = field(repr=False)
    staging_origin: str = field(repr=False)
    target_environment: str = field(repr=False)

    def __post_init__(self) -> None:
        binding = self.candidate_digest
        if (
            not self.actor_user_id
            or re.fullmatch(r"sha256:[0-9a-f]{64}", binding) is None
            or type(self.staging_origin) is not str
            or not self.staging_origin
            or type(self.target_environment) is not str
            or _ENVIRONMENT.fullmatch(self.target_environment) is None
        ):
            raise ValueError("current staging promotion authority is invalid")

    def __repr__(self) -> str:
        return "CurrentStagingResearchIndexPromotionAuthority()"


class StagingResearchIndexPromotionAuthorityResolver(Protocol):
    def resolve_current(
        self,
        actor: SessionPrincipal,
        evidence: CurrentStagingResearchIndexPromotionEvidence,
    ) -> CurrentStagingResearchIndexPromotionAuthority | None: ...


class StagingResearchIndexPromotionAuthorityUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_promotion_authority_unavailable")


def resolve_staging_research_index_promotion_authority(
    actor: SessionPrincipal,
    evidence: CurrentStagingResearchIndexPromotionEvidence,
    authorities: StagingResearchIndexPromotionAuthorityResolver,
) -> CurrentStagingResearchIndexPromotionAuthority | None:
    """Resolve current authority without deriving it from session or evidence."""

    try:
        if (
            type(actor) is not SessionPrincipal
            or type(evidence) is not CurrentStagingResearchIndexPromotionEvidence
        ):
            raise StagingResearchIndexPromotionAuthorityUnavailable
        authority = authorities.resolve_current(actor, evidence)
        if authority is None:
            return None
        binding = evidence.binding.run
        if (
            type(authority) is not CurrentStagingResearchIndexPromotionAuthority
            or authority.actor_user_id != actor.user_id
            or authority.candidate_digest != binding.candidate_digest
            or authority.staging_origin != binding.staging_origin
        ):
            raise StagingResearchIndexPromotionAuthorityUnavailable
        return authority
    except StagingResearchIndexPromotionAuthorityUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    raise StagingResearchIndexPromotionAuthorityUnavailable from None
