# LQ-1452 Dual-bound joint engine API accepted-source audit

- Audit forwards expected source identity to each source load.
- It forwards expected acceptance identity to each marker load.
- Cryptographic, snapshot, time, and duration checks are unchanged.
- A replacement cannot silently become the second observation basis.
- No caller-supplied allow flag or role participates in the decision.
- Technical failures use the established unavailable result.
- The command-line interface gains no identity arguments.
