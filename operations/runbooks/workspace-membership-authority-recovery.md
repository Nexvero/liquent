# Offline workspace membership-authority recovery

Use this emergency procedure only for one already anchored workspace whose
membership-management authority has no effective active manager. It is
separate from ordinary lifecycle, membership, permissions, bootstrap, HTTP,
startup, and deployment.

## Preconditions and independent review

- Confirm no effective manager remains in the exact workspace.
- Confirm the workspace is active.
- Confirm the target is an active internal user with existing inactive
  historical management authority in that same workspace.
- Obtain the exact current authority-set revision, or only when its pointer is
  missing the uniquely terminal last known revision from protected evidence.
- Complete the locally required emergency approval and separation of duties.
- Use a private temporary directory with `umask 077`.

Authority in another workspace, database possession, or access to this command
is not recovery authorization. Keep all values out of logs, chat, tickets,
shell history, environment variables, and image layers.

## Generate one recovery ID

```text
liquent-membership-authority-recovery new-recovery-id
```

Record it exactly once in the reviewed request and preserve the unchanged file
until the outcome is certain.

## Prepare the owner-only request

```json
{
  "recovery_id": "PRESERVED_RECOVERY_ID",
  "target_user_id": "HISTORICALLY_AUTHORIZED_ACTIVE_TARGET_USER_ID",
  "workspace_id": "EXACT_ACTIVE_WORKSPACE_ID",
  "expected_revision": "EXACT_CURRENT_OR_UNIQUELY_TERMINAL_REVISION_ID"
}
```

Actor, intent, role, status, permission, Allow value, authority list, and
resulting revision are forbidden inputs.

## Execute

Supply owner-only regular database URL and request files and a new absent
result path in an owner-only directory:

```text
liquent-membership-authority-recovery recover \
  --database-url-file DATABASE_URL_FILE \
  --request RECOVERY_REQUEST_FILE \
  --result-file RECOVERY_RESULT_FILE
```

`recovered` with exit 0 means commit or exact committed retry. The protected
0600 result contains only `recovery_id` and resulting `revision_id`.

`rejected` with exit 5 conceals which neutral eligibility, scope, foundation,
or revision precondition was not met. Input, conflict, and technical failures
use constant detail-free codes.

## Uncertain outcome

Repeat the exact request with a new absent result path. Never replace the
recovery ID, target, workspace, or expected revision merely because output was
lost. Exact retry returns the original result.

## Cleanup and follow-up

Retain evidence only in the approved restricted security record and securely
remove temporary files according to local policy.

Use the ordinary workspace authority-lifecycle operator for subsequent planned
rotation. This command cannot create or activate users or workspaces, grant new
authority history, mutate ordinary membership or permissions, bootstrap or
anchor authority, migrate schema, restart services, or expose a network path.
