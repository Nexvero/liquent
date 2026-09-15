from dataclasses import replace
from datetime import UTC, datetime

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
)
from liquent_platform.application.staging_research_index_evidence_composition import (
    acquire_staging_research_index_stage_handoff,
    publish_staging_research_index_acceptance_evidence,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot,
    StagingResearchIndexRequestPhase,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponse,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    OpaqueStagingResearchSession,
    StagingResearchIndexAcquisitionStage,
)
from liquent_platform.transport.staging_research_index_evidence_reader import (
    read_staging_research_index_evidence,
)
from liquent_platform.transport.staging_research_index_evidence_writer import (
    StagingResearchIndexEvidenceStorageUnavailable,
)


RUN = StagingResearchIndexAcceptanceRun(
    "sha256:" + "7" * 64,
    "https://staging.liquent.ai",
    datetime(2026, 9, 15, 18, tzinfo=UTC),
)
SESSIONS = {
    slot: OpaqueStagingResearchSession("opaque-session-" + str(index))
    for index, slot in enumerate((
        StagingResearchIndexCredentialSlot.EMPTY_WORKSPACE_READER,
        StagingResearchIndexCredentialSlot.VISIBLE_WORKSPACE_READER,
        StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER,
        StagingResearchIndexCredentialSlot.UNAVAILABLE_FIXTURE_READER,
    ), start=1)
}


class Acquisition:
    def acquire(self, request, session):
        if request.check is StagingResearchIndexCheck.ANONYMOUS_CLOSED:
            return StagingResearchIndexResponse(404, (), b"")
        if request.check is StagingResearchIndexCheck.QUERY_REJECTED:
            return StagingResearchIndexResponse(400, (), b"")
        if request.check is StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE:
            return StagingResearchIndexResponse(
                303, (("location", "/login/unavailable"),), b""
            )
        if request.phase is StagingResearchIndexRequestPhase.AFTER_REVOCATION:
            return StagingResearchIndexResponse(404, (), b"")
        body = (
            b"No Research jobs are available."
            if request.check is StagingResearchIndexCheck.AUTHORIZED_EMPTY
            else b'<li><span>job</span> <span>running</span> '
                 b'<time datetime="now">now</time></li>'
        )
        headers = (("content-type", "text/html"),)
        if request.check is StagingResearchIndexCheck.SECURITY_HEADERS:
            headers = (
                ("cache-control", "no-store"),
                ("referrer-policy", "no-referrer"),
            )
        return StagingResearchIndexResponse(200, headers, body)


def _sessions(stage):
    if stage is StagingResearchIndexAcquisitionStage.BASELINE:
        slots = (
            StagingResearchIndexCredentialSlot.EMPTY_WORKSPACE_READER,
            StagingResearchIndexCredentialSlot.VISIBLE_WORKSPACE_READER,
            StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER,
        )
    elif stage is StagingResearchIndexAcquisitionStage.AFTER_REVOCATION:
        slots = (StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER,)
    else:
        slots = (StagingResearchIndexCredentialSlot.UNAVAILABLE_FIXTURE_READER,)
    return {slot: SESSIONS[slot] for slot in slots}


def _handoffs():
    return tuple(
        acquire_staging_research_index_stage_handoff(
            RUN, stage, Acquisition(), _sessions(stage)
        )
        for stage in StagingResearchIndexAcquisitionStage
    )


def test_each_stage_is_immediately_bound_to_the_run() -> None:
    for handoff in _handoffs():
        assert handoff.run is RUN
        assert handoff.stage in StagingResearchIndexAcquisitionStage


def test_complete_handoffs_are_published_and_read_back(tmp_path) -> None:
    directory = tmp_path / "evidence"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    target = directory / "acceptance.json"
    handoffs = _handoffs()
    result = publish_staging_research_index_acceptance_evidence(target, handoffs)
    assert result.outcome is StagingResearchIndexAcceptanceOutcome.ACCEPTED
    assert read_staging_research_index_evidence(target) == handoffs


def test_incomplete_or_cross_run_set_creates_no_file(tmp_path) -> None:
    directory = tmp_path / "evidence"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    target = directory / "acceptance.json"
    handoffs = _handoffs()
    another = replace(RUN, candidate_digest="sha256:" + "8" * 64)
    invalid_sets = (handoffs[:-1], (
        handoffs[0], replace(handoffs[1], run=another), handoffs[2]
    ))
    for invalid in invalid_sets:
        with pytest.raises(ValueError):
            publish_staging_research_index_acceptance_evidence(target, invalid)
        assert not target.exists()


def test_existing_evidence_is_not_replaced(tmp_path) -> None:
    directory = tmp_path / "evidence"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    target = directory / "acceptance.json"
    target.write_bytes(b"existing")
    with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
        publish_staging_research_index_acceptance_evidence(target, _handoffs())
    assert target.read_bytes() == b"existing"
