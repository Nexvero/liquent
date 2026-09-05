# LQ-1720 Composed joint engine API outer audit time

- Existing trusted clock helpers are reused.
- Registry mode reads monotonic clocks only.
- Accepted mode additionally reads trusted UTC.
- Existing inner clocks remain separately owned.
- CLI arguments and exit codes remain unchanged.
- Test stubs without evidence remain backward compatible.
- Technical failure remains detail-free.
