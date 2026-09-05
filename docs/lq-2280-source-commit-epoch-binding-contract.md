# LQ-2280 source-commit epoch binding contract

- SOURCE_DATE_EPOCH is derived from the already bound source commit.
- The source phase addresses that commit explicitly rather than mutable HEAD.
- The resulting positive integer becomes immutable run state.
- Every later phase must retain its exact decimal environment value.
- Caller mutation cannot select a new artifact timestamp mid-run.
- The epoch remains an input to existing wheel and sdist checks.
- No clock, timezone, or filesystem timestamp becomes authoritative.
