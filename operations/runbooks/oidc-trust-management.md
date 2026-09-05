# Offline OIDC trust management

This procedure applies LQ-203 trust changes from a supervised offline operator
context. It is not an HTTP, browser, startup, or deployment path.

## Preconditions

- The database is already migrated and reachable only through the controlled
  operator environment.
- The selected internal actor already exists, is active, and holds the active
  global OIDC trust-management authority.
- The operator has independently reviewed every endpoint, client identifier,
  redirect URI, scope, algorithm, and clock-skew value.
- The working directory is private and temporary. Set `umask 077` before
  creating either input file.

Do not place the database URL, request file, or generated change identifier in
shell history, tickets, chat, logs, image layers, or deployment environment
variables.

## Prepare the stable change identity

Generate the identifier exactly once:

```text
liquent-oidc-trust new-change-id
```

Record that value in the reviewed request before applying it. Preserve the
unchanged request until the outcome is certain. Never generate a replacement
identifier merely because the first invocation timed out or its output was
lost.

## Private database URL file

Write only the SQLAlchemy PostgreSQL URL into a local regular file readable by
its owner alone. The command rejects group/world-accessible files and symbolic
links.

```text
postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE
```

This tool never migrates the database and never prints the URL.

## Activation request

The first revisions-bound activation uses `expected_revision: null` and a
complete configuration:

```json
{
  "actor_user_id": "INTERNAL_USER_ID",
  "change_id": "PRESERVED_GENERATED_CHANGE_ID",
  "kind": "activate",
  "expected_revision": null,
  "configuration": {
    "issuer": "https://idp.example",
    "authorization_endpoint": "https://idp.example/authorize",
    "client_id": "liquent-control-plane",
    "redirect_uri": "https://app.example/v1/session/oidc/callback",
    "scopes": ["openid"],
    "token_endpoint": "https://idp.example/token",
    "jwks_uri": "https://idp.example/jwks",
    "allowed_signing_algorithms": ["RS256"],
    "clock_skew_seconds": 30
  }
}
```

Unknown or missing fields are rejected. No value is discovered, defaulted,
trimmed, or inherited from current trust.

## Rotation request

Rotation uses `kind: "rotate"`, the exact currently selected internal revision
in `expected_revision`, a new stable change ID, and all nine configuration
values. Do not submit only changed fields.

Rotation after deactivation still names the retained prior revision. A stale or
incorrect revision is rejected neutrally and creates nothing.

## Deactivation request

Deactivation carries no configuration:

```json
{
  "actor_user_id": "INTERNAL_USER_ID",
  "change_id": "PRESERVED_GENERATED_CHANGE_ID",
  "kind": "deactivate",
  "expected_revision": "EXACT_CURRENT_REVISION_ID",
  "configuration": null
}
```

## Apply

With both files owner-readable only:

```text
liquent-oidc-trust apply --database-url-file DATABASE_URL_FILE --request REQUEST_FILE
```

Outcomes are intentionally sparse:

- `{"outcome":"applied"}` with exit 0: committed, or an exact committed retry;
- `{"outcome":"rejected"}` with exit 5: authority or state precondition was not
  confirmed;
- generic input, conflict, or unavailable error codes with non-zero exits.

No output distinguishes missing actors, revoked authority, absent trust, stale
revision, or other neutral rejection details. No output contains configuration,
database, actor, change, or revision values.

If the outcome is technically uncertain, repeat the exact same request file.
Do not alter whitespace-sensitive values and do not create a new change ID.

## Cleanup and evidence

After a confirmed outcome, retain the reviewed change request only in the
approved restricted security record if policy requires it. Securely remove the
local database URL file and temporary working copy using the operating
environment's approved procedure.

This command does not grant or revoke authority, create users, migrate schema,
restart the application, revoke sessions, or validate provider reachability.
