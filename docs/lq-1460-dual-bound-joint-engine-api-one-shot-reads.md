# LQ-1460 Dual-bound joint engine API one-shot reads

- Expected acceptance identity is forwarded to both marker loads.
- Expected source identity continues to constrain both source loads.
- All four reads use their corresponding resolved root identity.
- The marker write retains the same acceptance-root binding.
- Existing cryptographic, temporal, and snapshot checks remain.
- Technical failure details stay inside the established boundary.
- No command-line identity input is introduced.
