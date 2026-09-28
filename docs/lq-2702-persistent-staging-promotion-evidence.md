# LQ-2702 — Persistent staging promotion evidence

LQ-2702 persistently records the non-authorizing LQ-2701 evidence binding. The
append-only record contains only the canonical evidence digest and its exact
candidate digest, staging origin, and UTC observation time. It stores no
evidence body, session, credential, user, role, capability, or authority fact.

An identical retry is idempotent. A conflicting record for the same evidence
digest fails closed. Unknown bindings resolve as neutral absence; malformed
input, storage corruption, and technical database failures collapse to one
detail-free unavailability signal. The store exposes record and read only—no
update, delete, promotion, or deployment operation.

Migration `20260916_0045` adds only this evidence table and no seed data. This
slice performs no promotion, deployment, publication, environment mutation, or
authority decision. Current candidate and operator authority resolution and
real promotion remain separate later work.
