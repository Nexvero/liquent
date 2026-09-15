"""Current-candidate resolution for persisted staging promotion evidence."""

from dataclasses import dataclass, field
import re
from typing import Protocol

from liquent_platform.application.staging_research_index_promotion_evidence import (
    StagingResearchIndexPromotionEvidenceBinding,
)


class StagingResearchIndexPromotionEvidenceReader(Protocol):
    def resolve(
        self, evidence_digest: str
    ) -> StagingResearchIndexPromotionEvidenceBinding | None: ...


class CurrentStagingResearchIndexCandidateResolver(Protocol):
    def resolve_current(self, staging_origin: str) -> str | None: ...


@dataclass(frozen=True, slots=True)
class CurrentStagingResearchIndexPromotionEvidence:
    binding: StagingResearchIndexPromotionEvidenceBinding = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.binding) is not StagingResearchIndexPromotionEvidenceBinding:
            raise ValueError("exact staging promotion evidence binding is required")

    def __repr__(self) -> str:
        return "CurrentStagingResearchIndexPromotionEvidence()"


class CurrentStagingResearchIndexPromotionEvidenceUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("current_staging_research_index_promotion_evidence_unavailable")


def resolve_current_staging_research_index_promotion_evidence(
    evidence_digest: str,
    evidence: StagingResearchIndexPromotionEvidenceReader,
    candidates: CurrentStagingResearchIndexCandidateResolver,
) -> CurrentStagingResearchIndexPromotionEvidence | None:
    """Resolve evidence only while its candidate remains current at its origin."""

    try:
        binding = evidence.resolve(evidence_digest)
        if binding is None:
            return None
        if (
            type(binding) is not StagingResearchIndexPromotionEvidenceBinding
            or binding.evidence_digest != evidence_digest
        ):
            raise CurrentStagingResearchIndexPromotionEvidenceUnavailable
        current = candidates.resolve_current(binding.run.staging_origin)
        if current is None:
            return None
        if type(current) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", current) is None:
            raise CurrentStagingResearchIndexPromotionEvidenceUnavailable
        if current != binding.run.candidate_digest:
            return None
        return CurrentStagingResearchIndexPromotionEvidence(binding)
    except CurrentStagingResearchIndexPromotionEvidenceUnavailable as error:
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        pass
    raise CurrentStagingResearchIndexPromotionEvidenceUnavailable from None
