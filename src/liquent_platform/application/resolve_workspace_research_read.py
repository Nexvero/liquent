"""Resolve a current workspace only when current research-read access exists."""

from liquent_platform.application.authorize_research import authorize_research
from liquent_platform.identity.access import CurrentWorkspaceContext, Permission
from liquent_platform.identity.ports import (
    CurrentWorkspaceContextLookup,
    WorkspaceMembershipLookup,
)
from liquent_platform.identity.session import SessionPrincipal


def resolve_workspace_research_read(
    contexts: CurrentWorkspaceContextLookup,
    memberships: WorkspaceMembershipLookup,
    principal: SessionPrincipal,
) -> CurrentWorkspaceContext | None:
    """Return one current context only after a fresh research-read decision."""

    context = contexts.resolve_current_workspace(principal.user_id)
    if context is None or context.user_id != principal.user_id:
        return None
    if not authorize_research(
        memberships,
        principal,
        context.workspace_id,
        Permission.RESEARCH_READ,
    ):
        return None
    return context
