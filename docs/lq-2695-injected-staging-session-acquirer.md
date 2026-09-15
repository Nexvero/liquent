# LQ-2695 — Injected staging session acquirer

LQ-2695 supplies the first concrete LQ-2690 acquirer without choosing a secret
store or login mechanism. An externally owned source receives the opaque
session-set identity and exact expected revision and may return one already
validated LQ-2688 handoff. The adapter wraps that handoff in the exact acquired
set binding required by LQ-2693.

Unknown, inactive, revoked, stale, or otherwise unavailable material is exposed
by the source as neutral absence. Invalid source output is rejected. Source
failures remain available to the LQ-2693 and LQ-2694 detail-free technical
failure boundaries. Neither the adapter nor its representations expose session
values, set identities, revisions, credentials, or provider details.

The source remains externally owned and the adapter performs no work at
construction. This slice adds no persistence, cache, login automation, browser
control, provider selection, credential mutation, CLI, deployment, or
promotion. A secure operational source and real staging promotion remain later
work.
