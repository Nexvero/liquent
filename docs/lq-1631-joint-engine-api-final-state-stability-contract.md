# LQ-1631 Joint engine API final state stability contract

- Captured acceptance state must remain stable to return.
- Same-content marker replacement changes directory state.
- Such replacement invalidates successful completion.
- Final validation may not refresh expected state.
- Exact topology and ownership remain mandatory.
- No retry repairs an unstable success tail.
- Failure remains detail-free.
