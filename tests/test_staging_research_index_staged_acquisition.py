from datetime import UTC, datetime

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexCredentialSlot,
    StagingResearchIndexRequestPhase,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponse,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    StagingResearchIndexAcquisitionStage,
    acquire_staging_research_index_stage,
)
from liquent_platform.transport.staging_research_index_http_acquisition import (
    OpaqueStagingResearchSession,
)


RUN = StagingResearchIndexAcceptanceRun(
    "sha256:" + "1" * 64,
    "https://staging.liquent.ai",
    datetime(2026, 9, 15, 13, tzinfo=UTC),
)
SESSIONS = {
    slot: OpaqueStagingResearchSession("opaque-session-" + str(number))
    for number, slot in enumerate((
        StagingResearchIndexCredentialSlot.EMPTY_WORKSPACE_READER,
        StagingResearchIndexCredentialSlot.VISIBLE_WORKSPACE_READER,
        StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER,
        StagingResearchIndexCredentialSlot.UNAVAILABLE_FIXTURE_READER,
    ), start=1)
}


class Acquisition:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def acquire(self, request, session):
        self.calls.append((request.check, request.phase, session))
        if self.fail:
            raise RuntimeError("private transport detail")
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
            else b'<li><span>job</span> <span>running</span> <time datetime="now">now</time></li>'
        )
        headers = (("content-type", "text/html"),)
        if request.check is StagingResearchIndexCheck.SECURITY_HEADERS:
            headers = (
                ("cache-control", "no-store"),
                ("referrer-policy", "no-referrer"),
            )
        return StagingResearchIndexResponse(200, headers, body)


def _stage_sessions(stage):
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


@pytest.mark.parametrize(
    ("stage", "count"),
    (
        (StagingResearchIndexAcquisitionStage.BASELINE, 7),
        (StagingResearchIndexAcquisitionStage.AFTER_REVOCATION, 1),
        (StagingResearchIndexAcquisitionStage.UNAVAILABILITY, 1),
    ),
)
def test_each_stage_is_closed_and_immediately_classified(stage, count) -> None:
    acquisition = Acquisition()
    results = acquire_staging_research_index_stage(
        RUN, stage, acquisition, _stage_sessions(stage)
    )
    assert len(results) == count
    assert len(acquisition.calls) == count
    assert all(item.outcome is StagingResearchIndexCheckOutcome.PASSED for item in results)


def test_anonymous_calls_receive_no_session() -> None:
    acquisition = Acquisition()
    acquire_staging_research_index_stage(
        RUN,
        StagingResearchIndexAcquisitionStage.BASELINE,
        acquisition,
        _stage_sessions(StagingResearchIndexAcquisitionStage.BASELINE),
    )
    calls = {check: session for check, _, session in acquisition.calls}
    assert calls[StagingResearchIndexCheck.ANONYMOUS_CLOSED] is None
    assert calls[StagingResearchIndexCheck.QUERY_REJECTED] is None


def test_transport_fault_becomes_only_unavailable_classifications() -> None:
    results = acquire_staging_research_index_stage(
        RUN,
        StagingResearchIndexAcquisitionStage.AFTER_REVOCATION,
        Acquisition(fail=True),
        _stage_sessions(StagingResearchIndexAcquisitionStage.AFTER_REVOCATION),
    )
    assert results[0].outcome is StagingResearchIndexCheckOutcome.UNAVAILABLE
    assert "private" not in repr(results)


def test_missing_or_extra_sessions_fail_before_acquisition() -> None:
    acquisition = Acquisition()
    stage = StagingResearchIndexAcquisitionStage.AFTER_REVOCATION
    with pytest.raises(ValueError):
        acquire_staging_research_index_stage(RUN, stage, acquisition, {})
    with pytest.raises(ValueError):
        acquire_staging_research_index_stage(RUN, stage, acquisition, SESSIONS)
    assert acquisition.calls == []
