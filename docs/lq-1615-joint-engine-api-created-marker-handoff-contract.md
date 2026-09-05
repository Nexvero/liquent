# LQ-1615 Joint engine API created marker handoff contract

- One-shot returns the marker observation it finally confirmed.
- Handoff includes acceptance, identity, and complete stable state.
- Return occurs only after all one-shot checks succeed.
- Failed or uncertain acceptance returns no marker evidence.
- Callers may ignore the additive successful result.
- Handoff grants no authority beyond observed creation.
- Failure remains detail-free.
