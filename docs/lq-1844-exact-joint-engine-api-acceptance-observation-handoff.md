# LQ-1844 Exact joint engine API acceptance observation handoff

- Runtime type must equal the canonical observation class.
- Subclasses and structurally similar objects are not accepted.
- Complete acceptance, marker identity, and state are required.
- The return value is treated as mutation evidence.
- Caller-shaped values cannot become created-marker evidence.
- Existing observation validation remains authoritative.
- No new result model is introduced.
