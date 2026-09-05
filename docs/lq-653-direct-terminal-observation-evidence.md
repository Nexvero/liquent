# LQ-653 — Direct terminal observation evidence

## Status

Implemented as direct codec evidence and observation-only service guards.

## Evidence

Executable tests encode a real Writer terminal outcome, read it through the
direct observer, and prove the decoded outcome plus SHA-256/byte facts survive
exact-fact persistence unchanged.

Ordering guards prove direct Terminal persistence precedes engine inspection and
that engine inspection precedes journal terminalization. Missing Terminal and a
running engine both stop before the journal transition. Exited/dead membership,
profile-specific outcome type, handle, and final persisted result are explicit
comparisons.

Surface guards prove the absence of Terminal publication, Writer/Recovery
execution, compatibility outcome inspection, engine wait, Release wait, actor
authority, schema, CLI, and wiring.

The candidate composition now contains the observation-only Terminal service,
fixes terminal observation completeness to true, and keeps Production readiness
false. LQ-654 performs the completion audit.
