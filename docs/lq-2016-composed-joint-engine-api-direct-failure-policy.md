# LQ-2016 Composed joint engine API direct failure policy

- Accept, both audits, and clocks share one policy.
- Inner validation remains specific to each fact.
- Outer handling remains specific to technical failure.
- No foreign ordinary exception crosses direct APIs.
- CLI continues to map all failures to status two.
- Persistence ownership remains unchanged.
- No retry or fallback is introduced.
