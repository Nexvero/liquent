# LQ-2408 Exact installed-distribution gate

- The entry-point gate derives expected facts only from the already verified wheel.
- Installation still uses `pip --no-deps` inside the private fixed workspace child.
- Runtime metadata discovery must return exactly one installed distribution.
- Its exact name, version, console-script names, and targets must match expectations.
- Missing, additional, renamed, or retargeted entry points fail before tree retention.
- No caller-provided package identity or allow decision enters this gate.
