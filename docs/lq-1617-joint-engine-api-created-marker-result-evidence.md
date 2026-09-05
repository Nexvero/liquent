# LQ-1617 Joint engine API created marker result evidence

- Tests receive one complete marker observation from one-shot.
- Returned state identity matches marker identity.
- Returned acceptance contains the verified run fact.
- Existing generation and state checks remain green.
- Failed paths continue raising unavailable.
- CLI behavior remains unaffected.
- Evidence is local and deterministic.
