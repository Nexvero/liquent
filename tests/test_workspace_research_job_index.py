from datetime import datetime, timedelta, timezone
from inspect import signature

import pytest
from sqlalchemy import text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.ports import AuthorizedWorkspaceResearchJobIndex
from liquent_platform.identity.research import (
    JobId,
    ResearchJobClaimId,
    ResearchJobRevisionId,
    WorkspaceId,
)
from liquent_platform.identity.research_job import ResearchJobIndexItem
from liquent_platform.jobs.lifecycle import ResearchJobStatus
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.research_jobs import DatabaseResearchJobs

USER = UserId("index-user")
WORKSPACE = WorkspaceId("index-workspace")
OTHER_WORKSPACE = WorkspaceId("other-workspace")


def _store(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'index.db'}")
    upgrade_to_head(str(engine.url))
    store = DatabaseResearchJobs(
        engine,
        generate_job_id=lambda: JobId("unused-job"),
        generate_revision_id=lambda: ResearchJobRevisionId("unused-revision"),
        generate_claim_id=lambda: ResearchJobClaimId("unused-claim"),
        clock=lambda: datetime(2026, 9, 15, tzinfo=timezone.utc),
        lease_duration=timedelta(seconds=30),
    )
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:user,'active')"),
            {"user": USER.encode()},
        )
        for workspace in (WORKSPACE, OTHER_WORKSPACE):
            connection.execute(
                text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
                {"workspace": workspace.encode()},
            )
        connection.execute(
            text(
                "INSERT INTO workspace_memberships"
                " (user_id,workspace_id,status) VALUES (:user,:workspace,'active')"
            ),
            {"user": USER.encode(), "workspace": WORKSPACE.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO workspace_membership_permissions"
                " VALUES (:user,:workspace,'research:read')"
            ),
            {"user": USER.encode(), "workspace": WORKSPACE.encode()},
        )
    return engine, store


def _insert_job(
    engine,
    job_id: str,
    workspace_id: WorkspaceId,
    accepted_at: datetime,
    *,
    status: str = "queued",
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO research_jobs VALUES"
                " (:job,:revision,:actor,:workspace,'{}','backtest_result_v1',"
                " :status,:accepted,:updated)"
            ),
            {
                "job": job_id.encode(),
                "revision": f"revision-{job_id}".encode(),
                "actor": USER.encode(),
                "workspace": workspace_id.encode(),
                "status": status,
                "accepted": accepted_at,
                "updated": accepted_at,
            },
        )


def test_item_exposes_only_minimum_index_facts() -> None:
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)
    item = ResearchJobIndexItem(
        JobId("job-1"), ResearchJobStatus.QUEUED, now, now
    )

    assert item.status is ResearchJobStatus.QUEUED
    assert "job-1" not in repr(item)
    assert not hasattr(item, "workspace_id")
    assert not hasattr(item, "actor_user_id")
    assert not hasattr(item, "revision_id")
    with pytest.raises(ValueError):
        ResearchJobIndexItem(
            item.job_id,
            item.status,
            now,
            now - timedelta(seconds=1),
        )


def test_port_accepts_only_actor_and_system_resolved_workspace() -> None:
    assert list(
        signature(AuthorizedWorkspaceResearchJobIndex.list_jobs).parameters
    ) == ["self", "actor_user_id", "workspace_id"]


def test_index_is_workspace_bound_bounded_and_deterministic(tmp_path) -> None:
    engine, store = _store(tmp_path)
    base = datetime(2026, 9, 15, tzinfo=timezone.utc)
    _insert_job(engine, "job-a", WORKSPACE, base)
    _insert_job(engine, "job-b", WORKSPACE, base)
    _insert_job(engine, "job-new", WORKSPACE, base + timedelta(seconds=1))
    _insert_job(engine, "job-other", OTHER_WORKSPACE, base + timedelta(seconds=2))

    result = store.list_jobs(USER, WORKSPACE)

    assert tuple(item.job_id for item in result) == (
        JobId("job-new"),
        JobId("job-b"),
        JobId("job-a"),
    )
    assert all(type(item) is ResearchJobIndexItem for item in result)
    assert len(result) <= store.INDEX_LIMIT


def test_index_does_not_duplicate_jobs_for_read_and_write_authority(tmp_path) -> None:
    engine, store = _store(tmp_path)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO workspace_membership_permissions"
                " VALUES (:user,:workspace,'research:write')"
            ),
            {"user": USER.encode(), "workspace": WORKSPACE.encode()},
        )
    _insert_job(
        engine,
        "job-visible-once",
        WORKSPACE,
        datetime(2026, 9, 15, tzinfo=timezone.utc),
    )

    result = store.list_jobs(USER, WORKSPACE)

    assert tuple(item.job_id for item in result) == (JobId("job-visible-once"),)


def test_empty_authorized_workspace_is_successful(tmp_path) -> None:
    _, store = _store(tmp_path)

    assert store.list_jobs(USER, WORKSPACE) == ()


@pytest.mark.parametrize(
    "revocation",
    [
        "DELETE FROM workspace_membership_permissions",
        "UPDATE workspace_memberships SET status='inactive'",
        "UPDATE identity_users SET status='inactive'",
        "UPDATE identity_workspaces SET status='inactive'",
    ],
)
def test_current_revocation_hides_the_entire_index(tmp_path, revocation) -> None:
    engine, store = _store(tmp_path)
    _insert_job(
        engine,
        "job-visible-before-revocation",
        WORKSPACE,
        datetime(2026, 9, 15, tzinfo=timezone.utc),
    )
    assert store.list_jobs(USER, WORKSPACE)

    with engine.begin() as connection:
        connection.execute(text(revocation))

    assert store.list_jobs(USER, WORKSPACE) == ()
