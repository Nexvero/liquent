# LQ-1871 Joint engine API validated inventory delta contract

- Delta calculation consumes only validated inventories.
- Before and after tuples are canonical and unique.
- Existing entries must remain present in final inventory.
- Exactly one complete observation must be added.
- Created handoff must equal that exact addition.
- Invalid inventory never reaches membership comparisons.
- Acceptance atomicity semantics remain unchanged.
