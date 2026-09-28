# LQ-1684 Joint engine API dual-time source verification

- Verification UTC validates retained source before convergence.
- Completion UTC validates it after convergence.
- UTC ordering is explicit and strict against reversal.
- Monotonic duration remains the elapsed-time authority.
- Wall time is used only for evidence validity.
- Existing trusted clock boundaries are reused.
- No caller clock is admitted.
