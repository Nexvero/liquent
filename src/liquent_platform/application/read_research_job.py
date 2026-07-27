"""Authorized application read for one research job."""

from liquent_platform.application.authorize_research import (
    require_research_authorization,
)
from liquent_platform.identity.access import Permission
from liquent_platform.identity.ports import WorkspaceMembershipLookup
from liquent_platform.identity.research import JobId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.jobs.in_memory import InMemoryResearchJob, InMemoryResearchJobs


def get_authorized_research_job(
    jobs: InMemoryResearchJobs,
    memberships: WorkspaceMembershipLookup,
    principal: SessionPrincipal,
    job_id: JobId,
) -> InMemoryResearchJob:
    """Load a job and authorize read access against its stored workspace."""

    job = jobs.get(job_id)
    require_research_authorization(
        memberships,
        principal,
        job.snapshot.workspace_id,
        Permission.RESEARCH_READ,
    )
    return job
