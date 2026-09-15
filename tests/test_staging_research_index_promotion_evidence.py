from dataclasses import replace
from datetime import timedelta

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexCheckOutcome,
)
from liquent_platform.application.staging_research_index_evidence_codec import (
    encode_staging_research_index_evidence,
)
from liquent_platform.application.staging_research_index_promotion_eligibility import (
    StagingResearchIndexPromotionEligibility,
)
from liquent_platform.application.staging_research_index_promotion_evidence import (
    StagingResearchIndexPromotionEvidenceBinding,
    bind_staging_research_index_promotion_evidence,
)
from liquent_platform.application.staging_research_index_stage_handoff import (
    StagingResearchIndexStageHandoff,
)
from tests.test_staging_research_index_evidence_codec import RUN, _handoffs


def test_binds_exact_eligibility_to_canonical_accepted_evidence() -> None:
    evidence = encode_staging_research_index_evidence(_handoffs())
    binding = bind_staging_research_index_promotion_evidence(
        StagingResearchIndexPromotionEligibility(RUN), evidence
    )
    assert type(binding) is StagingResearchIndexPromotionEvidenceBinding
    assert binding.run == RUN
    assert binding.evidence_digest.startswith("sha256:")
    assert len(binding.evidence_digest) == 71


def test_same_evidence_has_stable_binding_digest() -> None:
    evidence = encode_staging_research_index_evidence(_handoffs())
    eligibility = StagingResearchIndexPromotionEligibility(RUN)
    first = bind_staging_research_index_promotion_evidence(eligibility, evidence)
    second = bind_staging_research_index_promotion_evidence(eligibility, evidence)
    assert first == second


def test_mismatched_run_is_rejected() -> None:
    eligibility = StagingResearchIndexPromotionEligibility(
        replace(RUN, observed_at=RUN.observed_at + timedelta(seconds=1))
    )
    with pytest.raises(ValueError, match="accepted staging promotion evidence"):
        bind_staging_research_index_promotion_evidence(
            eligibility, encode_staging_research_index_evidence(_handoffs())
        )


def test_nonaccepted_evidence_is_rejected() -> None:
    handoffs = list(_handoffs())
    last = handoffs[-1]
    classification = replace(
        last.classifications[0], outcome=StagingResearchIndexCheckOutcome.FAILED
    )
    handoffs[-1] = StagingResearchIndexStageHandoff(
        last.run, last.stage, (classification,)
    )
    with pytest.raises(ValueError):
        bind_staging_research_index_promotion_evidence(
            StagingResearchIndexPromotionEligibility(RUN),
            encode_staging_research_index_evidence(tuple(handoffs)),
        )


def test_noncanonical_or_untyped_input_is_rejected() -> None:
    eligibility = StagingResearchIndexPromotionEligibility(RUN)
    with pytest.raises(ValueError):
        bind_staging_research_index_promotion_evidence(eligibility, b"{}\n")
    with pytest.raises(ValueError, match="exact staging promotion eligibility"):
        bind_staging_research_index_promotion_evidence(  # type: ignore[arg-type]
            object(), encode_staging_research_index_evidence(_handoffs())
        )


def test_representation_hides_run_and_digest() -> None:
    binding = bind_staging_research_index_promotion_evidence(
        StagingResearchIndexPromotionEligibility(RUN),
        encode_staging_research_index_evidence(_handoffs()),
    )
    assert repr(binding) == "StagingResearchIndexPromotionEvidenceBinding()"
    assert binding.evidence_digest not in repr(binding)
    assert RUN.candidate_digest not in repr(binding)
    assert not hasattr(binding, "promote")
