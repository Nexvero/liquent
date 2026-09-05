# LQ-1371 Joint engine API operation mode finalization contract

- `accept-once` always finalizes its operation-root binding.
- `audit-registry` always finalizes its operation-root binding.
- `audit-accepted-source` always finalizes its operation-root binding.
- Finalization is mandatory regardless of each mode's internal outcome.
- Unknown modes remain rejected by the closed command parser.
- No mode receives an alternate root or validation exception.
- Final state must match the single initial resolved state.
