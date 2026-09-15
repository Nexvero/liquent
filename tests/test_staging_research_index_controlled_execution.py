from datetime import UTC, datetime

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceOutcome,
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
)
from liquent_platform.application.staging_research_index_controlled_execution import (
    StagingResearchIndexControlledExecutionUnavailable,
    execute_controlled_staging_research_index_acceptance,
)
from liquent_platform.application.staging_research_index_fixture_control import (
    RestoredStagingResearchIndexFixture,
    RevokedStagingResearchIndexFixture,
    StagingResearchIndexFixtureId,
    StagingResearchIndexFixtureRevision,
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


RUN = StagingResearchIndexAcceptanceRun(
    "sha256:" + "8" * 64,
    "https://staging.liquent.ai",
    datetime(2026, 9, 15, 19, tzinfo=UTC),
)
FIXTURE = StagingResearchIndexFixtureId("controlled-fixture-2685")
ACTIVE = StagingResearchIndexFixtureRevision("active-revision-2685")
REVOKED = RevokedStagingResearchIndexFixture(
    FIXTURE, ACTIVE, StagingResearchIndexFixtureRevision("revoked-revision-2685")
)
RESTORED = RestoredStagingResearchIndexFixture(
    FIXTURE, REVOKED.revoked_revision,
    StagingResearchIndexFixtureRevision("restored-revision-2685"),
)


def _session(number: int) -> OpaqueStagingResearchSession:
    return OpaqueStagingResearchSession(f"opaque-session-2685-{number}")


SESSIONS = {
    StagingResearchIndexAcquisitionStage.BASELINE: {
        StagingResearchIndexCredentialSlot.EMPTY_WORKSPACE_READER: _session(1),
        StagingResearchIndexCredentialSlot.VISIBLE_WORKSPACE_READER: _session(2),
        StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER: _session(3),
    },
    StagingResearchIndexAcquisitionStage.AFTER_REVOCATION: {
        StagingResearchIndexCredentialSlot.REVOCATION_FIXTURE_READER: _session(3),
    },
    StagingResearchIndexAcquisitionStage.UNAVAILABILITY: {
        StagingResearchIndexCredentialSlot.UNAVAILABLE_FIXTURE_READER: _session(4),
    },
}


class FixtureControl:
    def __init__(self, events: list[str], *, bad_restore: bool = False) -> None:
        self.events = events
        self.bad_restore = bad_restore

    def revoke(self, fixture_id, revision):
        self.events.append("revoke")
        assert (fixture_id, revision) == (FIXTURE, ACTIVE)
        return REVOKED

    def restore(self, revoked):
        self.events.append("restore")
        assert revoked is REVOKED
        if self.bad_restore:
            return RestoredStagingResearchIndexFixture(
                StagingResearchIndexFixtureId("different-fixture-2685"),
                REVOKED.revoked_revision,
                RESTORED.restored_revision,
            )
        return RESTORED


class Acquisition:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def acquire(self, request, session):
        event = (
            "after_revocation"
            if request.phase is StagingResearchIndexRequestPhase.AFTER_REVOCATION
            else "unavailability"
            if request.check is StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE
            else "baseline"
        )
        if not self.events or self.events[-1] != event:
            self.events.append(event)
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
        if request.check is StagingResearchIndexCheck.AUTHORIZED_EMPTY:
            return StagingResearchIndexResponse(
                200, (("content-type", "text/html"),),
                b"No Research jobs are available.",
            )
        if request.check is StagingResearchIndexCheck.SECURITY_HEADERS:
            return StagingResearchIndexResponse(
                200,
                (("cache-control", "no-store"), ("referrer-policy", "no-referrer")),
                b"<li><span>job</span> <span>running</span> "
                b'<time datetime="now">now</time></li>',
            )
        return StagingResearchIndexResponse(
            200, (("content-type", "text/html"),),
            b"<li><span>job</span> <span>running</span> "
            b'<time datetime="now">now</time></li>',
        )


def _execute(tmp_path, control, acquisition, sessions=SESSIONS):
    directory = tmp_path / "evidence"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    target = directory / "acceptance.json"
    result = execute_controlled_staging_research_index_acceptance(
        run=RUN, evidence_path=target, fixture_id=FIXTURE,
        expected_active_revision=ACTIVE, revoker=control, restorer=control,
        acquisition=acquisition, sessions=sessions,
    )
    return target, result


def test_executes_closed_order_restores_then_publishes(tmp_path) -> None:
    events: list[str] = []
    target, result = _execute(
        tmp_path, FixtureControl(events), Acquisition(events)
    )
    assert events == ["baseline", "revoke", "after_revocation", "restore", "unavailability"]
    assert result.outcome is StagingResearchIndexAcceptanceOutcome.ACCEPTED
    assert len(read_staging_research_index_evidence(target)) == 3


def test_invalid_restore_prevents_evidence_and_is_detail_free(tmp_path) -> None:
    events: list[str] = []
    directory = tmp_path / "evidence"
    directory.mkdir(mode=0o700)
    target = directory / "acceptance.json"
    with pytest.raises(StagingResearchIndexControlledExecutionUnavailable) as raised:
        execute_controlled_staging_research_index_acceptance(
            run=RUN, evidence_path=target, fixture_id=FIXTURE,
            expected_active_revision=ACTIVE,
            revoker=FixtureControl(events, bad_restore=True),
            restorer=FixtureControl(events, bad_restore=True),
            acquisition=Acquisition(events), sessions=SESSIONS,
        )
    assert not target.exists()
    assert raised.value.__cause__ is None and raised.value.__context__ is None


def test_inexact_session_inventory_mutates_nothing(tmp_path) -> None:
    events: list[str] = []
    sessions = dict(SESSIONS)
    sessions.pop(StagingResearchIndexAcquisitionStage.AFTER_REVOCATION)
    with pytest.raises(StagingResearchIndexControlledExecutionUnavailable):
        _execute(tmp_path, FixtureControl(events), Acquisition(events), sessions)
    assert events == []
