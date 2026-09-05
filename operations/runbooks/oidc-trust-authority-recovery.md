# Offline OIDC trust-authority recovery

Use this emergency procedure only when the global OIDC trust-management scope
is already anchored and no existing active user can exercise its authority.
This is not a routine lifecycle, bootstrap, HTTP, startup, or deployment path.

## Preconditions and independent review

- Confirm through the approved security process that no effective global trust
  manager remains.
- Confirm the target is an active internal user with an existing inactive
  historical global trust-management authority.
- Obtain the exact current authority-set revision from protected prior evidence.
- If the current pointer is missing, use only the uniquely terminal last known
  revision reviewed from persistent decision evidence.
- Require the locally approved emergency authorization and separation of duties.
- Work in a private temporary directory with `umask 077`.

Possession of database access, this command, or an input file is not by itself
authorization. Never copy the database URL, IDs, request, or result into logs,
chat, tickets, shell history, deployment variables, or image layers.

## Generate and preserve a recovery ID

Generate exactly one ID for the reviewed recovery decision:

```text
liquent-oidc-trust-authority-recovery new-recovery-id
```

Preserve it in the approved request. Never replace it after timeout, lost
console output, or uncertain commit status.

## Prepare the owner-only request

```json
{
  "recovery_id": "PRESERVED_RECOVERY_ID",
  "target_user_id": "HISTORICALLY_AUTHORIZED_ACTIVE_TARGET_USER_ID",
  "expected_revision": "EXACT_CURRENT_OR_UNIQUELY_TERMINAL_REVISION_ID"
}
```

The request contains no actor, role, intent, status, Allow value, authority
list, provider configuration, or result revision. Unknown fields are rejected.

## Execute

Use an owner-only regular database URL file, owner-only request file, and a new
absent result path in an owner-only directory:

```text
liquent-oidc-trust-authority-recovery recover \
  --database-url-file DATABASE_URL_FILE \
  --request RECOVERY_REQUEST_FILE \
  --result-file RECOVERY_RESULT_FILE
```

`recovered` with exit 0 means the decision committed or an exact retry was
resolved. The protected 0600 result contains only `recovery_id` and resulting
`revision_id`.

`rejected` with exit 5 intentionally does not distinguish an effective
manager, ineligible target, stale revision, absent history, or another neutral
precondition. Input, conflict, and unavailable failures use constant codes.

## Uncertain outcome

Repeat the unchanged request with a new absent result path. Do not create a new
recovery ID, select another target, or alter the expected revision. Exact retry
returns the committed revision even if later state changed.

## Cleanup and follow-up

Move required evidence into the approved restricted security record and remove
all temporary files through the environment's approved secure procedure.

After recovery, use the ordinary lifecycle operator for reviewed manager
rotation. This command cannot create a user, activate a user, bootstrap or
anchor authority, mutate OIDC configuration, migrate schema, restart services,
or expose a network endpoint.
