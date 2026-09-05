# Supervised disposable PostgreSQL volume disposition and deletion

This procedure evaluates and, only after separate authorization, removes the
exact PostgreSQL data volume of one bound disposable run. It is a supervised
offline procedure, not a script, service, scheduler, CI job, deployment hook,
HTTP route, automatic retry, polling loop, or permission grant.

Do not run every command in this document. Run exactly the command selected by
the current retained system-of-record artifacts and routing tables. Every next
command requires a new reviewed decision.

## Scope and explicit exclusions

This runbook begins only after terminal runtime cleanup. It covers local Docker
volume disposition, at most two exact remove attempts, reconciliation,
evidence-first claim finalization, and terminal local closeout.

It does not create retention, legal-hold, backup, restore, recovery, lineage,
or deletion authority. It does not delete backups, exports, snapshots,
replicas, logs, or historical evidence.

Never use `docker compose down`, `--volumes`, force, prune, mount, export,
manual `docker volume rm`, wildcard, prefix, labels, or project-group cleanup
as a substitute for these commands. Never delete a claim or create, repair,
rename, or overwrite evidence manually.

Successful closeout means only that the exact local Docker volume object was
finalized evidence-first and both deletion claims are absent. It never means
that all data has been disposed.

## Roles

- The environment owner approves the exact host, run, project, immutable
  image, source, Compose digest, process account, and evidence root.
- The policy owner supplies current system-of-record retention, legal-hold,
  backup, restore, and recovery decisions.
- The authorizer prepares each new owner-only authorization from retained
  artifacts and is not the executor.
- The executor runs one selected command under the dedicated non-interactive
  process account.
- The reviewer remains distinct where each command requires three identities.
- The evidence-retention owner preserves every input, authorization, claim
  history, evidence record, hash inventory, and incident record.
- The incident owner controls investigation and any reviewed resumption.

No role name, group membership, account possession, ID, or this runbook is an
allow decision.

## Bind one environment run

Before Stage A, privately record one opaque run reference and:

- reviewed source commit and immutable `repository@sha256:<digest>` image;
- reviewed Compose SHA-256 and exact project name derived for the run;
- absolute reviewed Docker executable;
- exact internally derived PostgreSQL volume identity;
- absolute private evidence root;
- terminal runtime-cleanup evidence and retained volume binding;
- lineage, retention, legal-hold, recovery, backup and restore artifacts;
- executor, authorizer, reviewer, retention-owner and incident-owner
  identities;
- UTC approval start and expiry.

Stop if any item refers to another run, host, image, project, volume, or
evidence root. Do not normalize a mismatch or select another file by name
similarity.

## Preconditions before disposition

Confirm from retained system-of-record artifacts:

- runtime cleanup is terminal and the exact volume remains run-bound;
- lineage is complete and unchanged;
- retention permits review of deletion;
- legal hold is clear and unambiguous;
- required backup and restore verification is complete;
- no later use is bound to the volume;
- evidence storage and incident ownership remain available.

Missing, stale, conflicting, or technically unclear facts stop the procedure.
Docker state, a ticket, a role, or a caller assertion cannot replace them.

## Private workspace rules

Use a reviewed local directory owned by the process account. Set:

```text
umask 077
```

Authorization and evidence inputs must be absolute regular files, owned by the
effective process account, single-link, non-symlink, and mode `0400` or `0600`
where accepted by the command. The evidence root must support durable create,
fsync, atomic hard-link finalization, read-back, and exact claim removal.

Do not place IDs, hashes, paths, authorization JSON, claims, evidence, volume
names, or error details in shell history, tickets, chat, public logs, image
layers, or environment variables. Do not broaden permissions to make a
command pass.

## Retained private path map

Maintain absolute retained paths for:

```text
DOCKER
LINEAGE
RETENTION_DECISION
LEGAL_HOLD_DECISION
RECOVERY_DECISION
DISPOSITION_AUTH
DELETION_AUTH
DELETION_RECON
DELETION_FINAL
CONTINUATION_AUTH
CONTINUATION_RECON
CONTINUATION_FINAL
TERMINAL_RECON
TERMINAL_FINAL
TERMINAL_HANDOFF
EVIDENCE_ROOT
PROJECT
```

This map is private audit material, not exported environment, configuration,
or authority. Expand paths only inside the supervised invocation mechanism.

## Authorization-material handoff

Before each command, the authorizer derives a new non-reusable operation ID
and authorization from exact retained predecessors. Record privately:

- source paths and bytewise SHA-256 values;
- every carried stable ID and exact scope;
- the new operation ID;
- distinct executor, authorizer and reviewer identities;
- current positive UTC window of at most one hour;
- resulting owner-only authorization path and SHA-256;
- reviewer confirmation that no field was omitted, normalized, inferred, or
  caller supplied.

The executor may verify this handoff but must not create its own authorization,
extend an expired window, repair a hash, or copy JSON from tests. A failed
authorization check stops as technical unavailability.

## Command inventory in authority order

1. `liquent-disposable-postgres-volume-disposition`
2. `liquent-disposable-postgres-volume-deletion-preflight`
3. `liquent-disposable-postgres-volume-delete`
4. `liquent-disposable-postgres-volume-delete-reconcile`
5. `liquent-disposable-postgres-volume-delete-finalize`
6. `liquent-disposable-postgres-volume-delete-continue`
7. `liquent-disposable-postgres-volume-delete-continue-reconcile`
8. `liquent-disposable-postgres-volume-delete-continue-finalize`
9. `liquent-disposable-postgres-volume-delete-terminal-handoff`

This order describes authority dependencies. It is not permission to invoke
all 9 commands. The current canonical outcome selects one route at a time.

## Common immutable inputs

Every selected command receives the same retained run binding and the
applicable subset of:

```text
--docker-executable DOCKER
--volume-disposition-file DISPOSITION_AUTH
--volume-deletion-file DELETION_AUTH
--lineage-manifest-file LINEAGE
--retention-decision-file RETENTION_DECISION
--legal-hold-decision-file LEGAL_HOLD_DECISION
--recovery-decision-file RECOVERY_DECISION
--project-name PROJECT
--evidence-directory EVIDENCE_ROOT
```

Later stages add exact retained reconciliation, finalization, continuation and
handoff files. Never substitute another run or a newer root artifact.

## Stage A — read-only disposition

Invoke `liquent-disposable-postgres-volume-disposition` with current
system-of-record inputs and `DISPOSITION_AUTH`.

- `deletion_review_ready` permits a separate reviewed Stage B decision.
- Any retention, hold, recovery, later-use, neutral, rejected, or
  investigation outcome stops without mutation.
- Technical unavailability stops and enters incident handling when unresolved.

The resolver never creates `DELETION_AUTH` and never grants deletion.

## Stage B — fresh deletion preflight

Prepare `DELETION_AUTH`, then invoke
`liquent-disposable-postgres-volume-deletion-preflight`.

The preflight runs Stage A logic freshly with the same authoritative inputs.

- `ready` permits a separate reviewed Stage C decision.
- `rejected` stops without claim or mutation.
- `investigation_required` or technical unavailability enters incident stop.

Do not rely on an earlier stdout value or ticket approval.

## Stage C — initial exact delete

Invoke `liquent-disposable-postgres-volume-delete` only after fresh Stage B
and separate approval.

The command creates the original deletion claim durably, performs a final
exact read-only binding check, and may issue exactly one remove for the bound
volume. It then confirms exact absence.

- Confirmed `volume_removed` writes atomic deletion evidence before releasing
  the original claim and closes the local deletion path.
- A pre-effect rejection or investigation result stops without mutation.
- Any unknown outcome after possible remove routes only to Stage D.

Do not rerun this mutating command after unknown outcome.

## Stage D — inspect an unknown initial delete

Prepare new current `DELETION_RECON`, then invoke
`liquent-disposable-postgres-volume-delete-reconcile` with the complete
original history.

- `final_evidence_present` -> Stage E.
- `volume_absent_evidence_missing` -> Stage E.
- `volume_present` -> Stage E, which records the nonterminal handoff.
- `not_found` -> neutral stop and private artifact review.
- `conflict` -> incident stop.
- Technical unavailability -> incident stop with every input unchanged.

The inspector never creates or releases a claim and never removes a volume.

## Stage E — finalize the original observation

Prepare new current `DELETION_FINAL` bound to `DELETION_RECON`, then invoke
`liquent-disposable-postgres-volume-delete-finalize`.

- `volume_removal_finalized` or `deletion_evidence_confirmed` closes the local
  deletion path after atomic evidence and original-claim release.
- `continuation_required` leaves the original claim open and permits only a
  separate reviewed Stage F decision.
- `not_found` stops neutrally.
- `investigation_required` or technical unavailability stops.

If finalization evidence exists but claim release was ambiguous, repeat this
exact finalizer with unchanged files. An evidence retry repeats only the exact
claim release and does not run the inspector or Docker.

## Stage F — one authorized continuation

Prepare new current `CONTINUATION_AUTH` bound to the nonterminal Stage E
history. Invoke `liquent-disposable-postgres-volume-delete-continue`.

Only a fresh `continuation_required` can create the subordinate claim and
reach mutation. The command may issue exactly one additional exact remove and
then confirm absence.

- Confirmed continuation evidence is written before release of only the
  subordinate claim; the original claim stays open.
- Already-finalized, neutral or investigation outcomes stop according to their
  canonical class.
- Unknown outcome after possible remove routes only to Stage G.

The total mutation budget is at most two exact remove attempts: one in Stage C
and one in Stage F. There is no third remove and no second continuation.

## Stage G — inspect an unknown continuation

Prepare new current `CONTINUATION_RECON`, then invoke
`liquent-disposable-postgres-volume-delete-continue-reconcile`.

- `continuation_evidence_present` -> Stage H.
- `volume_absent_evidence_missing` -> Stage H.
- `volume_present` or `conflict` -> incident stop; no new remove.
- `not_found` -> neutral stop.
- Technical unavailability -> incident stop.

The inspector leaves both claims, evidence and resources unchanged.

## Stage H — finalize the continuation

Prepare new current `CONTINUATION_FINAL` bound to `CONTINUATION_RECON`, then
invoke `liquent-disposable-postgres-volume-delete-continue-finalize`.

- `continuation_evidence_confirmed` or
  `volume_removal_ready_for_deletion_finalization` writes atomic finalization
  evidence, releases only the subordinate claim, and permits a separate
  Stage I decision.
- `not_found` stops neutrally.
- `investigation_required` or technical unavailability stops.

The original claim remains open. An evidence retry repeats only subordinate
claim release and does not invoke the inspector or Docker.

## Stage I — terminal handoff

Privately confirm positive Stage H evidence, absence of the subordinate claim,
and presence of the exact original claim.

Prepare new current `TERMINAL_RECON`, `TERMINAL_FINAL`, and
`TERMINAL_HANDOFF`. Invoke
`liquent-disposable-postgres-volume-delete-terminal-handoff` with the retained
continuation and continuation-finalization history.

The handoff delegates to the new LQ-398 boundary. It performs a fresh read-only
absence observation, writes terminal finalization evidence, and only then
releases the original claim.

- `volume_deletion_finalized` permits supervised closeout.
- `investigation_required` or technical unavailability stops.

The handoff has no writer of its own. A terminal evidence retry uses unchanged
files and reaches neither the inspector nor Docker.

## Outcome classes

- A positive step outcome proves only that step.
- `not_found` is neutral absence, not deletion success.
- `rejected` is a closed no-mutation decision.
- A named nonterminal outcome routes only to its documented next boundary.
- `conflict` or `investigation_required` requires incident handling.
- Exit code `2`, absent canonical output, malformed output, or process loss is
  technical unavailability unless the documented unknown-outcome route
  applies.

Never infer an outcome from empty stdout, volume absence, or exit code alone.

## Unknown outcome rules

After a possible Stage C effect, route only to Stage D. After a possible Stage
F effect, route only to Stage G.

Preserve every claim and input exactly. Do not assign a new mutation ID,
repeat the mutating command, use another Docker command, or release a claim.

No unknown outcome authorizes polling or automatic continuation.

## Incident stop

On conflict, investigation-required outcome, malformed or mismatched evidence,
foreign claim, ownership or mode failure, hash mismatch, host loss, unexpected
volume presence after Stage H, or technical unavailability:

1. stop all volume commands;
2. preserve exact inputs, claims and evidence root;
3. record only opaque run reference, UTC time, command boundary and public
   outcome class outside the private incident record;
4. notify environment, retention and incident owners;
5. forbid Docker mutation, claim deletion, evidence repair, ID replacement,
   permission broadening and automatic retry;
6. resume only from a reviewed decision based on unchanged system-of-record
   artifacts.

Exit code `2` never means `not_found` or success.

## Evidence retention and private inventory

After every command, privately inventory absolute path, bytewise SHA-256,
ownership, mode, link count, operation ID, canonical outcome and UTC
observation time for every authorization, claim and evidence artifact.

Preserve all clearance and lineage inputs, every authorization, each claim
while open and the evidence proving release, all operator and finalization
evidence, terminal evidence, retry decisions, and incident records.

Do not treat temporary files, partial copies, screenshots, logs, or public
status messages as evidence. Retention continues after claim release, volume
absence, and terminal closeout. Duration, medium, rotation and later disposal
remain environment-owned.

Never reuse an ID, claim path, evidence path, authorization, or volume identity
under a different binding, scope, run, or meaning.

## Successful local closeout

Close this supervised procedure only when all are true:

- Stage I returned canonical `volume_deletion_finalized`;
- terminal volume-deletion finalization evidence is fully retained;
- continuation-finalization evidence is retained when Stage F was used;
- the exact subordinate claim is absent;
- the exact original deletion claim is absent;
- every authorization and evidence artifact remains represented in the private
  inventory;
- no incident or technically unknown state remains open;
- retention and incident ownership remain assigned.

Record externally only opaque run reference, UTC completion time, and
`volume_deletion_finalized`. Do not disclose private IDs, hashes, paths,
resource names, or error details.

Claim absence or local volume absence alone is never successful closeout.

## Data-disposition boundary

Stop here. Backups, restores, exports, snapshots, replicas, logs and retained
evidence remain under their own system-of-record retention and disposition.

Never report “all data disposed”, “fully deleted”, or equivalent language from
this local volume outcome. The allowed statement is only that the exact local
Docker volume object was finalized evidence-first.
