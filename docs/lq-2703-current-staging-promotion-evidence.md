# LQ-2703 — Current staging promotion evidence

LQ-2703 resolves persisted LQ-2702 promotion evidence against the candidate
that is currently active for the evidence-bound staging origin. Both facts come
from separate trusted readers. The caller supplies only the evidence digest and
cannot provide an allow flag, role, current-candidate assertion, or authority.

Only an exact candidate-digest match produces a current evidence result.
Missing evidence, missing current candidate, candidate replacement, and
deactivation resolve as neutral absence. Malformed returned facts and technical
reader failures collapse to one detail-free unavailability signal.

The result remains evidence, not authority, and exposes no promotion or
deployment capability. Every later decision must resolve it again so candidate
replacement or deactivation affects subsequent decisions. This slice performs
no persistence mutation, publication, deployment, promotion, or environment
change and adds no schema, migration, CLI, route, worker, scheduler, retry,
credential, or secret decision. Current operator authority and real promotion
remain separate later work.
