# LQ-1537 Joint engine API source child invariant evidence

- Tests cover wrong type, mode, owner, and link count.
- Empty child state is rejected.
- State exceeding the fixed positional limit is rejected.
- Other authentic child states cannot compensate for one invalid state.
- Descriptor-derived observations remain accepted.
- Existing source capture tests remain green.
- Strict warning treatment guards regressions.
