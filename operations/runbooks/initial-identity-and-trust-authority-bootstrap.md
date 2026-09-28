# Initial identity and OIDC trust-authority bootstrap

This is a supervised one-time offline procedure for a newly migrated empty
environment. It does not migrate the database and is never run by the HTTP
process or deployment startup.

## Preconditions

- Verify the database is at the expected migration head.
- Use a restricted operator host and a private working directory.
- Set `umask 077` before creating files.
- Put only the SQLAlchemy PostgreSQL URL in an owner-only regular file.
- Ensure the requested result paths do not already exist.

The command rejects symbolic links, group/world-accessible input files,
non-private result directories, and existing result files. Never place the DSN
or generated identifiers in shell history, tickets, chat, or logs.

## Step 1: bootstrap identity authority

```text
liquent-initial-bootstrap identity \
  --database-url-file DATABASE_URL_FILE \
  --result-file IDENTITY_RESULT_FILE
```

On success, the result file is atomically created with owner-only permissions
and contains exactly the generated internal `user_id`, `workspace_id`,
`user_revision_id`, and `workspace_revision_id`. Standard output contains only
`bootstrapped` or `recovered`.

`recovered` means the database already contains exactly one active user, one
active workspace, and exactly their active onboarding-management authority.
Additional, partial, inactive, or differently shaped inventory is never
adopted and returns `closed`.

If the process outcome is uncertain and no complete result file exists, repeat
the same command with a new absent result path. Do not insert or inspect the
foundation with direct SQL.

Preserve the result in the approved restricted record. Use
`user_revision_id` as the first `expected_revision` for
`liquent-user-lifecycle create`, and `workspace_revision_id` as the first
`expected_revision` for `liquent-workspace-lifecycle create`. Do not copy
these values into shell history, tickets, chat, or logs. A stale revision is
rejected safely; never replace it with `null` or a guessed value.

## Step 2: prepare the selected user ID

Copy only the `user_id` from the identity result into a separate owner-only
regular file. One final newline is permitted. No whitespace is trimmed and no
other content is accepted.

## Step 3: bootstrap OIDC trust authority

```text
liquent-initial-bootstrap oidc-trust-authority \
  --database-url-file DATABASE_URL_FILE \
  --user-id-file USER_ID_FILE \
  --result-file TRUST_AUTHORITY_RESULT_FILE
```

The command invokes the one-time LQ-200 boundary. It creates no Trust revision
and no active provider configuration.

Recovery succeeds only when exactly one authority fact exists, it belongs to
the same requested active user, and both user and authority remain active. A
different target, inactive fact, extra authority, or noncanonical state returns
`closed` without modification.

## Step 4: activate OIDC trust separately

Use the LQ-203 `liquent-oidc-trust` procedure with a newly generated stable
change ID and a fully reviewed Trust request. Do not add provider values to this
bootstrap command.

## Outcomes

- `bootstrapped`, exit 0: this invocation committed the one-time fact.
- `recovered`, exit 0: exact canonical committed state was reconstructed after
  the one-time boundary was already closed.
- `closed`, exit 5: inventory is not canonically recoverable.
- generic `initial_bootstrap_operator_unavailable`, exit 2: input, filesystem,
  schema, database, transaction, decoding, or result persistence failed.

The output does not distinguish closed-state details. IDs are written only to
the protected result file, never standard output or error.

## Cleanup

After the complete outcome is confirmed, move required result evidence into the
approved restricted security record. Securely remove the local DSN, user-ID
copy, and temporary result files using the approved procedure.

This process does not create Memberships or Research permissions, mutate
authorities after bootstrap, onboard external identities, activate OIDC Trust,
restart services, or expose an HTTP route.
