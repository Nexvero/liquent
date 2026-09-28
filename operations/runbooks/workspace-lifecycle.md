# Offline workspace lifecycle management

This procedure applies regular LQ-224 workspace lifecycle decisions from a
supervised owner-only operator context. It is not bootstrap or recovery.

## Preconditions

- The database is migrated and reachable from the controlled environment.
- The actor is an active internal user with active workspace-lifecycle authority.
- The current complete workspace-inventory revision was independently obtained.
- A first onboarding manager is an existing active internal user.
- The private working directory uses `umask 077`.

Keep the database URL, internal identifiers, request, and result out of shell
history, tickets, chat, logs, images, and deployment variables.

## Stable change identity

Generate once and preserve the value with the reviewed request:

```text
liquent-workspace-lifecycle new-change-id
```

After an uncertain result, retry the unchanged request under the same ID and
use a new empty result path.

## Create an active workspace

```json
{
  "actor_user_id": "ACTIVE_INTERNAL_ACTOR_ID",
  "change_id": "PRESERVED_CHANGE_ID",
  "initial_onboarding_manager_user_id": "ACTIVE_INTERNAL_MANAGER_ID",
  "expected_revision": "EXACT_CURRENT_WORKSPACE_REVISION"
}
```

The system generates the workspace ID and returns it only in the owner-only
result. Creation binds the named first onboarding manager but creates no
membership, research capability, role, trust, or lifecycle authority.

## Terminally deactivate a workspace

```json
{
  "actor_user_id": "ACTIVE_INTERNAL_ACTOR_ID",
  "change_id": "PRESERVED_CHANGE_ID",
  "target_workspace_id": "EXISTING_INTERNAL_WORKSPACE_ID",
  "expected_revision": "EXACT_CURRENT_WORKSPACE_REVISION"
}
```

There is no reactivate command. Historical child facts remain retained and
become unusable through the inactive workspace; the operator does not cascade.

## Apply and interpret

```text
liquent-workspace-lifecycle create --database-url-file URL_FILE --request REQUEST --result-file NEW_RESULT
liquent-workspace-lifecycle deactivate --database-url-file URL_FILE --request REQUEST --result-file NEW_RESULT
```

- `applied`, exit 0: committed or exact committed retry;
- `rejected`, exit 5: an authority or state precondition was not confirmed;
- detail-free input, conflict, or unavailable errors: exits 2, 3, or 4.

The result contains only change ID, revision ID, and the system-bound workspace
ID. The tool rejects insecure inputs, never overwrites a result, never migrates,
and exposes no database or rejection detail.

After confirmation, retain evidence only in the approved restricted record and
remove temporary files through the approved secure procedure.
