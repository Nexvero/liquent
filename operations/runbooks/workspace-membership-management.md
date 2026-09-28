# Offline workspace membership management

This procedure bootstraps initial membership-management authority and applies
complete workspace membership snapshots. It is never an HTTP or startup path.

## Preconditions

- Use a migrated database and restricted operator host.
- Set `umask 077` in a private working directory.
- Store the database URL and every request as owner-only regular files.
- Use a new absent owner-only result path for each invocation.
- Review internal actor, target-user, workspace, expected revision, status, and
  every explicit permission before applying.

The command rejects symbolic links, unsafe input permissions, unsafe result
directories, and existing result files. It never migrates the database.

## Bootstrap first authority for one workspace

Create an owner-only request:

```json
{
  "user_id": "EXISTING_ACTIVE_INTERNAL_USER_ID",
  "workspace_id": "EXISTING_ACTIVE_INTERNAL_WORKSPACE_ID"
}
```

Apply it:

```text
liquent-membership-management bootstrap-authority \
  --database-url-file DATABASE_URL_FILE \
  --request BOOTSTRAP_REQUEST_FILE \
  --result-file BOOTSTRAP_RESULT_FILE
```

Recovery succeeds only for exactly one active authority in that workspace,
belonging to the same active user. Different, additional, or inactive authority
inventory remains neutrally rejected.

## Prepare stable membership change ID

Generate it exactly once:

```text
liquent-membership-management new-change-id
```

Preserve it in the reviewed request before applying. Reuse the exact request
after an uncertain outcome; never generate a replacement ID for a retry.

## Create or update an active membership

```json
{
  "actor_user_id": "ACTIVE_MANAGER_USER_ID",
  "change_id": "PRESERVED_CHANGE_ID",
  "target_user_id": "ACTIVE_TARGET_USER_ID",
  "workspace_id": "ACTIVE_WORKSPACE_ID",
  "expected_revision": null,
  "status": "active",
  "permissions": ["research:read", "research:write"]
}
```

Use `expected_revision: null` only for first creation. Every later change must
copy the exact `revision_id` from the prior protected result file.

Permission lists are complete snapshots, not patches. Omit a permission to
remove it. An empty active list creates or retains a membership with no
Research access. `research:write` is not expanded in persistence.

## Deactivate

Deactivation must use the exact current revision and an empty permission list:

```json
{
  "actor_user_id": "ACTIVE_MANAGER_USER_ID",
  "change_id": "NEW_PRESERVED_CHANGE_ID",
  "target_user_id": "ACTIVE_TARGET_USER_ID",
  "workspace_id": "ACTIVE_WORKSPACE_ID",
  "expected_revision": "EXACT_CURRENT_REVISION_ID",
  "status": "inactive",
  "permissions": []
}
```

Reactivation is a later active snapshot with another new change ID, the exact
inactive revision, and every newly desired permission explicitly listed.

## Apply a membership change

```text
liquent-membership-management apply \
  --database-url-file DATABASE_URL_FILE \
  --request MEMBERSHIP_REQUEST_FILE \
  --result-file MEMBERSHIP_RESULT_FILE
```

The protected result contains only `change_id` and resulting `revision_id`.
Preserve it for the next reviewed change.

## Outcomes

- `bootstrapped`, `recovered`, or `applied`, exit 0;
- `rejected`, exit 5 for neutral authority/foundation/revision/state rejection;
- constant detail-free input, conflict, or unavailable errors with non-zero
  exits.

No console output contains actor, target, workspace, revision, permission,
database URL, SQL, or stored inventory details.

After a technically uncertain apply, repeat the unchanged request with a new
absent result path. Exact retry returns the original revision even if authority
was revoked after commit.

## Cleanup

Move required evidence into the approved restricted record and securely remove
temporary DSN/request/result files using the approved procedure.

This tool does not create users or workspaces, onboard identities, mutate
management authority after bootstrap, activate OIDC Trust, restart services, or
expose a network endpoint.
