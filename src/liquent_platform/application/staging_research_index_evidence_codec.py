"""Canonical codec for sanitized staging Research-index stage evidence."""

from datetime import datetime
import json

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexRequestPhase,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponseClassification,
)
from liquent_platform.application.staging_research_index_stage_handoff import (
    StagingResearchIndexStageHandoff,
    evaluate_staging_research_index_handoffs,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    StagingResearchIndexAcquisitionStage,
)


_VERSION = 1
_CHECK_ORDER = {check: index for index, check in enumerate(StagingResearchIndexCheck)}
_PHASE_ORDER = {
    phase: index for index, phase in enumerate(StagingResearchIndexRequestPhase)
}


def encode_staging_research_index_evidence(
    handoffs: tuple[StagingResearchIndexStageHandoff, ...],
) -> bytes:
    """Encode one exact validated handoff set as canonical ASCII JSON."""

    result = evaluate_staging_research_index_handoffs(handoffs)
    by_stage = {handoff.stage: handoff for handoff in handoffs}
    run = result.run
    document = {
        "candidate_digest": run.candidate_digest,
        "observed_at": run.observed_at.isoformat().replace("+00:00", "Z"),
        "outcome": result.outcome.value,
        "stages": [
            {
                "classifications": [
                    {
                        "check": item.check.value,
                        "outcome": item.outcome.value,
                        "phase": item.phase.value,
                    }
                    for item in sorted(
                        by_stage[stage].classifications,
                        key=lambda value: (
                            _CHECK_ORDER[value.check], _PHASE_ORDER[value.phase]
                        ),
                    )
                ],
                "stage": stage.value,
            }
            for stage in StagingResearchIndexAcquisitionStage
        ],
        "staging_origin": run.staging_origin,
        "version": _VERSION,
    }
    return (
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def decode_staging_research_index_evidence(
    evidence: bytes,
) -> tuple[StagingResearchIndexStageHandoff, ...]:
    """Decode only canonical evidence that reproduces its bound evaluation."""

    if type(evidence) is not bytes or not evidence or len(evidence) > 8_192:
        raise ValueError("canonical bounded evidence is required")
    try:
        document = json.loads(evidence.decode("ascii"))
        if type(document) is not dict or set(document) != {
            "candidate_digest", "observed_at", "outcome", "stages",
            "staging_origin", "version",
        } or document["version"] != _VERSION or type(document["stages"]) is not list:
            raise ValueError
        observed_at = datetime.fromisoformat(document["observed_at"].replace("Z", "+00:00"))
        run = StagingResearchIndexAcceptanceRun(
            document["candidate_digest"], document["staging_origin"], observed_at
        )
        handoffs = tuple(
            StagingResearchIndexStageHandoff(
                run,
                StagingResearchIndexAcquisitionStage(stage_document["stage"]),
                tuple(
                    StagingResearchIndexResponseClassification(
                        StagingResearchIndexCheck(item["check"]),
                        StagingResearchIndexRequestPhase(item["phase"]),
                        StagingResearchIndexCheckOutcome(item["outcome"]),
                    )
                    for item in stage_document["classifications"]
                    if type(item) is dict
                    and set(item) == {"check", "outcome", "phase"}
                ),
            )
            for stage_document in document["stages"]
            if type(stage_document) is dict
            and set(stage_document) == {"classifications", "stage"}
            and type(stage_document["classifications"]) is list
        )
        result = evaluate_staging_research_index_handoffs(handoffs)
        if document["outcome"] != result.outcome.value:
            raise ValueError
    except Exception as exc:
        raise ValueError("staging evidence is invalid") from exc
    if encode_staging_research_index_evidence(handoffs) != evidence:
        raise ValueError("staging evidence is not canonical")
    return handoffs
