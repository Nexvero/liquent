# LQ-1293 Joint engine API remaining source budget evidence

- Tests record the effective maximum supplied to each child reader.
- A one-byte aggregate shortfall reaches child two as size minus one.
- The first child retains the lesser of its normal and aggregate limits.
- Ten-, eleven-, and fourteen-source layouts produce the same behavior.
- Normal source sets retain every pre-existing per-file maximum.
- Prior aggregate, cutoff, and source-stability tests remain green.
- Focused verification runs with deprecation warnings treated as failures.
