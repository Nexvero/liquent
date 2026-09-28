from dataclasses import replace
from datetime import UTC, datetime
import json

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
)
from liquent_platform.application.staging_research_index_evidence_codec import (
    decode_staging_research_index_evidence,
    encode_staging_research_index_evidence,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexRequestPhase,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponseClassification,
)
from liquent_platform.application.staging_research_index_stage_handoff import (
    StagingResearchIndexStageHandoff,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    StagingResearchIndexAcquisitionStage,
)


RUN = StagingResearchIndexAcceptanceRun(
    "sha256:" + "4" * 64,
    "https://staging.liquent.ai",
    datetime(2026, 9, 15, 15, tzinfo=UTC),
)


def _classification(check, phase, outcome=StagingResearchIndexCheckOutcome.PASSED):
    return StagingResearchIndexResponseClassification(check, phase, outcome)


def _handoffs():
    baseline = tuple(
        _classification(check, StagingResearchIndexRequestPhase.SINGLE)
        for check in StagingResearchIndexCheck
        if check not in {
            StagingResearchIndexCheck.REVOCATION_FRESH,
            StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE,
        }
    ) + (_classification(
        StagingResearchIndexCheck.REVOCATION_FRESH,
        StagingResearchIndexRequestPhase.BEFORE_REVOCATION,
    ),)
    return (
        StagingResearchIndexStageHandoff(
            RUN, StagingResearchIndexAcquisitionStage.BASELINE, baseline
        ),
        StagingResearchIndexStageHandoff(
            RUN,
            StagingResearchIndexAcquisitionStage.AFTER_REVOCATION,
            (_classification(
                StagingResearchIndexCheck.REVOCATION_FRESH,
                StagingResearchIndexRequestPhase.AFTER_REVOCATION,
            ),),
        ),
        StagingResearchIndexStageHandoff(
            RUN,
            StagingResearchIndexAcquisitionStage.UNAVAILABILITY,
            (_classification(
                StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE,
                StagingResearchIndexRequestPhase.SINGLE,
            ),),
        ),
    )


def test_round_trip_is_canonical_and_order_neutral() -> None:
    handoffs = _handoffs()
    reordered = tuple(
        replace(handoff, classifications=tuple(reversed(handoff.classifications)))
        for handoff in reversed(handoffs)
    )
    encoded = encode_staging_research_index_evidence(reordered)
    assert encoded == encode_staging_research_index_evidence(handoffs)
    assert encoded.endswith(b"\n")
    assert encode_staging_research_index_evidence(
        decode_staging_research_index_evidence(encoded)
    ) == encoded
    assert b"session" not in encoded and b"credential" not in encoded


def test_recorded_outcome_is_recomputed() -> None:
    encoded = encode_staging_research_index_evidence(_handoffs())
    document = json.loads(encoded)
    document["outcome"] = "rejected"
    changed = (json.dumps(
        document, sort_keys=True, separators=(",", ":")
    ) + "\n").encode()
    with pytest.raises(ValueError):
        decode_staging_research_index_evidence(changed)


@pytest.mark.parametrize("mutation", ("unknown", "spacing", "no_newline"))
def test_noncanonical_or_extended_evidence_is_rejected(mutation) -> None:
    encoded = encode_staging_research_index_evidence(_handoffs())
    if mutation == "unknown":
        document = json.loads(encoded)
        document["extra"] = True
        changed = (json.dumps(
            document, sort_keys=True, separators=(",", ":")
        ) + "\n").encode()
    elif mutation == "spacing":
        changed = encoded.replace(b'"version":1', b'"version": 1')
    else:
        changed = encoded.rstrip(b"\n")
    with pytest.raises(ValueError):
        decode_staging_research_index_evidence(changed)


def test_malformed_and_oversized_evidence_is_rejected_detail_free() -> None:
    for evidence in (b"", b"{}\n", b"\xff\n", b"x" * 8_193):
        with pytest.raises(ValueError):
            decode_staging_research_index_evidence(evidence)


def test_unavailable_outcome_survives_round_trip() -> None:
    handoffs = list(_handoffs())
    handoffs[-1] = replace(
        handoffs[-1],
        classifications=(replace(
            handoffs[-1].classifications[0],
            outcome=StagingResearchIndexCheckOutcome.UNAVAILABLE,
        ),),
    )
    encoded = encode_staging_research_index_evidence(tuple(handoffs))
    assert b'"outcome":"unavailable"' in encoded
    assert decode_staging_research_index_evidence(encoded)[-1] == handoffs[-1]
