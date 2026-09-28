# Supervised disposable PostgreSQL runtime cleanup

This procedure removes only the runtime container and networks of one bound
disposable PostgreSQL run. It preserves the run-bound PostgreSQL data volume.
It is a supervised offline procedure, not a script, service, scheduler, CI job,
deployment hook, HTTP route, automatic retry, or permission grant.

Do not run every command in this document. Run exactly the command selected by
the current retained system-of-record artifacts and the routing tables below.
Every next command requires a new reviewed decision.

## Scope and explicit exclusions

This runbook covers the installed runtime-cleanup commands from preflight to
cleanup-claim finalization. It does not cover initial disposable PostgreSQL
provisioning, admission, database migration, backup, restore, export, legal
hold, retention approval, or data-volume deletion.

Never use `docker compose down`, `--volumes`, force, prune, disconnect, a
wildcard, a name prefix, labels, or group cleanup as a substitute for these
commands. Never delete a claim or create, repair, rename, or overwrite evidence
manually.

Successful runtime cleanup means that the container and both networks are
absent, the exact data volume remains bound to the run, and the exact cleanup
claim has been finalized. It does not mean that the environment or data volume
has been fully disposed.

## Roles

- The environment owner approves the exact host, run, image digest, Compose
  file, project name, process account, and private evidence directory.
- The authorizer prepares each new owner-only authorization from retained
  system-of-record artifacts. The authorizer is not the command executor.
- The executor runs one selected command under the dedicated non-interactive
  cleanup account and records only its canonical outcome and exit class.
- The evidence-retention owner preserves every authorization, claim history,
  evidence record, hash inventory, and incident record.
- The incident owner controls investigation after conflict, malformed material,
  unknown infrastructure state, or technical unavailability.

No role name, account possession, ID, or this runbook is an allow decision.

## Bind one environment run

Before the first cleanup step, privately record one opaque run reference and:

- immutable application image reference `repository@sha256:<digest>`;
- reviewed source commit and Compose SHA-256;
- absolute Docker executable, Compose, runtime-environment and
  image-environment paths;
- exact Compose project name derived for the run;
- absolute private evidence directory;
- executor, authorizer, retention-owner and incident-owner identities;
- UTC approval start and expiry;
- retained staging, reconciliation, claim-reconciliation and disposition
  artifacts for the same run.

Stop if any item refers to another run, host, image, project, or evidence root.
Do not normalize a mismatch or select another file by name similarity.

## Private workspace rules

Use a reviewed local directory owned by the cleanup process account. Set:

```text
umask 077
```

All authorization and evidence inputs must be absolute regular files, owned by
the effective process account, single-link, non-symlink, and mode `0400` or
`0600` where accepted by the relevant command. The evidence directory must be
private and must support durable create, fsync, hard-link, read-back, and exact
removal.

Do not place IDs, hashes, paths, authorization JSON, claims, evidence, rendered
environment values, or error details in shell history, tickets, chat, public
logs, image layers, or environment variables. Do not broaden permissions to
make a command pass.

## Retained path map

Maintain a private path map for the bound run. The symbolic names used below
mean absolute retained paths, not shell variables or defaults:

```text
DOCKER                 reviewed executable
ROOT_AUTH              original disposable-postgres authorization
ROOT_RECON              original reconciliation authorization
CLAIM_RECON             claim-reconciliation authorization
DISPOSITION             approved disposition authorization
CLEANUP_AUTH            initial runtime-cleanup authorization
CLEANUP_RECON           cleanup reconciliation authorization
CLEANUP_FINAL           cleanup finalization authorization
CONTINUE_AUTH           first continuation authorization
CONTINUE_RECON          first continuation reconciliation authorization
CONTINUE_FINAL          first continuation finalization authorization
RECONTINUE_AUTH         recontinuation authorization
RECONTINUE_RECON        recontinuation reconciliation authorization
RECONTINUE_FINAL        recontinuation finalization authorization
CHAIN_AUTH              chained-continuation authorization
CHAIN_RECON             chained reconciliation authorization
CHAIN_FINAL             chained finalization authorization
GENERATION_AUTH         current generation continuation authorization
GENERATION_RECON        current generation reconciliation authorization
GENERATION_FINAL        current generation finalization authorization
STAGING_EVIDENCE        retained staging evidence
COMPOSE                 reviewed Compose file
RUNTIME_ENV             reviewed runtime environment file
IMAGE_ENV               reviewed image environment file
EVIDENCE_ROOT           private evidence directory
PROJECT                 exact bound Compose project name
```

Do not implement this map as exported environment variables. Expand paths only
inside the supervised invocation mechanism approved for the environment.

## Authorization-material handoff

Before each command, the authorizer must derive a new non-reusable operation ID
and authorization from the exact retained predecessor authorization and
evidence. Record privately:

- source artifact paths and their bytewise SHA-256 values;
- the new operation ID;
- separate executor and authorizer identities;
- exact operation and `runtime_only` scope;
- current positive UTC validity window of at most one hour;
- the resulting owner-only authorization path and SHA-256;
- reviewer confirmation that no unknown, duplicate, missing, or normalized
  field was introduced.

The executor may verify this handoff but must not create its own authorization,
extend an expired window, repair a hash, or copy JSON from tests. A failed
authorization check is technical unavailability and stops the procedure.

## Command inventory in authority order

The installed process boundaries are:

1. `liquent-disposable-postgres-cleanup-preflight`
2. `liquent-disposable-postgres-runtime-cleanup`
3. `liquent-disposable-postgres-cleanup-reconcile`
4. `liquent-disposable-postgres-cleanup-finalize`
5. `liquent-disposable-postgres-cleanup-continue`
6. `liquent-disposable-postgres-cleanup-continue-reconcile`
7. `liquent-disposable-postgres-cleanup-continue-finalize`
8. `liquent-disposable-postgres-cleanup-recontinue`
9. `liquent-disposable-postgres-cleanup-recontinue-reconcile`
10. `liquent-disposable-postgres-cleanup-recontinue-finalize`
11. `liquent-disposable-postgres-cleanup-chain-continue`
12. `liquent-disposable-postgres-cleanup-chain-reconcile`
13. `liquent-disposable-postgres-cleanup-chain-finalize`
14. `liquent-disposable-postgres-cleanup-generation-continue`
15. `liquent-disposable-postgres-cleanup-generation-reconcile`
16. `liquent-disposable-postgres-cleanup-generation-finalize`

This order describes authority dependencies. It is not permission to invoke all
16 commands. The current canonical outcome selects one route at a time.

## Common immutable inputs

Every invocation receives the same bound values for:

```text
--docker-executable DOCKER
--authorization-file ROOT_AUTH
--reconciliation-file ROOT_RECON
--claim-reconciliation-file CLAIM_RECON
--disposition-file DISPOSITION
--cleanup-file CLEANUP_AUTH
--staging-evidence-file STAGING_EVIDENCE
--compose-file COMPOSE
--runtime-env-file RUNTIME_ENV
--image-env-file IMAGE_ENV
--project-name PROJECT
--evidence-directory EVIDENCE_ROOT
```

Later commands add the exact retained intermediate authorization paths listed
in their sections. Never substitute a newer root file or another run.

## Stage A — fresh cleanup preflight

Invoke `liquent-disposable-postgres-cleanup-preflight` with the common immutable
inputs. The cleanup authorization is `CLEANUP_AUTH`.

- A positive eligible result permits a separate reviewed decision to invoke
  the initial cleanup with that exact authorization.
- A neutral rejection or absence stops without mutation.
- Conflict or technical unavailability stops and enters incident handling.

Do not infer eligibility from Docker output or retained evidence alone.

## Stage B — initial runtime cleanup

Invoke `liquent-disposable-postgres-runtime-cleanup` only after the fresh
preflight and separate approval. Use the same common inputs and
`CLEANUP_AUTH`.

- Confirmed runtime-removal evidence routes to Stage D for cleanup
  finalization.
- A clean rejection stops without a replacement authorization unless the
  authorizer reviews a genuinely new operation.
- Loss of output, timeout, process death, or any ambiguous technical result
  routes only to Stage C. Do not rerun this mutating command.

The original cleanup claim must remain open until Stage D succeeds.

## Stage C — inspect an unknown initial cleanup

Prepare `CLEANUP_RECON` as a new current authorization bound to
`CLEANUP_AUTH`, then invoke
`liquent-disposable-postgres-cleanup-reconcile` with the common inputs plus:

```text
--cleanup-reconciliation-file CLEANUP_RECON
```

Route the canonical outcome:

- exact cleanup evidence or complete removal -> Stage D;
- `container_stopped`, `container_removed`, or
  `application_network_removed` -> Stage D first, which records
  `continuation_required` without releasing the cleanup claim;
- `not_found` -> stop and inspect retained claim/evidence privately;
- `conflict` -> incident stop;
- technical unavailability -> incident stop with every input unchanged.

The inspector itself never creates or releases a claim.

## Stage D — finalize the current cleanup observation

Prepare `CLEANUP_FINAL` bound to `CLEANUP_RECON`, then invoke
`liquent-disposable-postgres-cleanup-finalize` with the common inputs plus:

```text
--cleanup-reconciliation-file CLEANUP_RECON
--cleanup-finalization-file CLEANUP_FINAL
```

- `runtime_removal_finalized`, `cleanup_evidence_confirmed`, or
  `no_effect_finalized` is an evidence-first cleanup-claim conclusion.
- `continuation_required` leaves the cleanup claim open and routes to Stage E
  with a newly reviewed continuation authorization.
- `not_found` stops neutrally.
- `investigation_required` or technical unavailability stops.

If cleanup-finalization evidence exists but claim release was ambiguous, repeat
this exact finalizer with unchanged files. Do not rerun the inspector or create
a new finalization ID.

## Stage E — first continuation

Prepare `CONTINUE_AUTH` from the latest nonterminal cleanup-finalization
evidence. Invoke `liquent-disposable-postgres-cleanup-continue` with common
inputs plus:

```text
--cleanup-reconciliation-file CLEANUP_RECON
--cleanup-continuation-file CONTINUE_AUTH
```

The command may perform only the minimal remaining network removals and
read-only volume identity check. Rejected state stops without mutation.
Unknown outcome routes only to Stage F.

## Stage F — inspect and finalize first continuation

Prepare `CONTINUE_RECON` and invoke
`liquent-disposable-postgres-cleanup-continue-reconcile` with common inputs
plus cleanup reconciliation, continuation, and continuation reconciliation
files.

Then prepare `CONTINUE_FINAL` and invoke
`liquent-disposable-postgres-cleanup-continue-finalize` with the same history
plus the continuation finalization file.

- Evidence-confirmed or runtime-removal-ready -> Stage D with a new current
  `CLEANUP_FINAL` authorization.
- Attempt-finalized or later-prefix-finalized -> Stage G.
- `not_found` stops neutrally.
- `investigation_required`, conflict, or technical unavailability stops.

An evidence retry repeats only the same continuation finalizer.

## Stage G — recontinuation

Prepare `RECONTINUE_AUTH` bound to the exact nonterminal `CONTINUE_FINAL`
evidence. Invoke `liquent-disposable-postgres-cleanup-recontinue` with common
inputs and the complete cleanup/continuation history through
`CONTINUE_FINAL`.

Unknown outcome routes to
`liquent-disposable-postgres-cleanup-recontinue-reconcile` with a new
`RECONTINUE_RECON`. Finalization uses
`liquent-disposable-postgres-cleanup-recontinue-finalize` with a new
`RECONTINUE_FINAL`.

- Terminal finalization -> Stage D.
- Nonterminal finalization -> Stage H.
- Neutral, conflict, rejection, or technical unavailability -> stop according
  to its exact class.

Do not repeat the first continuation against older evidence.

## Stage H — chained continuation

Prepare `CHAIN_AUTH` bound to the exact nonterminal `RECONTINUE_FINAL`
evidence. Invoke `liquent-disposable-postgres-cleanup-chain-continue` with the
complete retained history.

Unknown outcome routes to
`liquent-disposable-postgres-cleanup-chain-reconcile` with `CHAIN_RECON`.
Finalization uses `liquent-disposable-postgres-cleanup-chain-finalize` with
`CHAIN_FINAL`.

- Terminal finalization -> Stage D.
- Nonterminal finalization -> Stage I, Generation 1.
- Neutral, conflict, rejection, or technical unavailability -> stop.

Do not create another fixed chained continuation after `CHAIN_FINAL`.

## Stage I — Generation 1

Prepare `GENERATION_AUTH` with generation 1, predecessor kind `lq362`, and the
exact nonterminal `CHAIN_FINAL` authorization and evidence. Invoke
`liquent-disposable-postgres-cleanup-generation-continue` with the complete
history through `CHAIN_FINAL` and no generation-predecessor or lineage options.

Unknown outcome routes to the generation inspector with a new
`GENERATION_RECON`. Finalization uses a new `GENERATION_FINAL`.

- Terminal finalization -> Stage D.
- Nonterminal finalization -> Stage J, Generation 2.
- Neutral, conflict, rejection, or technical unavailability -> stop.

## Stage J — Generation 2

Prepare a new generation-2 continuation authorization bound to exact
generation-1 finalization evidence. The generation continuation, inspector and
finalizer each receive exactly:

```text
--predecessor-generation-continuation-file GENERATION_1_AUTH
--predecessor-generation-finalization-file GENERATION_1_FINAL
```

Do not add lineage options for Generation 2.

- Terminal finalization -> Stage D.
- Nonterminal finalization -> Stage K, Generation 3.
- Neutral, conflict, rejection, or technical unavailability -> stop.

## Stage K — Generations 3 through 17

For current generation `n`, retain two ordered private path lists containing
exactly generations 1 through `n - 1`:

```text
--generation-lineage-continuation-file GENERATION_1_AUTH
--generation-lineage-finalization-file GENERATION_1_FINAL
--generation-lineage-continuation-file GENERATION_2_AUTH
--generation-lineage-finalization-file GENERATION_2_FINAL
...
--generation-lineage-continuation-file GENERATION_N_MINUS_1_AUTH
--generation-lineage-finalization-file GENERATION_N_MINUS_1_FINAL
```

Pass the same ordered lists to continuation, inspector, and finalizer. Do not
also pass the single predecessor options. File names do not prove order; the
private inventory and each canonical generation binding do.

Generation 17, with 16 historical pairs, is the maximum. A nonterminal
Generation-17 result cannot authorize Generation 18. Stop without truncating,
paging, or replacing the lineage.

## Stage L — terminal handoff to cleanup finalization

Only `generation_continuation_evidence_confirmed` and
`runtime_removal_ready_for_cleanup_finalization` route here.

Confirm privately that every subordinate claim is absent, the exact original
cleanup claim remains open, and the complete lineage inventory is retained.
Obtain a new current `CLEANUP_FINAL` authorization bound to the original
cleanup reconciliation—not to a generation outcome.

Invoke `liquent-disposable-postgres-cleanup-finalize`. LQ-343 performs a fresh
read-only cleanup inspection. It writes separate cleanup-finalization evidence
before releasing only the exact original cleanup claim.

Do not pass generation files to LQ-343. Preserve them byte-for-byte.

## Outcome classes

- A positive step result proves only that step's closed outcome.
- A nonterminal finalized result may support exactly the next separately
  authorized continuation.
- A terminal finalized result may support a separately authorized Stage D or
  Stage L decision.
- `not_found` is neutral absence, not cleanup success.
- `rejected` is a closed no-mutation decision.
- `conflict` or `investigation_required` requires incident handling.
- Exit code `2`, absent canonical output, malformed output, or process loss is
  technical unavailability unless the relevant unknown-outcome route applies.

Never infer an outcome from an empty stdout stream alone.

## Incident stop

On conflict, malformed or mismatched evidence, foreign claim, ownership or
mode failure, hash mismatch, host loss, impossible generation, or technical
unavailability:

1. stop all cleanup commands;
2. preserve the exact input files and current evidence directory;
3. record only run reference, UTC time, command boundary and public outcome
   class outside the private incident record;
4. notify the environment and incident owners;
5. forbid manual Docker mutation, claim deletion, evidence repair, ID
   replacement, permission broadening, and automatic retry;
6. resume only from a reviewed decision based on unchanged system-of-record
   artifacts.

Exit code `2` never means `not_found` or success.

## Evidence retention and private inventory

After every command, the retention owner records privately the absolute path,
bytewise SHA-256, file ownership, mode, link count, operation ID, generation if
present, canonical outcome, and UTC observation time for every new
authorization or evidence artifact.

Preserve:

- all root, cleanup, continuation and generation authorizations;
- every claim while open and the evidence proving its later release;
- every continuation and finalization evidence generation;
- cleanup-finalization evidence;
- the ordered lineage inventory;
- incident records and exact retry decisions.

Do not treat temporary files, partial copies, screenshots, logs, or public
status messages as evidence. Retention continues after claim release and
runtime cleanup completion.

## Successful runtime-cleanup closeout

Close the supervised runtime-cleanup procedure only when all are true:

- private cleanup-finalization evidence is fully retained;
- the exact original cleanup claim is absent;
- every subordinate claim is absent;
- every authorization and evidence file remains byte-for-byte represented in
  the private inventory;
- the exact PostgreSQL data volume remains present and run-bound;
- retention and incident ownership remain assigned.

Record externally only the bound run reference, UTC completion time, and
`runtime_cleanup_finalized`. Do not disclose private IDs, hashes, paths,
resources, or error details.

## Volume disposition remains separate

Stop here. Do not mount, inspect content, export, back up, retain, release,
delete, prune, or rename the PostgreSQL data volume under this runbook.

Backup validity, legal hold, retention expiry, deletion authority and physical
volume removal require a separate future contract and evidence-first process.
Until that process completes, never report the disposable environment as fully
disposed.
