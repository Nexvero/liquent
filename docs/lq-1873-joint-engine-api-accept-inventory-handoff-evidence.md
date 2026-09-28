# LQ-1873 Joint engine API accept inventory handoff evidence

- Tests reject five malformed initial inventories.
- Invalid initial inventory prevents mutation entirely.
- Tests reject four malformed final inventories.
- Durable marker remains after final-inventory failure.
- Shared validator handles before, after, and result.
- Stable exact inventories still complete.
- All focused warnings are treated as errors.
