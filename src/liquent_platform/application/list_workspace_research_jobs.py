"""Compose current workspace research-read authority with the job index."""

from liquent_platform.application.resolve_workspace_research_read import (
    resolve_workspace_research_read,
)
from liquent_platform.identity.ports import (
    AuthorizedWorkspaceResearchJobIndex,
    CurrentWorkspaceContextLookup,
    WorkspaceMembershipLookup,
)
from liquent_platform.identity.research_job import ResearchJobIndexItem
from liquent_platform.identity.session import SessionPrincipal


def list_current_workspace_research_jobs(
    contexts: CurrentWorkspaceContextLookup,
    memberships: WorkspaceMembershipLookup,
    jobs: AuthorizedWorkspaceResearchJobIndex,
    principal: SessionPrincipal,
) -> tuple[ResearchJobIndexItem, ...] | None:
    """Return the authorized index, or neutral absence when access is denied."""

    context = resolve_workspace_research_read(contexts, memberships, principal)
    if context is None:
        return None
    return jobs.list_jobs(principal.user_id, context.workspace_id)
