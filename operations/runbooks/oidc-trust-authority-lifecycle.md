# Offline OIDC trust-authority lifecycle

This procedure anchors and manages the global OIDC trust-management authority
through the LQ-213 and LQ-214 persistence boundaries. It is not an HTTP,
startup, deployment, bootstrap, or recovery path.

## Preconditions

- The database is already migrated.
- Initial global trust authority already exists through the approved bootstrap.
- The selected actor is an active internal user with current active global
  trust-management authority.
- Work from a private temporary directory with `umask 077`.
- Store the database URL, requests, and results as owner-only regular files.
- Use a new absent result path for every invocation.

Never place the database URL, internal IDs, requests, or results in shell
history, tickets, chat, deployment variables, image layers, or application
logs.

## Generate a stable change ID

Generate one opaque ID for each distinct decision:

```text
liquent-oidc-trust-authority new-change-id
```

Insert it into the reviewed request and preserve that exact request. If an
outcome is technically uncertain, retry with the same change ID and unchanged
content. Never generate a replacement merely because output was lost.

## Anchor existing bootstrap authority

Create an owner-only request:

```json
{
  "actor_user_id": "ACTIVE_BOOTSTRAP_MANAGER_USER_ID",
  "change_id": "PRESERVED_ANCHOR_CHANGE_ID"
}
```

Run:

```text
liquent-oidc-trust-authority anchor \
  --database-url-file DATABASE_URL_FILE \
  --request ANCHOR_REQUEST_FILE \
  --result-file ANCHOR_RESULT_FILE
```

The protected result contains only `change_id` and the first `revision_id`.
Anchoring changes no authority status. A scope that is already anchored is
neutrally rejected unless the request is the exact committed retry.

## Grant another manager

Use the exact revision from the anchor or prior lifecycle result:

```json
{
  "actor_user_id": "ACTIVE_MANAGER_USER_ID",
  "change_id": "NEW_PRESERVED_CHANGE_ID",
  "target_user_id": "ACTIVE_TARGET_USER_ID",
  "intent": "grant",
  "expected_revision": "EXACT_CURRENT_AUTHORITY_SET_REVISION"
}
```

Apply with:

```text
liquent-oidc-trust-authority apply \
  --database-url-file DATABASE_URL_FILE \
  --request LIFECYCLE_REQUEST_FILE \
  --result-file LIFECYCLE_RESULT_FILE
```

Grant is only for a target with no prior authority history. It creates no user,
workspace, provider configuration, membership, or research permission.

## Deactivate or reactivate

For deactivation, use `"intent":"deactivate"`; for historical reactivation,
use `"intent":"reactivate"`. Both require a new stable change ID and the exact
current revision.

Grant or reactivate a second effective manager before deactivating the current
last manager. The persistence boundary rejects any operation that would leave
no effective active manager.

## Outcomes and retry

- `anchored` or `applied`, exit 0: committed or exact committed retry;
- `rejected`, exit 5: authority, foundation, revision, transition, or lockout
  precondition was not confirmed;
- constant input, conflict, or unavailable code with non-zero exit.

Console output contains no actor, target, revision, change ID, database, SQL,
or stored inventory detail. The protected result is written atomically with
mode 0600 and is never overwritten.

After technical uncertainty, repeat the exact request with a new absent result
path. Do not edit the expected revision or change ID.

## Cleanup

Move required evidence into the approved restricted security record. Remove
temporary database URL, request, and result files through the environment's
approved secure procedure.

This tool cannot bootstrap authority, recover a scope with no effective
manager, alter user status, mutate OIDC configuration, migrate schema, restart
services, or expose a network endpoint.
