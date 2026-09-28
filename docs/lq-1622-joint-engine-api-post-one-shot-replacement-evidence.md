# LQ-1622 Joint engine API post-one-shot replacement evidence

- Tests let one-shot complete successfully.
- They then replace the new marker with identical bytes and mode.
- Final inventory observes another marker identity and state.
- Exact handoff comparison rejects the operation.
- Stable marker handoff remains successful.
- Existing old-marker preservation remains green.
- Strict warning treatment guards regressions.
