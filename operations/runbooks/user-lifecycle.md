# Offline user lifecycle management

This procedure applies regular LQ-223 user lifecycle decisions from a
supervised owner-only operator context. It is not bootstrap or recovery.

## Preconditions

- The database is migrated and reachable from the controlled environment.
- The actor is an active internal user with active user-lifecycle authority.
- The current complete user-inventory revision was independently obtained.
- The private working directory uses `umask 077`.

Never place the database URL, internal identifiers, request, or result in shell
history, tickets, chat, logs, images, or deployment variables.

## Stable change identity

Generate once and preserve the value with the reviewed request:

```text
liquent-user-lifecycle new-change-id
```

Do not replace this ID after a timeout or uncertain result. Exact retries use
the unchanged request and a new empty result path.

## Private database URL file

Write only the SQLAlchemy PostgreSQL URL to an owner-readable regular file.
The tool rejects symlinks and group/world-readable files and never migrates.

## Create an active user

```json
{
  "actor_user_id": "ACTIVE_INTERNAL_ACTOR_ID",
  "change_id": "PRESERVED_CHANGE_ID",
  "expected_revision": "EXACT_CURRENT_USER_REVISION"
}
```

The generated user ID is returned only in the private result. No identity,
membership, role, workspace, permission, session, or authority is created.

## Deactivate or reactivate

Use the `deactivate` or `reactivate` command with exactly:

```json
{
  "actor_user_id": "ACTIVE_INTERNAL_ACTOR_ID",
  "change_id": "PRESERVED_CHANGE_ID",
  "target_user_id": "EXISTING_INTERNAL_USER_ID",
  "expected_revision": "EXACT_CURRENT_USER_REVISION"
}
```

Deactivation succeeds only after all live dependencies and management
authorities have been drained. The operator performs no cascade. Reactivation
restores only user status and no dependent access.

## Apply and interpret

```text
liquent-user-lifecycle create --database-url-file URL_FILE --request REQUEST --result-file NEW_RESULT
liquent-user-lifecycle deactivate --database-url-file URL_FILE --request REQUEST --result-file NEW_RESULT
liquent-user-lifecycle reactivate --database-url-file URL_FILE --request REQUEST --result-file NEW_RESULT
```

- `applied`, exit 0: committed or exact committed retry;
- `rejected`, exit 5: an authority or state precondition was not confirmed;
- detail-free input, conflict, or unavailable errors: exits 2, 3, or 4.

The owner-only result contains only change ID, resulting revision ID, and the
bound user ID. An existing result path is never overwritten.

After a confirmed outcome, retain evidence only in the approved restricted
record and remove temporary files through the approved secure procedure.
