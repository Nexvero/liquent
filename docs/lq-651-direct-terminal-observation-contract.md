# LQ-651 — Direct terminal observation contract

## Status

Accepted as the final observation-only parent boundary for child-owned execution.

## Direct artifact

The parent reads exactly the gate-owned Terminal-envelope role from the bound
control directory and applies the canonical control-artifact codec. Artifact ID,
handle, role, terminal observation ID, encoded SHA-256, byte count, and decoded
closed outcome must all agree.

The observation carries both the decoded terminal document and the actual
publication facts. Persistence records only those facts. The parent never
constructs an outcome from engine state, exit code, logs, exceptions, settings,
or caller input.

## Journal terminality

Direct Terminal absence is neutral and creates no transition. After an exact
Terminal record, the parent inspects the same bound runtime. A running engine
remains neutral and nonterminal. Only `exited` or `dead` permits the existing
profile-specific terminal journal transition with the exact decoded outcome.

Terminal engine state without an envelope is not success. Envelope without
terminal engine state is not journal terminality. Divergence is a closed service
conflict; malformed or unavailable evidence remains detail-free technical
unavailability.

## Scope

No Terminal publication, compatibility outcome inspection, capability executor,
wait/retry, schema, migration, port, settings, or wiring is introduced. LQ-652
implements direct observation, persistence, and journal terminalization.
