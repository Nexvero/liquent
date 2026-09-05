# Offline workspace membership-authority lifecycle

This procedure anchors and manages membership-management authority for one
exact workspace. It is separate from ordinary membership and Research
permission management and is never an HTTP, startup, bootstrap, or recovery
path.

## Preconditions

- The database is already migrated.
- Initial membership-management authority exists for the target workspace.
- The actor, target, and workspace are reviewed internal facts.
- The actor and workspace are active and the actor currently holds active
  management authority in that exact workspace.
- Use a private temporary directory with `umask 077`.
- Keep database URL, requests, and results in owner-only regular files.
- Supply a new absent result path for every invocation.

Do not copy these files or their values to logs, chat, tickets, shell history,
deployment environments, or image layers.

## Generate one stable change ID

```text
liquent-membership-authority new-change-id
```

Preserve that ID in the exact reviewed request. A retry after an uncertain
outcome always reuses the unchanged request and never creates a replacement
change ID.

## Anchor one workspace

```json
{
  "actor_user_id": "ACTIVE_WORKSPACE_MANAGER_USER_ID",
  "change_id": "PRESERVED_ANCHOR_CHANGE_ID",
  "workspace_id": "EXACT_ACTIVE_WORKSPACE_ID"
}
```

```text
liquent-membership-authority anchor \
  --database-url-file DATABASE_URL_FILE \
  --request ANCHOR_REQUEST_FILE \
  --result-file ANCHOR_RESULT_FILE
```

The protected result carries only `change_id` and the first authority-set
`revision_id`. The operation snapshots every existing management-authority
fact in that workspace without changing status. Other workspaces are not
adopted or altered.

## Grant a workspace manager

```json
{
  "actor_user_id": "ACTIVE_WORKSPACE_MANAGER_USER_ID",
  "change_id": "NEW_PRESERVED_CHANGE_ID",
  "target_user_id": "ACTIVE_TARGET_USER_ID",
  "workspace_id": "EXACT_ACTIVE_WORKSPACE_ID",
  "intent": "grant",
  "expected_revision": "EXACT_CURRENT_AUTHORITY_SET_REVISION"
}
```

```text
liquent-membership-authority apply \
  --database-url-file DATABASE_URL_FILE \
  --request LIFECYCLE_REQUEST_FILE \
  --result-file LIFECYCLE_RESULT_FILE
```

Grant creates only the dedicated management authority in the named workspace.
It creates no membership, Research permission, onboarding authority, user,
workspace, or global trust authority.

## Deactivate and reactivate

Use `"intent":"deactivate"` for an active historical target and
`"intent":"reactivate"` for an inactive historical target. Every distinct
decision needs a new stable change ID and the exact current revision.

Before deactivating the last effective manager, first grant or reactivate a
second effective manager and use that resulting revision for deactivation. A
request that would leave the workspace without an effective manager is
neutrally rejected.

Authority in another workspace cannot authorize this request and cannot be
used as the resulting scope.

## Outcomes and retry

- `anchored` or `applied`, exit 0: committed or exact committed retry;
- `rejected`, exit 5: a neutral precondition was not confirmed;
- constant detail-free input, conflict, or unavailable error otherwise.

No console output contains actor, target, workspace, revision, change ID,
database URL, SQL, or inventory detail. Successful result files are atomically
written owner-only and never overwritten.

For an uncertain outcome, rerun the exact request with a new absent result
path. An exact retry returns the original revision even after later actor
authority revocation.

## Cleanup

Retain evidence only in the approved restricted record, then securely remove
temporary database URL, request, and result files according to local policy.

This operator does not bootstrap authority, recover lost authority, mutate
ordinary membership or permissions, change users or workspaces, migrate the
database, restart services, or expose a network endpoint.
