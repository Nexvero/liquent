# Controlled release publication handoff and worker

This procedure prepares and executes one authorized persistent publication work
unit through the installed offline process boundaries. It is a supervised
operation, not a scheduler, service, deployment hook, CI action, HTTP path, or
authorization grant.

## Preconditions

- Registry bootstrap, key activation, signing, promotion, publication bootstrap,
  executor registration, handoff, and worker execution are separate reviewed
  decisions. Perform only the stages authorized for this operation.
- The database is migrated to the exact supported head and is reachable only
  from the dedicated non-interactive publication account.
- The package-index origin, TLS path, immutable-create behavior, target name,
  and operator account have been independently approved.
- Bundle, detached SSHSIG, and promotion evidence are the retained immutable
  files bound to the persistent handoff.
- The publication credential is limited to the configured target and is not a
  signing, deployment, OIDC, research, or database credential.
- The reviewed working directory is local and private. Set `umask 077` before
  creating any operator input.

Do not copy secrets, database URLs, internal IDs, artifact hashes, provider
responses, or request files into tickets, chat, shell history, process
arguments, image layers, logs, or environment variables.

## Establish the release authorities once

Skip this section when the required active registry already exists. Never run a
second bootstrap to repair, rotate, or reactivate an existing registry.

Prepare canonical registry-bootstrap JSON:

```json
{"bootstrap_id":"REGISTRY_BOOTSTRAP_ID"}
```

Place the approved Ed25519 public key in a separate private file and invoke:

```text
liquent-release-registry-bootstrap \
  --database-url-file /PRIVATE/PATH/database-url \
  --request /PRIVATE/PATH/registry-bootstrap.json \
  --public-key-file /PRIVATE/PATH/release-key.pub
```

Preserve the returned lifecycle-authority, signer, key, registry-revision and
policy-revision IDs. They are references, not transferable authority.

Key activation is a later separately approved operation. Prepare exactly:

```json
{"actor_authority_id":"LIFECYCLE_AUTHORITY_ID","change_id":"KEY_ACTIVATION_CHANGE_ID","expected_revision":"REGISTRY_REVISION_ID","key_id":"KEY_ID"}
```

First materialize the bound challenge, obtain the independently produced proof
and reviewer approval, then apply the same unchanged request:

```text
liquent-release-key-activation challenge \
  --database-url-file /PRIVATE/PATH/database-url \
  --request /PRIVATE/PATH/key-activation.json \
  --output /PRIVATE/PATH/key-activation.challenge

liquent-release-key-activation apply \
  --database-url-file /PRIVATE/PATH/database-url \
  --request /PRIVATE/PATH/key-activation.json \
  --proof /PRIVATE/PATH/key-activation.proof \
  --approval /PRIVATE/PATH/key-activation.approval
```

Do not generate proof or approval with the publication account. Reviewer trust
is environment-owned configuration and must not be added to the request.

## Establish the publication control plane once

Skip this section when the approved active publication channel already exists.
Prepare exactly:

```json
{"bootstrap_id":"PUBLICATION_BOOTSTRAP_ID","package_name":"liquent","provider_kind":"package-index","target_name":"stable"}
```

Invoke:

```text
liquent-release-publication-bootstrap \
  --database-url-file /PRIVATE/PATH/database-url \
  --request /PRIVATE/PATH/publication-bootstrap.json
```

Preserve the returned publisher-authority, channel and channel-revision IDs.
Bootstrap does not sign, promote, hand off, or publish an artifact.

## Sign and verify the exact release candidate

Use `liquent-release-signing` under its separately approved signing procedure
to create the detached SSHSIG for the immutable bundle. Then run
`liquent-release-promotion` with the process-bound verifier identity
`liquent-release-publication-handoff-v1` and preserve its canonical evidence.

Signing does not promote. Promotion does not create a channel, handoff,
execution, attempt, provider call, or publication permission.

## Register the technical executor

Prepare a stable registration request exactly once:

```json
{"registration_id":"EXECUTOR_REGISTRATION_ID"}
```

Invoke:

```text
liquent-release-publication-executor register \
  --database-url-file /PRIVATE/PATH/database-url \
  --request /PRIVATE/PATH/executor-registration.json
```

Preserve the returned Executor-ID in the private Executor-ID file used below.
An exact retry uses the same Registration-ID and returns the same Executor-ID.
Executor registration grants no publisher, channel, registry, signing, provider,
workspace, or research authority.

## Authorize and persist the handoff

Generate and preserve one stable Execution-ID before the first handoff call.
Prepare canonical handoff JSON with exactly:

```json
{"bundle_path":"/PRIVATE/PATH/liquent.tar.gz","channel_id":"CHANNEL_ID","channel_revision_id":"CHANNEL_REVISION_ID","decision_id":"PUBLICATION_DECISION_ID","execution_id":"EXECUTION_ID","handoff_id":"HANDOFF_ID","promotion_evidence_path":"/PRIVATE/PATH/promotion.json","publisher_authority_id":"PUBLISHER_AUTHORITY_ID","signature_path":"/PRIVATE/PATH/liquent.tar.gz.sshsig"}
```

Invoke:

```text
liquent-release-publication-handoff \
  --database-url-file /PRIVATE/PATH/database-url \
  --request /PRIVATE/PATH/handoff.json
```

Exit `0`, `accepted`, authorizes the retained handoff. Exit `5`,
`not_accepted`, is a neutral current denial. Exit `3` is a detail-free binding
conflict; Exit `2` is invalid input; Exit `4` is technical unavailability.

Do not proceed to the worker unless the handoff returned `accepted`. Preserve
the handoff request byte-for-byte for every exact retry and for construction of
the worker request. The Handoff-ID, Publisher-ID, Channel-ID, Channel-Revision
and Execution-ID must be copied without normalization or replacement.

## Preserve the work identity

Prepare one canonical compact JSON work file with a final newline and exactly:

```json
{"channel_id":"CHANNEL_ID","execution_id":"EXECUTION_ID","expected_channel_revision":"CHANNEL_REVISION_ID","handoff_id":"HANDOFF_ID","publisher_authority_id":"PUBLISHER_AUTHORITY_ID"}
```

These references must come from the accepted controlled handoff. Do not add phase,
attempt, role, capability, allow, provider, artifact, or outcome fields.

Preserve this exact file for every explicit continuation of the same execution.
Never create replacement identities after a timeout or lost result.

## Prepare the artifact source

Create canonical compact JSON with the same Handoff-ID and absolute local paths:

```json
{"bundle_path":"/PRIVATE/PATH/liquent.tar.gz","handoff_id":"HANDOFF_ID","promotion_evidence_path":"/PRIVATE/PATH/promotion.json","signature_path":"/PRIVATE/PATH/liquent.tar.gz.sshsig"}
```

The signature filename must be the complete bundle filename plus `.sshsig`.
Do not insert hashes, signer claims, key IDs, package versions, or authority
facts. The worker resolves those from persistence and rechecks all bytes.

## Prepare the provider boundary

Write the package-index credential alone into its own private file. Then create
canonical compact provider JSON:

```json
{"connect_timeout_seconds":3,"credential_path":"/PRIVATE/PATH/credential","origin":"https://packages.example","read_timeout_seconds":10,"request_max_bytes":16777216,"response_max_bytes":65536,"target_name":"stable","total_timeout_seconds":15}
```

Do not configure retries, mirrors, fallback origins, redirects, alternate
targets, or a second credential. Confirm that total timeout is sufficient for
one bounded call sequence without turning the process into a polling loop.

## Prepare technical identity files

Write the approved publication Executor-ID and Promotion-Verifier-ID into two
separate private files, each with at most one final newline.

These identities describe technical execution and verification. They do not
grant publisher authority and cannot replace current persistent authority.

## Private file rules

The database URL, work request, artifact source, provider configuration,
Executor-ID, Promotion-Verifier-ID, and credential files must all be absolute,
regular, owner-held, single-link files with mode `0400` or `0600`.

Do not use symlinks, hardlinked copies, pipes, device files, group-readable
files, secret-manager mount aliases, or environment fallbacks. The operator
will not repair permissions or normalize content.

## Execute exactly once

Invoke one process with paths only:

```text
liquent-release-publication \
  --database-url-file /PRIVATE/PATH/database-url \
  --request /PRIVATE/PATH/work.json \
  --artifact-source /PRIVATE/PATH/artifacts.json \
  --provider /PRIVATE/PATH/provider.json \
  --executor-id-file /PRIVATE/PATH/executor-id \
  --promotion-verifier-id-file /PRIVATE/PATH/verifier-id
```

Do not wrap this command in an automatic retry, restart policy, timer, queue,
watcher, daemon, CI job, deployment hook, or shell loop.

## Interpret the result

- Exit `0`, `published`: a persistent confirmed receipt exists.
- Exit `6`, `published_reassessment_required`: publication is externally
  confirmed, but separate security reassessment is required.
- Exit `7`, `not_published`: the bounded lifecycle ended without publication.
- Exit `8`, `publication_conflict`: external state conflicts with the retained
  artifact and requires separate review.
- Exit `9`, `pending_reconciliation`: preserve every input unchanged and plan
  one later supervised invocation; never issue a manual replacement upload.
- Exit `5`, `not_actionable`: current persistent state or authority does not
  permit work; do not infer which prerequisite failed.
- Exit `2`: reject the input set and review it offline without broadening file
  permissions or changing persistent facts.
- Exit `4`: technical availability is unconfirmed. Preserve the exact request
  and investigate through approved infrastructure evidence without exposing
  stderr details or assuming that no provider effect occurred.

Only `published` is operational success. Every other normal outcome requires
the explicitly named review or continuation decision.

## Unknown outcome and continuation

After any possible provider write, loss of process output, timeout, or transport
failure may leave a persistent unknown outcome. Never treat that as absence.

The next supervised invocation must use the same six configuration files and
lets current persistent state choose read-only reconciliation. Do not alter the
request, generate an attempt ID, call the provider manually, or retry a PUT.

At most two immutable create attempts are available through the persistent
lifecycle. No runbook action can authorize a third attempt.

## Revocation and stale references

Every invocation resolves current registry, signer, key, channel, publisher,
and execution state again. Revocation or a stale reference closes later work.

Do not reactivate authority, edit persistence, lower verification policy, or
replace retained artifacts as part of publication execution. Those are separate
controlled security changes.

## Evidence and cleanup

Record only the approved execution reference, invocation time, process account,
exit code, canonical outcome family, and review decision in the restricted
operational record. Do not retain command tracing or provider payloads.

Keep the unchanged work and artifact inputs for all required reconciliation and
audit periods. Keep persistent receipts, attempts, recoveries, reassessments,
and evidence as the normative history.

After a terminal reviewed outcome, remove the local database URL, credential,
and temporary configuration copies using the environment's approved secure
procedure. Never delete the retained release artifacts or persistent history as
part of this command.
