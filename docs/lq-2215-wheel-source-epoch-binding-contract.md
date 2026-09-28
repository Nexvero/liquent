# LQ-2215 Wheel source epoch binding contract

- The reviewed SOURCE_DATE_EPOCH determines the wheel ZIP timestamp.
- Direct wheel, sdist, and roundtrip wheel share that temporal fact.
- Uniform but unrelated wheel timestamps are insufficient in preflight.
- ZIP two-second resolution is the only permitted deterministic rounding.
- Epoch values outside representable release bounds fail closed.
- Standalone structural verification remains available without composition input.
- The contract adds no publication, signing, or deployment authority.
