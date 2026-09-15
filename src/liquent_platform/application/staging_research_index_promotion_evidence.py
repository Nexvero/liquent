"""Canonical evidence binding for non-authorizing staging eligibility."""

from dataclasses import dataclass, field
import hashlib
import re

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceRun,
)
from liquent_platform.application.staging_research_index_evidence_codec import (
    decode_staging_research_index_evidence,
)
from liquent_platform.application.staging_research_index_promotion_eligibility import (
    StagingResearchIndexPromotionEligibility,
)
from liquent_platform.application.staging_research_index_stage_handoff import (
    evaluate_staging_research_index_handoffs,
)


@dataclass(frozen=True, slots=True)
class StagingResearchIndexPromotionEvidenceBinding:
    run: StagingResearchIndexAcceptanceRun = field(repr=False)
    evidence_digest: str = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.run) is not StagingResearchIndexAcceptanceRun
            or type(self.evidence_digest) is not str
            or re.fullmatch(r"sha256:[0-9a-f]{64}", self.evidence_digest) is None
        ):
            raise ValueError("exact staging promotion evidence binding is required")

    def __repr__(self) -> str:
        return "StagingResearchIndexPromotionEvidenceBinding()"


def bind_staging_research_index_promotion_evidence(
    eligibility: StagingResearchIndexPromotionEligibility,
    evidence: bytes,
) -> StagingResearchIndexPromotionEvidenceBinding:
    """Bind eligibility only to canonical accepted evidence for the same run."""

    if type(eligibility) is not StagingResearchIndexPromotionEligibility:
        raise ValueError("exact staging promotion eligibility is required")
    handoffs = decode_staging_research_index_evidence(evidence)
    result = evaluate_staging_research_index_handoffs(handoffs)
    if (
        result.outcome is not StagingResearchIndexAcceptanceOutcome.ACCEPTED
        or result.run != eligibility.run
    ):
        raise ValueError("accepted staging promotion evidence is required")
    digest = "sha256:" + hashlib.sha256(evidence).hexdigest()
    return StagingResearchIndexPromotionEvidenceBinding(result.run, digest)
