from liquent_platform.identity.access import CurrentWorkspaceContext, UserId
from liquent_platform.identity.ports import CurrentWorkspaceContextLookup
from liquent_platform.identity.research import WorkspaceId


class StubCurrentWorkspaceContexts:
    def __init__(self, result: CurrentWorkspaceContext | None) -> None:
        self.result = result
        self.requested: UserId | None = None

    def resolve_current_workspace(
        self, user_id: UserId
    ) -> CurrentWorkspaceContext | None:
        self.requested = user_id
        return self.result


def _resolve(
    lookup: CurrentWorkspaceContextLookup, user_id: UserId
) -> CurrentWorkspaceContext | None:
    return lookup.resolve_current_workspace(user_id)


def test_lookup_uses_only_internal_actor_identity() -> None:
    context = CurrentWorkspaceContext(
        UserId("user-2656"), WorkspaceId("workspace-2656")
    )
    lookup = StubCurrentWorkspaceContexts(context)

    assert _resolve(lookup, context.user_id) is context
    assert lookup.requested == context.user_id


def test_absent_or_ambiguous_context_is_neutral_none() -> None:
    assert _resolve(StubCurrentWorkspaceContexts(None), UserId("user-2656")) is None
