# LQ-1312 Joint engine API layout path binding composition

- Each loader opens and records its private source root as before.
- Bounded child capture remains descriptor-relative and layout-specific.
- One common helper then validates root metadata and visible identity.
- Only successful revalidation permits snapshot object composition.
- Authority, policy, and artifact byte ordering remains unchanged.
- Existing final inventory comparison remains descriptor-relative.
- Public APIs, CLI behavior, and deployment wiring do not change.
